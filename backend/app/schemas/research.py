"""Stage 4 claim-level research schemas."""
from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.base import WireModel

EntityType = Literal["company", "person", "auto"]
FindingCategory = Literal[
    "news",
    "hires_and_leadership",
    "product_and_service_launches",
    "business_developments",
    "risks_and_challenges",
]
ConfidenceStatus = Literal["verified", "supported", "single_source", "unconfirmed", "conflicting"]
QuestionGrounding = Literal["verified_development", "missing_or_conflicting"]


ResearchDepth = Literal["quick", "standard", "deep"]


class ResearchRequest(WireModel):
    entity_name: str = Field(min_length=1, max_length=200)
    entity_type: EntityType = "auto"
    # ISO date or datetime — drives the research window (not server "now")
    meeting_at: str = Field(min_length=8, max_length=40)
    meeting_context: str | None = Field(default=None, max_length=2000)
    # Optional override; default is 30 calendar days ending on meeting date
    window_days: int = Field(default=30, ge=1, le=90)
    # Stage 2: research depth controls query breadth and gap-filling rounds
    research_depth: ResearchDepth = "standard"
    # Optional subject website / profile URL for anchoring
    subject_url: str | None = Field(default=None, max_length=500)
    research_question: str | None = Field(default=None, max_length=1000)


class ResearchSourceOut(WireModel):
    id: str
    headline: str
    publisher: str
    url: str
    published_at: str
    retrieved_at: str
    excerpt: str
    category: str
    target_entity: str
    relevance_score: float
    credibility: str  # high | medium | low | unknown
    in_window: bool
    undated: bool = False


class ResearchClaimOut(WireModel):
    id: str
    statement: str
    event_date: str | None = None
    category: FindingCategory
    confidence: ConfidenceStatus
    source_ids: list[str]
    # True when statement is interpretive rather than a direct extract
    is_interpretation: bool = False


class ResearchFindingOut(WireModel):
    id: str
    category: FindingCategory
    statement: str
    event_date: str | None = None
    confidence: ConfidenceStatus
    sources: list[ResearchSourceOut]
    claims: list[ResearchClaimOut] = Field(default_factory=list)


class OpenQuestionOut(WireModel):
    id: str
    question: str
    rationale: str
    grounding: QuestionGrounding
    related_finding_ids: list[str] = Field(default_factory=list)
    category: str = "strategy"


class ResearchProgressOut(WireModel):
    stage: str
    message: str
    percent: int


class ResearchResultOut(WireModel):
    id: str
    entity_name: str
    entity_type: Literal["company", "person"]
    meeting_at: str
    window_start: str
    window_end: str
    window_days: int
    # Inclusive/exclusive convention documentation for clients
    window_convention: str
    findings: list[ResearchFindingOut]
    sources: list[ResearchSourceOut]
    open_questions: list[OpenQuestionOut]
    gaps: list[str]
    contradictions: list[str]
    stats: dict
    grounding_notes: list[str]
    generated_at: str
    status: Literal["completed", "partial", "failed"] = "completed"
    # Stage 2 enrichments — stored as plain structures for backward compatibility
    research_depth: str = "standard"
    timeline: list[dict] = Field(default_factory=list)
    evidence: list[dict] = Field(default_factory=list)
    company_intelligence: dict | None = None
    person_intelligence: dict | None = None
    research_question: str | None = None
    subject_url: str | None = None


# ---------------------------------------------------------------------------
# Stage 2: timeline, evidence, intelligence profiles, comparison
# ---------------------------------------------------------------------------

TimelineCategory = Literal[
    "news",
    "leadership",
    "funding",
    "products",
    "partnerships",
    "acquisitions",
    "market",
    "risks",
    "other",
]


class TimelineEventOut(WireModel):
    id: str
    date: str  # ISO date or datetime
    title: str
    category: TimelineCategory
    description: str
    source_id: str | None = None
    source_url: str | None = None
    source_publisher: str | None = None
    importance: Literal[1, 2, 3] = 2
    verification_status: ConfidenceStatus = "single_source"
    finding_id: str | None = None


class EvidenceItemOut(WireModel):
    """Structured evidence for a single claim."""

    claim: str
    source_id: str
    source_url: str | None = None
    source_title: str | None = None
    publisher: str | None = None
    publication_date: str | None = None
    retrieved_date: str | None = None
    excerpt: str = ""
    verification_status: ConfidenceStatus = "single_source"
    confidence_note: str = ""
    conflicting_evidence: list[str] = Field(default_factory=list)


class CompanyIntelligenceOut(WireModel):
    overview: str = ""
    founding_history: str = ""
    founders: list[str] = Field(default_factory=list)
    leadership: list[str] = Field(default_factory=list)
    products_services: list[str] = Field(default_factory=list)
    business_model: str = ""
    industry: str = ""
    recent_announcements: list[str] = Field(default_factory=list)
    funding: list[str] = Field(default_factory=list)
    partnerships: list[str] = Field(default_factory=list)
    competitors: list[str] = Field(default_factory=list)
    expansion: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class PersonIntelligenceOut(WireModel):
    professional_bio: str = ""
    current_role: str = ""
    previous_positions: list[str] = Field(default_factory=list)
    career_timeline: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    associated_companies: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    public_statements: list[str] = Field(default_factory=list)
    recent_activities: list[str] = Field(default_factory=list)
    professional_relationships: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class ComparisonRequest(WireModel):
    left_session_id: str = Field(min_length=1, max_length=36)
    right_session_id: str = Field(min_length=1, max_length=36)
    focus: str | None = Field(default=None, max_length=500)


class ComparisonSectionOut(WireModel):
    title: str
    left: list[str] = Field(default_factory=list)
    right: list[str] = Field(default_factory=list)
    similarities: list[str] = Field(default_factory=list)
    differences: list[str] = Field(default_factory=list)


class ComparisonResultOut(WireModel):
    id: str
    left_entity: str
    right_entity: str
    left_type: str
    right_type: str
    sections: list[ComparisonSectionOut]
    left_sources: list[ResearchSourceOut] = Field(default_factory=list)
    right_sources: list[ResearchSourceOut] = Field(default_factory=list)
    generated_at: str
    summary: str = ""
