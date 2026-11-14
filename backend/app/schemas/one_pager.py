"""One-page meeting brief wire models (Stage 5)."""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.base import WireModel

EntityType = Literal["company", "person"]


class CitationRef(WireModel):
    index: int  # [1], [2], ...
    source_id: str
    title: str
    publisher: str
    url: str
    published_at: str | None = None


class BriefBullet(WireModel):
    text: str  # includes inline [n] markers
    citation_indexes: list[int] = Field(default_factory=list)
    category: str | None = None
    is_analysis: bool = False


class OnePageBrief(WireModel):
    id: str
    entity_name: str
    entity_type: EntityType
    meeting_at: str
    research_window_start: str
    research_window_end: str
    generated_at: str
    # Section A
    executive_snapshot: str
    # Section B
    news: list[BriefBullet]
    hires_and_leadership: list[BriefBullet]
    product_and_service_launches: list[BriefBullet]
    # Section C — analytical (explicitly labelled)
    what_matters: list[BriefBullet]
    # Section D
    open_questions: list[str]
    # Citations
    citations: list[CitationRef]
    # Coverage honesty
    limitations: list[str]
    # Provenance
    research_session_id: str | None = None
    provider: str = "deterministic"  # deterministic | gemini
    # PDF meta
    page_fits: bool = True
    overflow_note: str | None = None


class OnePageRequest(WireModel):
    entity_name: str = Field(min_length=1, max_length=200)
    entity_type: Literal["company", "person", "auto"] = "auto"
    meeting_at: str = Field(min_length=8, max_length=40)
    meeting_context: str | None = Field(default=None, max_length=2000)
    window_days: int = Field(default=30, ge=1, le=90)
    # Optional: reuse an existing Stage 4 research session id
    research_session_id: str | None = None
