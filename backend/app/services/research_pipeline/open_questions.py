"""Generate meeting-oriented open questions from findings and gaps."""
from __future__ import annotations

import uuid

from app.schemas.research import OpenQuestionOut, ResearchFindingOut
from app.services.research_pipeline.claims import ClaimDraft


def _qid() -> str:
    return f"oq-{uuid.uuid4().hex[:8]}"


def generate_open_questions(
    *,
    entity: str,
    entity_type: str,
    findings: list[ResearchFindingOut],
    claims: list[ClaimDraft],
    gaps: list[str],
    contradictions: list[str],
    meeting_context: str | None,
) -> list[OpenQuestionOut]:
    qs: list[OpenQuestionOut] = []

    by_cat: dict[str, list[ResearchFindingOut]] = {}
    for f in findings:
        by_cat.setdefault(f.category, []).append(f)

    if by_cat.get("hires_and_leadership"):
        f = by_cat["hires_and_leadership"][0]
        qs.append(
            OpenQuestionOut(
                id=_qid(),
                question=f"How do recent leadership changes at {entity} affect decision-making for this engagement?",
                rationale="Grounded in verified or supported leadership coverage in the research window.",
                grounding="verified_development",
                related_finding_ids=[f.id],
                category="team",
            )
        )
    if by_cat.get("product_and_service_launches"):
        f = by_cat["product_and_service_launches"][0]
        qs.append(
            OpenQuestionOut(
                id=_qid(),
                question=f"Which of the recent product or service launches are most relevant to our discussion, and what is the rollout status?",
                rationale="Tied to launch-related findings in the window.",
                grounding="verified_development",
                related_finding_ids=[f.id],
                category="product",
            )
        )
    if by_cat.get("business_developments"):
        f = by_cat["business_developments"][0]
        qs.append(
            OpenQuestionOut(
                id=_qid(),
                question=f"How should we interpret the recent business developments (funding, partnerships, or M&A) when scoping next steps with {entity}?",
                rationale="Based on business-development findings with source URLs.",
                grounding="verified_development",
                related_finding_ids=[f.id],
                category="strategy",
            )
        )
    if by_cat.get("risks_and_challenges"):
        f = by_cat["risks_and_challenges"][0]
        qs.append(
            OpenQuestionOut(
                id=_qid(),
                question=f"Are there open legal, regulatory, or operational issues we should account for in the meeting agenda?",
                rationale="Risks and challenges category has supporting sources in-window.",
                grounding="verified_development",
                related_finding_ids=[f.id],
                category="business",
            )
        )

    for g in gaps[:3]:
        qs.append(
            OpenQuestionOut(
                id=_qid(),
                question=f"Can you help clarify: {g.rstrip('.')}?",
                rationale="Raised because public sources in the window did not cover this area.",
                grounding="missing_or_conflicting",
                related_finding_ids=[],
                category="strategy",
            )
        )
    for c in contradictions[:2]:
        qs.append(
            OpenQuestionOut(
                id=_qid(),
                question=f"Public sources appear to conflict regarding: {c} How does {entity} view this?",
                rationale="Conflicting source coverage detected during research.",
                grounding="missing_or_conflicting",
                related_finding_ids=[],
                category="strategy",
            )
        )

    if meeting_context and len(qs) < 6:
        qs.append(
            OpenQuestionOut(
                id=_qid(),
                question=f"Given the meeting context, what outcomes is {entity} prioritizing over the next quarter?",
                rationale="Contextual question from user-provided meeting notes; not a verified public claim.",
                grounding="missing_or_conflicting",
                related_finding_ids=[],
                category="strategy",
            )
        )

    if not qs:
        qs.append(
            OpenQuestionOut(
                id=_qid(),
                question=f"What developments at {entity} over the past month should shape our agenda today?",
                rationale="Fallback agenda question when the window has limited structured findings.",
                grounding="missing_or_conflicting",
                related_finding_ids=[],
                category="business",
            )
        )

    return qs[:8]
