"""Extract claim-like factual statements from source titles/excerpts.

Claims are grounded in source text only — never invented facts.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Literal

from app.services.research_pipeline.classification import (
    FindingCategory,
    classify_text,
    is_likely_interpretation,
)

ConfidenceStatus = Literal["verified", "supported", "single_source", "unconfirmed", "conflicting"]


@dataclass
class RawSource:
    id: str
    headline: str
    publisher: str
    url: str
    published_at: str | None
    retrieved_at: str
    excerpt: str
    category: str
    target_entity: str
    relevance_score: float
    credibility: str
    in_window: bool
    undated: bool


@dataclass
class ClaimDraft:
    id: str
    statement: str
    event_date: str | None
    category: FindingCategory
    confidence: ConfidenceStatus
    source_ids: list[str]
    is_interpretation: bool


def _claim_id() -> str:
    return f"cl-{uuid.uuid4().hex[:10]}"


def extract_claims_from_source(src: RawSource, entity: str) -> list[ClaimDraft]:
    """One primary claim per source, derived from headline (+ light excerpt support)."""
    if not src.url or not src.headline:
        return []
    statement = src.headline.strip()
    if src.excerpt and entity.lower() in src.excerpt.lower():
        for sent in re.split(r"(?<=[.!?])\s+", src.excerpt):
            if entity.lower() in sent.lower() and 40 <= len(sent) <= 280:
                statement = sent.strip()
                break
    cat = classify_text(src.headline, src.excerpt)
    conf: ConfidenceStatus = "single_source"
    if src.credibility == "high":
        conf = "supported"
    return [
        ClaimDraft(
            id=_claim_id(),
            statement=statement,
            event_date=src.published_at[:10] if src.published_at else None,
            category=cat,
            confidence=conf,
            source_ids=[src.id],
            is_interpretation=is_likely_interpretation(statement),
        )
    ]


def merge_duplicate_claims(claims: list[ClaimDraft]) -> list[ClaimDraft]:
    """Merge near-duplicate statements; prefer multi-source confidence."""
    out: list[ClaimDraft] = []
    for c in claims:
        key = re.sub(r"[^a-z0-9 ]", "", c.statement.lower())[:120]
        matched = None
        for existing in out:
            ekey = re.sub(r"[^a-z0-9 ]", "", existing.statement.lower())[:120]
            if key == ekey or (len(key) > 30 and key in ekey) or (len(ekey) > 30 and ekey in key):
                matched = existing
                break
        if matched:
            for sid in c.source_ids:
                if sid not in matched.source_ids:
                    matched.source_ids.append(sid)
            if len(matched.source_ids) >= 2:
                matched.confidence = "verified"
            elif matched.confidence == "single_source" and c.confidence == "supported":
                matched.confidence = "supported"
        else:
            out.append(c)
    return out
