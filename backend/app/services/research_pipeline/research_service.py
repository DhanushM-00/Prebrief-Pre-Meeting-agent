"""Stage 4 meeting-window research orchestrator."""
from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.orm import Session

from app.core.errors import UpstreamError
from app.models.research import ResearchFindingRow, ResearchSession, ResearchSourceRow
from app.schemas.research import (
    OpenQuestionOut,
    ResearchFindingOut,
    ResearchRequest,
    ResearchResultOut,
    ResearchSourceOut,
)
from app.services.research import parse_published  # reuse robust date parser
from app.services.research_pipeline.claims import (
    ClaimDraft,
    RawSource,
    extract_claims_from_source,
    merge_duplicate_claims,
)
from app.services.research_pipeline.classification import classify_text
from app.services.research_pipeline.entity_resolution import (
    entity_mentioned,
    person_disambiguation_ok,
    resolve_entity_type,
)
from app.services.research_pipeline.open_questions import generate_open_questions
from app.services.research_pipeline.source_verification import (
    assess_credibility,
    excerpt,
    publisher_from_url,
    relevance_score,
)
from app.services.research_pipeline.window import compute_window, in_window, parse_meeting_at
from app.services.tavily_client import TavilyClient

log = logging.getLogger("prebrief.research_pipeline")

ProgressCb = Callable[[str, str, int], Awaitable[None] | None]

_TRACKING = re.compile(r"^(utm_|fbclid|gclid|mc_|ref$|ref_src$)", re.I)


def _normalize_url(url: str) -> str:
    p = urlsplit(url.strip())
    host = p.netloc.lower().removeprefix("www.")
    q = urlencode([(k, v) for k, v in parse_qsl(p.query) if not _TRACKING.match(k)])
    return urlunsplit((p.scheme.lower(), host, p.path.rstrip("/"), q, ""))


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _build_queries(
    entity: str,
    entity_type: str,
    context: str | None,
    *,
    depth: str = "standard",
    research_question: str | None = None,
    subject_url: str | None = None,
) -> list[tuple[str, str]]:
    """Return list of (category_hint, query_text). Depth controls breadth."""
    s = entity
    if entity_type == "person":
        qs = [
            ("news", f'"{s}"'),
            ("hires_and_leadership", f'"{s}" appointed OR joins OR resigns OR "steps down"'),
            ("product_and_service_launches", f'"{s}" announces OR launches OR unveils'),
            ("business_developments", f'"{s}" funding OR partnership OR invests OR acquisition'),
            ("risks_and_challenges", f'"{s}" lawsuit OR investigation OR controversy OR fine'),
            ("news", f'"{s}" interview'),
        ]
        if depth == "deep":
            qs.extend([
                ("hires_and_leadership", f'"{s}" biography OR profile OR "career" OR education'),
                ("business_developments", f'"{s}" board OR advisor OR "joined the"'),
                ("news", f'"{s}" "keynote" OR speech OR statement'),
            ])
    else:
        qs = [
            ("news", f'"{s}"'),
            ("hires_and_leadership", f'"{s}" CEO OR executive OR appointed OR resigns OR hires'),
            ("product_and_service_launches", f'"{s}" launches OR unveils OR "new product" OR release'),
            ("business_developments", f'"{s}" funding OR raises OR acquisition OR partnership OR merger'),
            ("risks_and_challenges", f'"{s}" lawsuit OR regulatory OR investigation OR layoffs'),
            ("business_developments", f'"{s}" earnings OR revenue OR expansion'),
        ]
        if depth == "deep":
            qs.extend([
                ("business_developments", f'"{s}" competitors OR "market share" OR "versus"'),
                ("business_developments", f'"{s}" investors OR "Series" OR valuation'),
                ("product_and_service_launches", f'"{s}" customers OR "case study" OR enterprise'),
                ("risks_and_challenges", f'"{s}" "class action" OR "SEC" OR "FTC" OR fine'),
            ])
    if context:
        for term in re.split(r"[,;\n]+", context)[:3 if depth == "deep" else 2]:
            term = term.strip()
            if term and len(term) < 80:
                qs.insert(0, ("news", f'"{s}" {term}'))
    if research_question and depth != "quick":
        qs.insert(0, ("news", f'"{s}" {research_question[:120]}'))
    if subject_url and depth == "deep":
        # Encourage site-specific recall when a URL is provided
        from urllib.parse import urlparse
        host = urlparse(subject_url).netloc.removeprefix("www.")
        if host:
            qs.append(("news", f'site:{host} {s}'))
    # Dedupe by query text
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for cat, text in qs:
        k = text.lower()
        if k not in seen:
            seen.add(k)
            out.append((cat, text))
    limit = {"quick": 4, "standard": 8, "deep": 12}.get(depth, 8)
    return out[:limit]


