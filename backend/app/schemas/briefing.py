"""Pydantic mirror of src/types.ts -- the canonical PreBrief wire contract.

Any change here must be made in src/types.ts too; tests/test_types_parity.py
fails if the two drift apart.
"""
from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.base import WireModel

SubjectType = Literal["company", "person"]
SubjectTypeInput = Literal["auto", "company", "person"]
Sentiment = Literal["positive", "neutral", "negative"]
SignalKind = Literal["opportunity", "risk", "watch"]
QuestionCategory = Literal["business", "product", "strategy", "team", "market"]
NewsCategory = Literal[
    "funding", "earnings", "product", "partnerships", "leadership", "regulation",
    "litigation", "markets", "customers", "expansion", "acquisition", "hiring",
    "social", "analysis",
]
# 1 = minor, 2 = notable, 3 = major
Level = Literal[1, 2, 3]
ALLOWED_WINDOWS = (7, 14, 30, 60, 90)
WindowDays = Literal[7, 14, 30, 60, 90]


# ---------------------------------------------------------------- response --
class NewsItem(WireModel):
    id: str
    headline: str
    summary: str
    why_it_matters: str
    source: str
    source_url: str | None = None
    published_at: str
    category: NewsCategory
    sentiment: Sentiment
    impact: Level
    entities: list[str]
    in_window: bool
    is_key: bool | None = None
    opener: str | None = None
    # Optional article thumbnail from the source page (never a generic company image)
    image_url: str | None = None
    image_source: str | None = None
    # Heuristic fields — not objective truth
    cluster_id: str | None = None
    relevance_score: float | None = None
    is_interpretation: bool | None = None


class BriefFact(WireModel):
    label: str
    value: str
    hint: str | None = None


class KeyPerson(WireModel):
    name: str
    role: str
    note: str | None = None


class Snapshot(WireModel):
    type: SubjectType
    name: str
    legal_name: str | None = None
    tagline: str
    website: str | None = None
    sector: str | None = None
    headquarters: str | None = None
    founded: str | None = None
    employee_count: str | None = None
    revenue: str | None = None
    funding: str | None = None
    valuation: str | None = None
    ticker: str | None = None
    tags: list[str]
    facts: list[BriefFact]
    key_people: list[KeyPerson]
    watchlist: list[str]


class Signal(WireModel):
    id: str
    kind: SignalKind
    title: str
    detail: str
    evidence: list[str]
    severity: Level


class TalkingPoint(WireModel):
    id: str
    text: str
    rationale: str
    opener: str
    evidence: list[str]


class OpenQuestion(WireModel):
    id: str
    question: str
    why: str
    category: QuestionCategory
    evidence: list[str]


class SourceEntry(WireModel):
    id: str
    name: str
    url: str | None = None
    published_at: str
    headline: str
    category: NewsCategory
    in_window: bool


class SentimentPoint(WireModel):
    __nullable__ = frozenset({"score"})

    date: str
    # -1..+1; None means "no coverage that day" and MUST serialise as null.
    score: float | None
    volume: int


class CoverageSlice(WireModel):
    category: NewsCategory
    count: int


class BriefingStats(WireModel):
    articles: int
    sources: int
    key_items: int
    avg_sentiment: float
    days_covered: int
    categories_covered: int


class ImageAsset(WireModel):
    id: str
    url: str
    thumbnail_url: str | None = None
    title: str | None = None
    alt_text: str | None = None
    category: str  # logo | headquarters | office | product | event | brand | profile | leadership | public
    source_page_url: str | None = None
    source_name: str | None = None
    attribution: str | None = None
    license_note: str | None = None
    retrieved_at: str
    confidence: str | None = None  # high | medium | low


class BriefingResult(WireModel):
    id: str
    subject: str
    type: SubjectType
    generated_at: str
    window_days: int
    window_start: str
    window_end: str
    snapshot: Snapshot
    news: list[NewsItem]
    signals: list[Signal]
    talking_points: list[TalkingPoint]
    questions: list[OpenQuestion]
    sources: list[SourceEntry]
    sentiment_trend: list[SentimentPoint]
    coverage: list[CoverageSlice]
    stats: BriefingStats
    grounding: list[str]
    synthetic: bool | None = None
    # Visual profile / gallery (Stage 3)
    images: list[ImageAsset] | None = None



# ----------------------------------------------------------------- request --
class MeetingContext(WireModel):
    title: str = Field(max_length=200)
    date: str = Field(max_length=40)
    attendees: list[str] = Field(max_length=25)
    note: str = Field(max_length=2000)


class BriefingRequest(WireModel):
    subject: str = Field(min_length=1, max_length=200)
    type: SubjectTypeInput = "auto"
    days: WindowDays = 30
    focus: str | None = Field(default=None, max_length=300)
    meeting_note: str | None = Field(default=None, max_length=2000)
    meeting: MeetingContext | None = None
    # Optional uploaded document IDs owned by the caller — used as research context
    document_ids: list[str] | None = None
    # Stage 4: when set, research window is anchored to this meeting date/time
    meeting_at: str | None = Field(default=None, max_length=40)

    @field_validator("subject")
    @classmethod
    def _strip_subject(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("subject must not be blank")
        return v

    @field_validator("focus", "meeting_note")
    @classmethod
    def _blank_to_none(cls, v: str | None) -> str | None:
        return (v.strip() or None) if v is not None else None




# -------------------------------------------------------------------- chat --
class ChatTurn(WireModel):
    id: str
    role: Literal["user", "agent"]
    content: str = Field(max_length=8000)
    created_at: str
    citations: list[str] | None = None


class ChatRequest(WireModel):
    briefing_id: str = Field(min_length=1, max_length=200)
    question: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=40)

    @field_validator("question")
    @classmethod
    def _strip_question(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("question must not be blank")
        return v

    def prior_turns(self) -> list[ChatTurn]:
        """History *before* this question.

        The current frontend appends the new user turn to ``history`` and also
        sends it as ``question``. ``question`` is authoritative, so a trailing
        user turn with identical text is dropped to avoid asking twice.
        """
        turns = list(self.history)
        if turns and turns[-1].role == "user" and turns[-1].content.strip() == self.question:
            turns.pop()
        return turns


class ChatResponse(WireModel):
    answer: str
    citations: list[str] = Field(default_factory=list)
