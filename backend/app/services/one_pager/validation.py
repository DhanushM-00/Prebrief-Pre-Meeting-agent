"""Citation integrity validation before PDF export.

Rejects or strips unsupported factual claims so the one-page brief never
presents a fact without a mapped source URL.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.schemas.one_pager import BriefBullet, CitationRef, OnePageBrief

_CITATION_RE = re.compile(r"\[(\d+)\]")
# Phrases that mark analytical (non-factual) content
_ANALYSIS_MARKERS = ("analysis:", "analysis —", "analysis -")


@dataclass
class ValidationIssue:
    code: str
    message: str
    bullet_text: str = ""


@dataclass
class ValidationResult:
    ok: bool
    brief: OnePageBrief
    issues: list[ValidationIssue] = field(default_factory=list)
    omitted: list[str] = field(default_factory=list)


def _is_analysis(bullet: BriefBullet) -> bool:
    if bullet.is_analysis:
        return True
    t = (bullet.text or "").strip().lower()
    return any(t.startswith(m) for m in _ANALYSIS_MARKERS)


def _markers_in(text: str) -> list[int]:
    return [int(m) for m in _CITATION_RE.findall(text or "")]


def validate_one_pager(brief: OnePageBrief) -> ValidationResult:
    """Ensure every non-analysis factual bullet has valid citation→URL mapping."""
    issues: list[ValidationIssue] = []
    omitted: list[str] = []
    by_index = {c.index: c for c in brief.citations}

    def check_bullet(b: BriefBullet, section: str) -> BriefBullet | None:
        if _is_analysis(b):
            return b  # analysis may cite optionally
        markers = sorted(set(b.citation_indexes or _markers_in(b.text)))
        if not markers:
            issues.append(
                ValidationIssue(
                    "missing_citation",
                    f"Factual bullet in {section} has no citation marker",
                    b.text,
                )
            )
            omitted.append(b.text)
            return None
        valid_idxs: list[int] = []
        for idx in markers:
            cit = by_index.get(idx)
            if cit is None:
                issues.append(
                    ValidationIssue(
                        "orphan_marker",
                        f"Citation [{idx}] not found in citation list ({section})",
                        b.text,
                    )
                )
                continue
            if not cit.url or not cit.url.startswith(("http://", "https://")):
                issues.append(
                    ValidationIssue(
                        "invalid_url",
                        f"Citation [{idx}] has invalid URL ({section})",
                        b.text,
                    )
                )
                continue
            valid_idxs.append(idx)
        if not valid_idxs:
            omitted.append(b.text)
            return None
        # Rewrite markers to only valid ones if some were dropped
        text = b.text
        for idx in markers:
            if idx not in valid_idxs:
                text = text.replace(f"[{idx}]", "")
        text = re.sub(r"\s+", " ", text).strip()
        # Ensure at least one marker remains visible
        for idx in valid_idxs:
            if f"[{idx}]" not in text:
                text = f"{text} [{idx}]".strip()
        return BriefBullet(
            text=text,
            citation_indexes=valid_idxs,
            category=b.category,
            is_analysis=False,
        )

    news = [x for b in brief.news if (x := check_bullet(b, "news"))]
    hires = [x for b in brief.hires_and_leadership if (x := check_bullet(b, "hires"))]
    launches = [x for b in brief.product_and_service_launches if (x := check_bullet(b, "launches"))]
    matters: list[BriefBullet] = []
    for b in brief.what_matters:
        if _is_analysis(b):
            matters.append(b)
        else:
            x = check_bullet(b, "what_matters")
            if x:
                matters.append(x)

    # Executive snapshot citation integrity
    snapshot = brief.executive_snapshot or ""
    snap_markers = _markers_in(snapshot)
    for idx in list(snap_markers):
        cit = by_index.get(idx)
        if cit is None or not (cit.url or "").startswith(("http://", "https://")):
            issues.append(
                ValidationIssue(
                    "snapshot_citation",
                    f"Executive snapshot citation [{idx}] is missing or has an invalid URL",
                    snapshot[:120],
                )
            )
            snapshot = snapshot.replace(f"[{idx}]", "")
            omitted.append(f"snapshot marker [{idx}]")
            snap_markers = [m for m in snap_markers if m != idx]
    snapshot = re.sub(r"\s+", " ", snapshot).strip()

    used: set[int] = set(snap_markers)
    for bucket in (news, hires, launches, matters):
        for b in bucket:
            used.update(b.citation_indexes)
            used.update(_markers_in(b.text))
    citations = [c for c in brief.citations if c.index in used] or list(brief.citations)

    limitations = list(brief.limitations)
    if omitted:
        limitations.append(
            f"{len(omitted)} factual statement(s) omitted because they lacked valid source evidence."
        )

    cleaned = brief.model_copy(
        update={
            "executive_snapshot": snapshot,
            "news": news,
            "hires_and_leadership": hires,
            "product_and_service_launches": launches,
            "what_matters": matters,
            "citations": citations,
            "limitations": limitations,
        }
    )
    return ValidationResult(ok=True, brief=cleaned, issues=issues, omitted=omitted)