def _build_gap_queries(entity: str, entity_type: str, gaps: list[str], existing_cats: set[str]) -> list[tuple[str, str]]:
    """Second-pass queries targeting identified information gaps."""
    qs: list[tuple[str, str]] = []
    s = entity
    gap_text = " ".join(gaps).lower()
    if "funding" in gap_text or "investor" in gap_text:
        qs.append(("business_developments", f'"{s}" funding OR raised OR investors OR valuation'))
    if "leadership" in gap_text or "executive" in gap_text or "hire" in gap_text:
        qs.append(("hires_and_leadership", f'"{s}" CEO OR CFO OR CTO OR "appointed" OR "joins as"'))
    if "product" in gap_text or "launch" in gap_text:
        qs.append(("product_and_service_launches", f'"{s}" product OR platform OR "launched" OR "released"'))
    if "competitor" in gap_text or "market" in gap_text:
        qs.append(("business_developments", f'"{s}" competitor OR "versus" OR "market leader"'))
    if "risk" in gap_text or "lawsuit" in gap_text:
        qs.append(("risks_and_challenges", f'"{s}" lawsuit OR investigation OR regulatory OR "settlement"'))
    # Always try one corroboration query if category coverage is thin
    for cat in ("news", "business_developments", "risks_and_challenges"):
        if cat not in existing_cats:
            qs.append((cat, f'"{s}" {cat.replace("_", " ")}'))
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for cat, text in qs:
        k = text.lower()
        if k not in seen:
            seen.add(k)
            out.append((cat, text))
    return out[:4]


def _findings_to_timeline(findings: list, sources_by_id: dict) -> list[dict]:
    """Build interactive timeline events from findings."""
    cat_map = {
        "news": "news",
        "hires_and_leadership": "leadership",
        "product_and_service_launches": "products",
        "business_developments": "funding",
        "risks_and_challenges": "risks",
    }
    events = []
    for f in findings:
        fid = getattr(f, "id", None) or (f.get("id") if isinstance(f, dict) else None)
        statement = getattr(f, "statement", None) or (f.get("statement") if isinstance(f, dict) else "")
        category = getattr(f, "category", None) or (f.get("category") if isinstance(f, dict) else "news")
        event_date = getattr(f, "event_date", None) or (f.get("event_date") if isinstance(f, dict) else None)
        confidence = getattr(f, "confidence", None) or (f.get("confidence") if isinstance(f, dict) else "single_source")
        srcs = getattr(f, "sources", None) or (f.get("sources") if isinstance(f, dict) else []) or []
        source_ids = getattr(f, "source_ids", None) or (f.get("source_ids") if isinstance(f, dict) else []) or []
        sid = None
        url = None
        pub = None
        if srcs:
            s0 = srcs[0]
            sid = getattr(s0, "id", None) or (s0.get("id") if isinstance(s0, dict) else None)
            url = getattr(s0, "url", None) or (s0.get("url") if isinstance(s0, dict) else None)
            pub = getattr(s0, "publisher", None) or (s0.get("publisher") if isinstance(s0, dict) else None)
        elif source_ids:
            sid = source_ids[0]
            s0 = sources_by_id.get(sid) or {}
            url = s0.get("url") if isinstance(s0, dict) else getattr(s0, "url", None)
            pub = s0.get("publisher") if isinstance(s0, dict) else getattr(s0, "publisher", None)
        importance = 3 if confidence in ("verified", "supported") else 2 if confidence == "single_source" else 1
        tl_cat = cat_map.get(str(category), "other")
        if "partner" in statement.lower():
            tl_cat = "partnerships"
        if "acqui" in statement.lower() or "merger" in statement.lower():
            tl_cat = "acquisitions"
        if "fund" in statement.lower() or "raised" in statement.lower() or "series" in statement.lower():
            tl_cat = "funding"
        events.append({
            "id": f"tl-{fid or uuid.uuid4().hex[:8]}",
            "date": event_date or "",
            "title": (statement[:120] + ("…" if len(statement) > 120 else "")),
            "category": tl_cat,
            "description": statement,
            "source_id": sid,
            "source_url": url,
            "source_publisher": pub,
            "importance": importance,
            "verification_status": confidence,
            "finding_id": fid,
        })
    # Sort by date descending when available
    events.sort(key=lambda e: e.get("date") or "", reverse=True)
    return events


