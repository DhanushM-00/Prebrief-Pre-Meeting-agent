from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.core.errors import UpstreamError
from app.dependencies import AnonymousSessionId
from app.db import get_db
from app.schemas.briefing import BriefingRequest, BriefingResult
from app.services.cache import SearchCache
from app.services.documents.retrieval import get_document_context
from app.services.research import run_research
from app.services.stub import build_stub
from app.services.tavily_client import TavilyClient
from sqlalchemy.orm import Session

router = APIRouter(tags=["briefing"])

_cache: SearchCache | None = None


def get_cache(settings: Settings) -> SearchCache:
    global _cache
    if _cache is None:
        _cache = SearchCache(settings.search_cache_path, settings.search_cache_ttl_seconds)
    return _cache


async def get_tavily(settings: Settings = Depends(get_settings)) -> AsyncIterator[TavilyClient | None]:
    """Overridable in tests. Yields None in stub mode; fails clearly if live mode lacks a key."""
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


@router.post("/briefing", response_model=BriefingResult, response_model_by_alias=True)
async def create_briefing(
    req: BriefingRequest,
    session_id: AnonymousSessionId,
    settings: Settings = Depends(get_settings),
    tavily: TavilyClient | None = Depends(get_tavily),
    db: Session = Depends(get_db),
) -> BriefingResult:
    # Merge uploaded-document context into focus when the caller is authenticated
    # and supplied document_ids. Uploaded claims are labelled as user-provided,
    # never treated as independently verified facts.
    effective = req
    if session_id and req.document_ids:
        ctx = get_document_context(db, session_id, req.document_ids, max_chars=8000)
        if ctx.strip():
            note = (
                "User-provided document context (unverified; treat as claims to check):\n"
                + ctx
            )
            focus = (req.focus or "").strip()
            merged_focus = f"{focus}\n\n{note}".strip() if focus else note
            effective = req.model_copy(update={"focus": merged_focus[:2000]})

    if tavily is None:
        return build_stub(effective)
    return await run_research(effective, tavily, max_results=settings.tavily_max_results)
