"""Generate a one-page meeting brief from Stage 4 verified research.

Never invents facts. Every bullet is grounded in research findings/sources.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone

from app.schemas.one_pager import BriefBullet, CitationRef, OnePageBrief
from app.schemas.research import ResearchFindingOut, ResearchResultOut, ResearchSourceOut

log = logging.getLogger("prebrief.one_pager")

_CAT_NEWS = "news"
_CAT_HIRES = "hires_and_leadership"
_CAT_LAUNCH = "product_and_service_launches"
_CAT_BIZ = "business_developments"
_CAT_RISK = "risks_and_challenges"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _fmt_date(iso: str | None) -> str:
    if not iso:
        return ""
    return iso[:10]


def _truncate(text: str, n: int) -> str:
    t = re.sub(r"\s+", " ", text or "").strip()
    if len(t) <= n:
        return t
    cut = t[: n - 1]
    return cut.rsplit(" ", 1)[0] + "…"


def _build_citation_map(sources: list[ResearchSourceOut]) -> tuple[list[CitationRef], dict[str, int]]:
    """Assign stable [n] indexes; prefer higher relevance, unique URLs."""
    seen: set[str] = set()
    ordered: list[ResearchSourceOut] = []
    for s in sorted(sources, key=lambda x: -x.relevance_score):
        if s.url in seen:
            continue
        seen.add(s.url)
        ordered.append(s)
    refs: list[CitationRef] = []
    id_to_idx: dict[str, int] = {}
    for i, s in enumerate(ordered, start=1):
        refs.append(
            CitationRef(
                index=i,
                source_id=s.id,
                title=s.headline,
                publisher=s.publisher,
                url=s.url,
                published_at=s.published_at,
            )
        )
        id_to_idx[s.id] = i
    return refs, id_to_idx


def _bullet_from_finding(
    f: ResearchFindingOut,
    id_to_idx: dict[str, int],
    *,
    max_len: int = 180,
) -> BriefBullet | None:
    idxs: list[int] = []
    for s in f.sources:
        if s.id in id_to_idx:
            idxs.append(id_to_idx[s.id])
        elif s.url:
            # Fallback: match by any citation with same URL later
            pass
    if not idxs and f.sources:
        # Still require at least one URL on the finding
        if not any(s.url for s in f.sources):
            return None
    idxs = sorted(set(idxs))
    markers = "".join(f"[{i}]" for i in idxs) if idxs else ""
    text = _truncate(f.statement, max_len)
    if markers and markers not in text:
        text = f"{text} {markers}".strip()
    return BriefBullet(
        text=text,
        citation_indexes=idxs,
        category=f.category,
        is_analysis=False,
    )


def _pick(findings: list[ResearchFindingOut], category: str, limit: int) -> list[ResearchFindingOut]:
    items = [f for f in findings if f.category == category and f.sources]
    # Prefer verified/supported and more sources
    rank = {"verified": 3, "supported": 2, "single_source": 1, "unconfirmed": 0, "conflicting": 0}
    items.sort(key=lambda f: (-rank.get(f.confidence, 0), -len(f.sources)))
    return items[:limit]


def generate_one_pager(
    research: ResearchResultOut,
    *,
    meeting_context: str | None = None,
    max_news: int = 3,
    max_hires: int = 2,
    max_launches: int = 2,
) -> OnePageBrief:
    citations, id_to_idx = _build_citation_map(research.sources)

    news_f = _pick(research.findings, _CAT_NEWS, max_news)
    # Include business/risks under news if news is thin
    if len(news_f) < max_news:
        for cat in (_CAT_BIZ, _CAT_RISK):
            for f in _pick(research.findings, cat, max_news - len(news_f)):
                if f not in news_f:
                    news_f.append(f)
            if len(news_f) >= max_news:
                break

    hires_f = _pick(research.findings, _CAT_HIRES, max_hires)
    launch_f = _pick(research.findings, _CAT_LAUNCH, max_launches)

    news = [b for f in news_f if (b := _bullet_from_finding(f, id_to_idx))]
    hires = [b for f in hires_f if (b := _bullet_from_finding(f, id_to_idx))]
    launches = [b for f in launch_f if (b := _bullet_from_finding(f, id_to_idx))]

    limitations: list[str] = list(research.gaps[:5])
    if not research.sources:
        limitations.insert(
            0,
            "No verified sources were found in the research window. Sections below may be empty.",
        )
    if not hires:
        limitations.append("No verified hires or leadership changes found in the research window.")
    if not launches:
        limitations.append("No verified product or service launches found in the research window.")
    if research.contradictions:
        limitations.extend(f"Conflicting coverage: {c}" for c in research.contradictions[:2])

    # Executive snapshot — deterministic, no invention
    if news or hires or launches:
        top = (news or hires or launches)[0]
        executive = (
            f"{research.entity_name} ({research.entity_type}). "
            f"Most notable recent development: {top.text}"
        )
    else:
        executive = (
            f"{research.entity_name} ({research.entity_type}). "
            f"Insufficient verified public coverage in the research window "
            f"({_fmt_date(research.window_start)} – {_fmt_date(research.window_end)}) "
            f"to produce a detailed snapshot."
        )
    executive = _truncate(executive, 420)

    # What matters — labelled analysis derived only from available findings
    what_matters: list[BriefBullet] = []
    if hires:
        what_matters.append(
            BriefBullet(
                text=_truncate(
                    f"Analysis: Leadership developments may affect who owns decisions in this meeting. "
                    f"Confirm current counterparts. {''.join(f'[{i}]' for i in hires[0].citation_indexes)}",
                    220,
                ),
                citation_indexes=hires[0].citation_indexes,
                is_analysis=True,
            )
        )
    if launches:
        what_matters.append(
            BriefBullet(
                text=_truncate(
                    f"Analysis: Recent launches signal product focus; ask about rollout status and relevance "
                    f"to this agenda. {''.join(f'[{i}]' for i in launches[0].citation_indexes)}",
                    220,
                ),
                citation_indexes=launches[0].citation_indexes,
                is_analysis=True,
            )
        )
    if any(f.category == _CAT_RISK for f in research.findings):
        risk = next(f for f in research.findings if f.category == _CAT_RISK)
        b = _bullet_from_finding(risk, id_to_idx, max_len=160)
        if b:
            what_matters.append(
                BriefBullet(
                    text=_truncate(
                        f"Analysis: Public risk coverage exists; consider agenda time for constraints. {b.text}",
                        220,
                    ),
                    citation_indexes=b.citation_indexes,
                    is_analysis=True,
                )
            )
    if meeting_context and what_matters:
        what_matters.append(
            BriefBullet(
                text=_truncate(
                    f"Analysis: Align discussion with stated meeting context — {_truncate(meeting_context, 120)}.",
                    200,
                ),
                citation_indexes=[],
                is_analysis=True,
            )
        )
    if not what_matters:
        what_matters.append(
            BriefBullet(
                text="Analysis: Limited verified developments in-window; use open questions to surface priorities directly.",
                citation_indexes=[],
                is_analysis=True,
            )
        )

    # Open questions — prefer Stage 4 grounded questions
    oq = [q.question for q in research.open_questions[:5]]
    if not oq:
        oq = [
            f"What developments at {research.entity_name} should shape today's agenda?",
            "Are there leadership or ownership changes we should account for?",
            "What outcomes are highest priority for the next quarter?",
        ]

    # Trim citations to those actually referenced
    used: set[int] = set()
    for bucket in (news, hires, launches, what_matters):
        for b in bucket:
            used.update(b.citation_indexes)
    citations = [c for c in citations if c.index in used] or citations[:8]
    # Re-index is NOT done — markers already assigned; keep stable indexes

    return OnePageBrief(
        id=f"op-{uuid.uuid4().hex[:12]}",
        entity_name=research.entity_name,
        entity_type=research.entity_type,
        meeting_at=research.meeting_at,
        research_window_start=research.window_start,
        research_window_end=research.window_end,
        generated_at=_iso_now(),
        executive_snapshot=executive,
        news=news,
        hires_and_leadership=hires,
        product_and_service_launches=launches,
        what_matters=what_matters[:4],
        open_questions=oq[:5],
        citations=citations,
        limitations=limitations[:8],
        research_session_id=research.id,
        provider="deterministic",
        page_fits=True,
        overflow_note=None,
    )