def _build_evidence(findings: list, sources_by_id: dict) -> list[dict]:
    items = []
    for f in findings:
        statement = getattr(f, "statement", None) or (f.get("statement") if isinstance(f, dict) else "")
        confidence = getattr(f, "confidence", None) or (f.get("confidence") if isinstance(f, dict) else "single_source")
        srcs = getattr(f, "sources", None) or (f.get("sources") if isinstance(f, dict) else []) or []
        source_ids = getattr(f, "source_ids", None) or (f.get("source_ids") if isinstance(f, dict) else []) or []
        ids = []
        if srcs:
            for s in srcs:
                ids.append(getattr(s, "id", None) or (s.get("id") if isinstance(s, dict) else None))
        else:
            ids = list(source_ids)
        for sid in ids:
            if not sid:
                continue
            s = sources_by_id.get(sid) or {}
            if not isinstance(s, dict):
                s = {
                    "url": getattr(s, "url", None),
                    "headline": getattr(s, "headline", None),
                    "publisher": getattr(s, "publisher", None),
                    "published_at": getattr(s, "published_at", None),
                    "retrieved_at": getattr(s, "retrieved_at", None),
                    "excerpt": getattr(s, "excerpt", None),
                }
            items.append({
                "claim": statement,
                "source_id": sid,
                "source_url": s.get("url"),
                "source_title": s.get("headline"),
                "publisher": s.get("publisher"),
                "publication_date": s.get("published_at"),
                "retrieved_date": s.get("retrieved_at"),
                "excerpt": s.get("excerpt") or "",
                "verification_status": confidence,
                "confidence_note": f"Claim confidence: {confidence}",
                "conflicting_evidence": [],
            })
    return items


def _build_company_intelligence(findings: list, entity: str) -> dict:
    buckets = {
        "overview": [], "founding_history": [], "founders": [], "leadership": [],
        "products_services": [], "business_model": [], "industry": [],
        "recent_announcements": [], "funding": [], "partnerships": [],
        "competitors": [], "expansion": [], "risks": [], "opportunities": [],
        "evidence_ids": [],
    }
    for f in findings:
        statement = getattr(f, "statement", None) or (f.get("statement") if isinstance(f, dict) else "")
        cat = getattr(f, "category", None) or (f.get("category") if isinstance(f, dict) else "")
        fid = getattr(f, "id", None) or (f.get("id") if isinstance(f, dict) else None)
        if fid:
            buckets["evidence_ids"].append(fid)
        low = statement.lower()
        if "risk" in cat or any(k in low for k in ("lawsuit", "investigation", "fine", "layoff")):
            buckets["risks"].append(statement)
        elif "hire" in cat or "leadership" in cat or any(k in low for k in ("ceo", "appointed", "joins as")):
            buckets["leadership"].append(statement)
        elif "product" in cat or "launch" in cat:
            buckets["products_services"].append(statement)
            buckets["recent_announcements"].append(statement)
        elif any(k in low for k in ("fund", "raised", "series", "valuation", "investor")):
            buckets["funding"].append(statement)
        elif any(k in low for k in ("partner", "alliance", "collaboration")):
            buckets["partnerships"].append(statement)
        elif any(k in low for k in ("acqui", "merger", "expand", "opens office", "enters")):
            buckets["expansion"].append(statement)
        elif any(k in low for k in ("competitor", "versus", "rivals")):
            buckets["competitors"].append(statement)
        else:
            buckets["recent_announcements"].append(statement)
    # Cap lists
    for k, v in list(buckets.items()):
        if isinstance(v, list) and k != "evidence_ids":
            buckets[k] = v[:8]
    buckets["overview"] = (
        f"Research profile for {entity} assembled from public web sources in the selected window. "
        "Only evidence-backed statements are included."
    )
    return buckets


