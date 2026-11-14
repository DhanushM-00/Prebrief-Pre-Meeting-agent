"""Stage 5: one-page meeting brief generation + PDF/JSON export."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.core.errors import UpstreamError
from app.db import get_db
from app.dependencies import AnonymousSessionId
from app.models.research import ResearchSession
from app.schemas.one_pager import OnePageBrief, OnePageRequest
from app.schemas.research import ResearchRequest, ResearchResultOut
from app.services.cache import SearchCache
from app.services.one_pager import generate_one_pager, render_one_page_pdf, validate_one_pager
from app.services.research_pipeline import run_meeting_research
from app.services.tavily_client import TavilyClient

router = APIRouter(tags=["one-pager"])

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


async def _resolve_research(
    req: OnePageRequest,
    tavily: TavilyClient | None,
    db: Session,
    settings: Settings,
    session_id: str | None,
) -> ResearchResultOut:
    # Reuse persisted session if provided
    if req.research_session_id:
        row = db.get(ResearchSession, req.research_session_id)
        if row is None or not row.result_json:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Research session not found.")
        if row.user_id and session_id and row.user_id != session_id:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Not allowed to access this research session.")
        if row.user_id and not session_id:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Not allowed to access this research session.")
        return ResearchResultOut.model_validate_json(row.result_json)

    research_req = ResearchRequest(
        entity_name=req.entity_name,
        entity_type=req.entity_type,
        meeting_at=req.meeting_at,
        meeting_context=req.meeting_context,
        window_days=req.window_days,
    )
    if tavily is None:
        # Deterministic empty research (no fabricated news)
        from app.services.research_pipeline.window import compute_window, parse_meeting_at
        from datetime import datetime, timezone

        meeting_dt = parse_meeting_at(req.meeting_at)
        start, end, note = compute_window(meeting_dt, req.window_days)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
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
            gaps=["Stub mode: live research disabled. Set BRIEFING_MODE=live and TAVILY_API_KEY."],
            contradictions=[],
            stats={"sources": 0, "findings": 0, "mode": "stub"},
            grounding_notes=[note, "No claims fabricated in stub mode."],
            generated_at=now,
            status="partial",
        )

    return await run_meeting_research(
        research_req,
        tavily,
        db=db,
        user_id=session_id,
        max_results=settings.tavily_max_results,
    )


@router.post("/one-pager", response_model=OnePageBrief, response_model_by_alias=True)
async def create_one_pager(
    req: OnePageRequest,
    session_id: AnonymousSessionId,
    settings: Settings = Depends(get_settings),
    tavily: TavilyClient | None = Depends(get_tavily),
    db: Session = Depends(get_db),
) -> OnePageBrief:
    try:
        research = await _resolve_research(req, tavily, db, settings, session_id)
    except ValueError as e:
        return JSONResponse(  # type: ignore[return-value]
            status_code=422,
            content={"error": {"code": "validation_error", "message": str(e)}},
        )
    brief = generate_one_pager(research, meeting_context=req.meeting_context)
    validated = validate_one_pager(brief)
    brief = validated.brief
    # Probe PDF fit
    try:
        _, fits, note = render_one_page_pdf(brief)
        brief = brief.model_copy(update={"page_fits": fits, "overflow_note": note})
    except RuntimeError:
        # reportlab missing — still return JSON brief
        pass
    return brief


@router.post("/one-pager/pdf")
async def create_one_pager_pdf(
    req: OnePageRequest,
    session_id: AnonymousSessionId,
    settings: Settings = Depends(get_settings),
    tavily: TavilyClient | None = Depends(get_tavily),
    db: Session = Depends(get_db),
) -> Response:
    try:
        research = await _resolve_research(req, tavily, db, settings, session_id)
    except ValueError as e:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "validation_error", "message": str(e)}},
        )
    brief = validate_one_pager(
        generate_one_pager(research, meeting_context=req.meeting_context)
    ).brief
    try:
        pdf_bytes, fits, note = render_one_page_pdf(brief)
    except RuntimeError as e:
        return JSONResponse(
            status_code=503,
            content={"error": {"code": "pdf_unavailable", "message": str(e)}},
        )
    headers = {
        "Content-Disposition": f'attachment; filename="prebrief-{_slug(brief.entity_name)}.pdf"',
        "X-Prebrief-Page-Fits": "true" if fits else "false",
    }
    if note:
        headers["X-Prebrief-Overflow-Note"] = note[:200]
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@router.post("/one-pager/json")
async def create_one_pager_json(
    req: OnePageRequest,
    session_id: AnonymousSessionId,
    settings: Settings = Depends(get_settings),
    tavily: TavilyClient | None = Depends(get_tavily),
    db: Session = Depends(get_db),
) -> Response:
    try:
        research = await _resolve_research(req, tavily, db, settings, session_id)
    except ValueError as e:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "validation_error", "message": str(e)}},
        )
    brief = validate_one_pager(
        generate_one_pager(research, meeting_context=req.meeting_context)
    ).brief
    payload = {
        "brief": brief.model_dump(by_alias=True),
        "research": research.model_dump(by_alias=True),
    }
    body = json.dumps(payload, indent=2)
    return Response(
        content=body,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="prebrief-{_slug(brief.entity_name)}.json"'
        },
    )


def _slug(name: str) -> str:
    import re

    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return (s or "brief")[:40]
