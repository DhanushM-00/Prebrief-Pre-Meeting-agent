"""Company-to-company and person-to-person comparison from research sessions."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import AnonymousSessionId
from app.models.research import ResearchSession
from app.schemas.research import (
    ComparisonRequest,
    ComparisonResultOut,
    ComparisonSectionOut,
    ResearchSourceOut,
)

router = APIRouter(tags=["compare"])


def _load_owned(db: Session, session_id: str, owner: str) -> dict:
    row = db.get(ResearchSession, session_id)
    if row is None or (row.user_id and row.user_id != owner):
        raise HTTPException(status_code=404, detail=f"Research session {session_id} not found")
    if not row.result_json:
        raise HTTPException(status_code=404, detail="Research session has no stored result")
    try:
        return json.loads(row.result_json)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid stored research: {e}") from e


def _statements(payload: dict, limit: int = 12) -> list[str]:
    out = []
    for f in payload.get("findings") or []:
        s = f.get("statement") or ""
        if s:
            out.append(s)
        if len(out) >= limit:
            break
    return out


def _by_category(payload: dict) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {}
    for f in payload.get("findings") or []:
        cat = f.get("category") or "news"
        buckets.setdefault(cat, []).append(f.get("statement") or "")
    return buckets


def _sources(payload: dict) -> list[ResearchSourceOut]:
    out = []
    for s in (payload.get("sources") or [])[:20]:
        try:
            out.append(ResearchSourceOut.model_validate(s))
        except Exception:
            continue
    return out


@router.post("/compare", response_model=ComparisonResultOut, response_model_by_alias=True)
async def compare_research(
    req: ComparisonRequest,
    session_id: AnonymousSessionId,
    db: Session = Depends(get_db),
) -> ComparisonResultOut:
    """Side-by-side comparison of two research sessions owned by the caller."""
    left = _load_owned(db, req.left_session_id, session_id)
    right = _load_owned(db, req.right_session_id, session_id)

    left_name = left.get("entity_name") or "Left"
    right_name = right.get("entity_name") or "Right"
    left_type = left.get("entity_type") or "company"
    right_type = right.get("entity_type") or "company"

    left_cats = _by_category(left)
    right_cats = _by_category(right)
    all_cats = sorted(set(left_cats) | set(right_cats))

    sections: list[ComparisonSectionOut] = []

    # Overview
    sections.append(
        ComparisonSectionOut(
            title="Overview",
            left=[f"{left_name} ({left_type}) — {len(left.get('findings') or [])} findings"],
            right=[f"{right_name} ({right_type}) — {len(right.get('findings') or [])} findings"],
            similarities=[],
            differences=[],
        )
    )

    for cat in all_cats:
        l_items = [x for x in left_cats.get(cat, []) if x][:6]
        r_items = [x for x in right_cats.get(cat, []) if x][:6]
        # crude similarity: shared tokens
        sims = []
        diffs = []
        if l_items and not r_items:
            diffs.append(f"Only {left_name} has coverage in {cat.replace('_', ' ')}")
        elif r_items and not l_items:
            diffs.append(f"Only {right_name} has coverage in {cat.replace('_', ' ')}")
        sections.append(
            ComparisonSectionOut(
                title=cat.replace("_", " ").title(),
                left=l_items,
                right=r_items,
                similarities=sims,
                differences=diffs,
            )
        )

    # Intelligence profiles if present
    l_intel = left.get("company_intelligence") or left.get("person_intelligence") or {}
    r_intel = right.get("company_intelligence") or right.get("person_intelligence") or {}
    if l_intel or r_intel:
        for key in ("risks", "funding", "leadership", "products_services", "recent_activities", "achievements"):
            lv = l_intel.get(key) or []
            rv = r_intel.get(key) or []
            if isinstance(lv, str):
                lv = [lv] if lv else []
            if isinstance(rv, str):
                rv = [rv] if rv else []
            if lv or rv:
                sections.append(
                    ComparisonSectionOut(
                        title=key.replace("_", " ").title(),
                        left=list(lv)[:5],
                        right=list(rv)[:5],
                        similarities=[],
                        differences=[],
                    )
                )

    summary_parts = [
        f"Comparison of **{left_name}** and **{right_name}** based on stored research sessions.",
        f"Left: {len(left.get('findings') or [])} findings / {len(left.get('sources') or [])} sources.",
        f"Right: {len(right.get('findings') or [])} findings / {len(right.get('sources') or [])} sources.",
    ]
    if req.focus:
        summary_parts.append(f"Focus requested: {req.focus}")

    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return ComparisonResultOut(
        id=f"cmp-{uuid.uuid4().hex[:10]}",
        left_entity=left_name,
        right_entity=right_name,
        left_type=left_type,
        right_type=right_type,
        sections=sections,
        left_sources=_sources(left),
        right_sources=_sources(right),
        generated_at=now,
        summary=" ".join(summary_parts),
    )