def _build_person_intelligence(findings: list, entity: str) -> dict:
    buckets = {
        "professional_bio": "",
        "current_role": "",
        "previous_positions": [],
        "career_timeline": [],
        "education": [],
        "associated_companies": [],
        "achievements": [],
        "public_statements": [],
        "recent_activities": [],
        "professional_relationships": [],
        "evidence_ids": [],
    }
    for f in findings:
        statement = getattr(f, "statement", None) or (f.get("statement") if isinstance(f, dict) else "")
        cat = getattr(f, "category", None) or (f.get("category") if isinstance(f, dict) else "")
        fid = getattr(f, "id", None) or (f.get("id") if isinstance(f, dict) else None)
        if fid:
            buckets["evidence_ids"].append(fid)
        low = statement.lower()
        if "hire" in cat or "leadership" in cat or any(k in low for k in ("appointed", "joins", "named", "role")):
            buckets["career_timeline"].append(statement)
            if not buckets["current_role"] and any(k in low for k in ("ceo", "cto", "cfo", "president", "director")):
                buckets["current_role"] = statement
        elif "interview" in low or "said" in low or "stated" in low:
            buckets["public_statements"].append(statement)
        else:
            buckets["recent_activities"].append(statement)
    for k in ("previous_positions", "career_timeline", "achievements", "public_statements", "recent_activities"):
        buckets[k] = buckets[k][:8]
    buckets["professional_bio"] = (
        f"Public professional profile for {entity} based solely on web sources collected "
        "in the research window. Private or sensitive personal data is excluded."
    )
    return buckets


async def _emit(cb: ProgressCb | None, stage: str, message: str, percent: int) -> None:
    if not cb:
        return
    res = cb(stage, message, percent)
    if asyncio.iscoroutine(res):
        await res


