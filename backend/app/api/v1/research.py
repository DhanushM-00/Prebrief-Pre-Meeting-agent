"""Stage 4 unified research endpoint — meeting-date window, claim-level sources."""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.core.errors import UpstreamError
from app.db import get_db
from app.dependencies import AnonymousSessionId
from app.schemas.research import ResearchRequest, ResearchResultOut
from app.services.cache import SearchCache
from app.services.research_pipeline import run_meeting_research
from app.services.tavily_client import TavilyClient

router = APIRouter(tags=["research"])

_cache: SearchCache | None = None


def get_cache(settings: Settings) -> SearchCache:
    global _cache
    if _cache is None:
        _cache = SearchCache(settings.search_cache_path, settings.search_cache_ttl_seconds)
    return _cache


async def get_tavily(settings: Settings = Depends(get_settings)) -> AsyncIterator[TavilyClient | None]:
    if settings.briefing_mode == "stub":
        yield None
        return
    if not settings.tavily_api_key:
        raise UpstreamError("Research provider is not configured (TAVILY_API_KEY is missing).")
    client = TavilyClient(
        settings.tavily_api_key,
        base_url=settings.tavily_base_url,
        timeout=settings.tavily_timeout_seconds,
        cache=get_cache(settings),
    )
    try:
        yield client
    finally:
        await client.aclose()


@router.post("/research", response_model=ResearchResultOut, response_model_by_alias=True)
async def create_research(
    req: ResearchRequest,
    session_id: AnonymousSessionId,
    settings: Settings = Depends(get_settings),
    tavily: TavilyClient | None = Depends(get_tavily),
    db: Session = Depends(get_db),
) -> ResearchResultOut:
    if tavily is None:
        # Deterministic empty-structure response for stub mode (no fabricated news)
        from datetime import datetime, timezone

        from app.services.research_pipeline.window import compute_window, parse_meeting_at

        try:
            meeting_dt = parse_meeting_at(req.meeting_at)
        except ValueError as e:
            return JSONResponse(
                status_code=422,
                content={"error": {"code": "validation_error", "message": str(e)}},
            )
        start, end, note = compute_window(meeting_dt, req.window_days)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        depth = getattr(req, "research_depth", None) or "standard"
        return ResearchResultOut(
            id="rs-stub",
            entity_name=req.entity_name.strip(),
            entity_type="company" if req.entity_type != "person" else "person",
            meeting_at=meeting_dt.isoformat().replace("+00:00", "Z"),
            window_start=start.isoformat().replace("+00:00", "Z"),
            window_end=end.isoformat().replace("+00:00", "Z"),
            window_days=req.window_days,
            window_convention=note,
            findings=[],
            sources=[],
            open_questions=[],
            gaps=[
                "Stub mode: live Tavily research is disabled. Set BRIEFING_MODE=live and TAVILY_API_KEY.",
            ],
            contradictions=[],
            stats={"sources": 0, "findings": 0, "mode": "stub", "research_depth": depth},
            grounding_notes=[note, "No claims fabricated in stub mode."],
            generated_at=now,
            status="partial",
            research_depth=depth,
            timeline=[],
            evidence=[],
            company_intelligence=None,
            person_intelligence=None,
            research_question=getattr(req, "research_question", None),
            subject_url=getattr(req, "subject_url", None),
        )

    try:
        return await run_meeting_research(
            req,
            tavily,
            db=db,
            user_id=session_id,
            max_results=settings.tavily_max_results,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "validation_error", "message": str(e)}},
        )


# ---------------------------------------------------------------------------
# Research session library (list / get / delete owned sessions)
# ---------------------------------------------------------------------------
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select, desc

from app.models.research import ResearchSession
from pydantic import Field
from app.schemas.base import WireModel


class ResearchSessionSummary(WireModel):
    id: str
    entity_name: str
    entity_type: str
    meeting_at: str
    window_days: int
    status: str
    created_at: str
    findings_count: int = 0
    sources_count: int = 0


class ResearchSessionListOut(WireModel):
    sessions: list[ResearchSessionSummary]
    total: int


@router.get("/research/sessions", response_model=ResearchSessionListOut)
async def list_research_sessions(
    session_id: AnonymousSessionId,
    db: Session = Depends(get_db),
    limit: int = 50,
) -> ResearchSessionListOut:
    """List research sessions owned by the current anonymous browser session."""
    limit = max(1, min(limit, 100))
    rows = list(
        db.scalars(
            select(ResearchSession)
            .where(ResearchSession.user_id == session_id)
            .order_by(desc(ResearchSession.created_at))
            .limit(limit)
        )
    )
    out: list[ResearchSessionSummary] = []
    for r in rows:
        findings_count = 0
        sources_count = 0
        if r.result_json:
            try:
                data = __import__("json").loads(r.result_json)
                findings_count = len(data.get("findings") or [])
                sources_count = len(data.get("sources") or [])
            except Exception:
                pass
        out.append(
            ResearchSessionSummary(
                id=r.id,
                entity_name=r.entity_name,
                entity_type=r.entity_type,
                meeting_at=r.meeting_at,
                window_days=r.window_days or 30,
                status=r.status or "completed",
                created_at=(
                    r.created_at.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
                    if r.created_at
                    else ""
                ),
                findings_count=findings_count,
                sources_count=sources_count,
            )
        )
    return ResearchSessionListOut(sessions=out, total=len(out))


@router.get("/research/sessions/{research_id}", response_model=ResearchResultOut)
async def get_research_session(
    research_id: str,
    session_id: AnonymousSessionId,
    db: Session = Depends(get_db),
) -> ResearchResultOut:
    """Load a previously completed research session (must be owned by caller)."""
    row = db.get(ResearchSession, research_id)
    if row is None or (row.user_id and row.user_id != session_id):
        raise HTTPException(status_code=404, detail="Research session not found")
    if not row.result_json:
        raise HTTPException(status_code=404, detail="Research session has no stored result")
    import json
    try:
        data = json.loads(row.result_json)
        return ResearchResultOut.model_validate(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stored research payload is invalid: {e}")


@router.delete("/research/sessions/{research_id}")
async def delete_research_session(
    research_id: str,
    session_id: AnonymousSessionId,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Delete a research session owned by the caller."""
    row = db.get(ResearchSession, research_id)
    if row is None or (row.user_id and row.user_id != session_id):
        raise HTTPException(status_code=404, detail="Research session not found")
    db.delete(row)
    db.commit()
    return {"ok": True, "id": research_id}