async def run_meeting_research(
    req: ResearchRequest,
    client: TavilyClient,
    *,
    db: Session | None = None,
    user_id: str | None = None,
    progress: ProgressCb | None = None,
    max_results: int = 8,
) -> ResearchResultOut:
    meeting_dt = parse_meeting_at(req.meeting_at)
    window_start, window_end, convention = compute_window(meeting_dt, req.window_days)
    entity_type = resolve_entity_type(req.entity_name, req.entity_type)
    entity = req.entity_name.strip()
    retrieved_at = _iso(datetime.now(timezone.utc))

    await _emit(progress, "resolve", f"Resolved entity type: {entity_type}", 5)
    await _emit(
        progress,
        "window",
        f"Research window {window_start.date()} → {window_end.date()} (meeting-driven)",
        10,
    )

    depth = getattr(req, "research_depth", None) or "standard"
    research_question = getattr(req, "research_question", None)
    subject_url = getattr(req, "subject_url", None)
    queries = _build_queries(
        entity, entity_type, req.meeting_context,
        depth=depth, research_question=research_question, subject_url=subject_url,
    )
    await _emit(progress, "search", f"Running {len(queries)} specialized searches ({depth})…", 20)

    async def one(qtext: str) -> dict[str, Any]:
        return await client.search_full(
            qtext,
            topic="news",
            start_date=window_start.strftime("%Y-%m-%d"),
            end_date=window_end.strftime("%Y-%m-%d"),
            max_results=max_results,
            include_images=False,
        )

    results = await asyncio.gather(*(one(q[1]) for q in queries), return_exceptions=True)
    failures = sum(1 for r in results if isinstance(r, Exception))
    if failures == len(queries):
        first = next(r for r in results if isinstance(r, Exception))
        raise first if isinstance(first, UpstreamError) else UpstreamError(str(first))

    await _emit(progress, "filter", "Verifying dates, entity match, and deduplicating…", 45)

    raw_sources: list[RawSource] = []
    seen_urls: set[str] = set()
    undated = off_topic = out_of_window = 0

    for (cat_hint, _qtext), res in zip(queries, results):
        if isinstance(res, Exception):
            continue
        rows = res.get("results") if isinstance(res, dict) else []
        if not isinstance(rows, list):
            continue
        for hit in rows:
            if not isinstance(hit, dict):
                continue
            url = (hit.get("url") or "").strip()
            title = (hit.get("title") or "").strip()
            if not url or not title:
                continue
            nu = _normalize_url(url)
            if nu in seen_urls:
                continue
            content = hit.get("content") or ""
            published = parse_published(
                hit.get("published_date") or hit.get("publishedDate") or hit.get("date")
            )
            if published is None:
                undated += 1
                continue
            if not in_window(published, window_start, window_end):
                out_of_window += 1
                continue
            if entity_type == "person":
                if not person_disambiguation_ok(entity, title, content):
                    off_topic += 1
                    continue
            elif not entity_mentioned(entity, title, content):
                off_topic += 1
                continue

            seen_urls.add(nu)
            rel = relevance_score(entity, title, content, float(hit.get("score") or 0.0))
            raw_sources.append(
                RawSource(
                    id=f"src-{uuid.uuid4().hex[:10]}",
                    headline=title,
                    publisher=publisher_from_url(url),
                    url=url,
                    published_at=_iso(published),
                    retrieved_at=retrieved_at,
                    excerpt=excerpt(content, title),
                    category=classify_text(title, content),
                    target_entity=entity,
                    relevance_score=rel,
                    credibility=assess_credibility(url),
                    in_window=True,
                    undated=False,
                )
            )

    # Near-duplicate headlines
    kept: list[RawSource] = []
    for src in sorted(raw_sources, key=lambda s: -s.relevance_score):
        if any(
            SequenceMatcher(None, src.headline.lower(), k.headline.lower()).ratio() >= 0.88
            for k in kept
        ):
            continue
        kept.append(src)

    await _emit(progress, "claims", "Extracting claim-level evidence…", 65)

    all_claims: list[ClaimDraft] = []
    for src in kept:
        all_claims.extend(extract_claims_from_source(src, entity))
    claims = merge_duplicate_claims(all_claims)

    # Build findings grouped by category — only claims with ≥1 URL
    source_by_id = {s.id: s for s in kept}
    findings: list[ResearchFindingOut] = []
    for cat in (
        "news",
        "hires_and_leadership",
        "product_and_service_launches",
        "business_developments",
        "risks_and_challenges",
    ):
        cat_claims = [c for c in claims if c.category == cat and c.source_ids]
        # Prefer higher confidence / more sources
        cat_claims.sort(key=lambda c: (-len(c.source_ids), c.statement))
        for c in cat_claims[:8]:
            srcs = [
                ResearchSourceOut(
                    id=source_by_id[sid].id,
                    headline=source_by_id[sid].headline,
                    publisher=source_by_id[sid].publisher,
                    url=source_by_id[sid].url,
                    published_at=source_by_id[sid].published_at or "",
                    retrieved_at=source_by_id[sid].retrieved_at,
                    excerpt=source_by_id[sid].excerpt,
                    category=source_by_id[sid].category,
                    target_entity=source_by_id[sid].target_entity,
                    relevance_score=source_by_id[sid].relevance_score,
                    credibility=source_by_id[sid].credibility,
                    in_window=source_by_id[sid].in_window,
                    undated=source_by_id[sid].undated,
                )
                for sid in c.source_ids
                if sid in source_by_id and source_by_id[sid].url
            ]
            if not srcs:
                continue  # never emit claim without URL
            findings.append(
                ResearchFindingOut(
                    id=f"fnd-{uuid.uuid4().hex[:10]}",
                    category=cat,  # type: ignore[arg-type]
                    statement=c.statement,
                    event_date=c.event_date,
                    confidence=c.confidence,
                    sources=srcs,
                    claims=[],  # claims embedded as finding statement for wire simplicity
                )
            )

    await _emit(progress, "questions", "Generating open questions and gap analysis…", 80)

    gaps: list[str] = []
    present = {f.category for f in findings}
    expected = {
        "hires_and_leadership": "No leadership or hiring developments found in the window.",
        "product_and_service_launches": "No product or service launches found in the window.",
        "business_developments": "No funding, M&A, or partnership developments found in the window.",
        "risks_and_challenges": "No material risks or controversies found in the window.",
        "news": "Limited general news coverage in the window.",
    }
    for cat, msg in expected.items():
        if cat not in present:
            gaps.append(msg)

    # Simple contradiction heuristic: opposite polarity keywords on same topic tokens
    contradictions: list[str] = []
    titles = [s.headline.lower() for s in kept]
    if any("raises" in t or "funding" in t for t in titles) and any(
        "layoffs" in t or "cuts" in t for t in titles
    ):
        contradictions.append("Funding/growth language appears alongside cost-cutting or layoffs coverage.")

    open_qs = generate_open_questions(
        entity=entity,
        entity_type=entity_type,
        findings=findings,
        claims=claims,
        gaps=gaps,
        contradictions=contradictions,
        meeting_context=req.meeting_context,
    )

    sources_out = [
        ResearchSourceOut(
            id=s.id,
            headline=s.headline,
            publisher=s.publisher,
            url=s.url,
            published_at=s.published_at or "",
            retrieved_at=s.retrieved_at,
            excerpt=s.excerpt,
            category=s.category,
            target_entity=s.target_entity,
            relevance_score=s.relevance_score,
            credibility=s.credibility,
            in_window=s.in_window,
            undated=s.undated,
        )
        for s in sorted(kept, key=lambda x: -x.relevance_score)
    ]

    outlets = sorted({s.publisher for s in kept})
    stats = {
        "sources": len(kept),
        "findings": len(findings),
        "claims": len(claims),
        "queries": len(queries),
        "query_failures": failures,
        "undated_excluded": undated,
        "out_of_window_excluded": out_of_window,
        "off_topic_excluded": off_topic,
        "unique_outlets": len(outlets),
        "open_questions": len(open_qs),
        "gaps": len(gaps),
    }
    grounding = [
        convention,
        f"Meeting date drives the window; server clock is not used for filtering.",
        f"{len(kept)} sources retained after date, entity, and dedupe filters.",
        f"Excluded: {undated} undated, {out_of_window} outside window, {off_topic} off-entity.",
        "Every finding includes at least one source URL. No claims without evidence.",
        "Confidence labels: verified (≥2 sources), supported (high-credibility single source), single_source otherwise.",
    ]

    sources_by_id = {s.id: s for s in sources_out}
    timeline = _findings_to_timeline(findings, sources_by_id)
    evidence = _build_evidence(findings, sources_by_id)
    company_intel = _build_company_intelligence(findings, entity) if entity_type == "company" else None
    person_intel = _build_person_intelligence(findings, entity) if entity_type == "person" else None
    stats["research_depth"] = depth
    stats["timeline_events"] = len(timeline)
    stats["evidence_items"] = len(evidence)

    result = ResearchResultOut(
        id=f"rs-{uuid.uuid4().hex[:12]}",
        entity_name=entity,
        entity_type=entity_type,  # type: ignore[arg-type]
        meeting_at=_iso(meeting_dt),
        window_start=_iso(window_start),
        window_end=_iso(window_end),
        window_days=req.window_days,
        window_convention=convention,
        findings=findings,
        sources=sources_out,
        open_questions=open_qs,
        gaps=gaps,
        contradictions=contradictions,
        stats=stats,
        grounding_notes=grounding,
        generated_at=retrieved_at,
        status="partial" if failures else "completed",
        research_depth=depth,
        timeline=timeline,
        evidence=evidence,
        company_intelligence=company_intel,
        person_intelligence=person_intel,
        research_question=research_question,
        subject_url=subject_url,
    )

    if db is not None:
        try:
            _persist(db, result, user_id=user_id, meeting_context=req.meeting_context)
        except Exception:
            log.exception("failed to persist research session")

    await _emit(progress, "done", "Research complete", 100)
    return result


def _persist(
    db: Session,
    result: ResearchResultOut,
    *,
    user_id: str | None,
    meeting_context: str | None,
) -> None:
    session = ResearchSession(
        id=result.id,
        user_id=user_id,
        entity_name=result.entity_name,
        entity_type=result.entity_type,
        meeting_at=result.meeting_at,
        window_start=result.window_start,
        window_end=result.window_end,
        window_days=result.window_days,
        meeting_context=meeting_context,
        status=result.status,
        result_json=result.model_dump_json(by_alias=True),
    )
    db.add(session)
    for s in result.sources:
        db.add(
            ResearchSourceRow(
                id=s.id,
                session_id=result.id,
                headline=s.headline,
                publisher=s.publisher,
                url=s.url,
                published_at=s.published_at,
                retrieved_at=s.retrieved_at,
                excerpt=s.excerpt,
                category=s.category,
                target_entity=s.target_entity,
                relevance_score=s.relevance_score,
                credibility=s.credibility,
                in_window=s.in_window,
                undated=s.undated,
            )
        )
    for f in result.findings:
        db.add(
            ResearchFindingRow(
                id=f.id,
                session_id=result.id,
                category=f.category,
                statement=f.statement,
                event_date=f.event_date,
                confidence=f.confidence,
                source_ids_csv=",".join(s.id for s in f.sources),
            )
        )
    db.commit()
