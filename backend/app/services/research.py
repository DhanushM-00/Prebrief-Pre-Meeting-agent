"""Phase 3 research pipeline: Tavily search -> in-window filter -> relevance -> dedupe -> BriefingResult.

What is real here: URLs, headlines, outlets, publication dates, window enforcement, dedupe, counts.
What is INTERIM until Phase 4 (Gemini): category/sentiment/impact are keyword heuristics,
`whyItMatters` is a generic per-category sentence, and snapshot/signals/talkingPoints/questions
are left empty rather than invented.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.core.errors import UpstreamError
from app.schemas.briefing import (
    BriefingRequest, BriefingResult, NewsItem, Snapshot, SourceEntry, SubjectType,
)
from app.services import derive
from app.services.images import discover_images
from app.services.tavily_client import TavilyClient

MAX_QUERIES = 10
_CORPORATE = re.compile(
    r"\b(inc|ltd|llc|plc|gmbh|corp|corporation|co|company|group|holdings|labs|systems|technologies|ventures|partners|bank|airlines|motors)\b\.?",
    re.I,
)
_HONORIFIC = re.compile(r"^(dr|mr|mrs|ms|prof)\.?\s+", re.I)

# --------------------------------------------------------------- categories --
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "funding": ("raises", "raised", "funding", "series a", "series b", "series c", "seed round", "valuation", "investors", "venture"),
    "earnings": ("earnings", "revenue", "quarterly", "profit", "guidance", "results", "ebitda"),
    "acquisition": ("acquire", "acquires", "acquisition", "merger", "takeover", "buyout", "to buy"),
    "litigation": ("lawsuit", "sues", "sued", "court", "settlement", "litigation", "class action", "alleged"),
    "regulation": ("regulator", "regulatory", "fine", "fined", "investigation", "probe", "antitrust", "compliance", "sec "),
    "leadership": ("ceo", "cfo", "cto", "appoints", "appointed", "steps down", "resigns", "hires", "chairman", "executive"),
    "partnerships": ("partnership", "partners with", "collaboration", "alliance", "agreement", "joint venture"),
    "product": ("launch", "launches", "unveils", "releases", "announces", "new product", "feature", "rollout"),
    "expansion": ("expands", "expansion", "new office", "opens", "enters", "market entry"),
    "hiring": ("layoffs", "lays off", "hiring", "job cuts", "headcount", "workforce"),
    "customers": ("customer", "customers", "contract", "signs", "wins deal"),
    "markets": ("shares", "stock", "market cap", "ipo", "listing", "trading"),
}
HIGH_IMPACT = {"funding", "acquisition", "earnings", "litigation", "regulation", "leadership"}
CATEGORY_WHY = {  # INTERIM generic text; replaced by Gemini-written, article-specific text in Phase 4.
    "funding": "Funding news changes runway and priorities; worth asking how it shifts their plans.",
    "earnings": "Financial results frame what they can commit to; check how they describe the numbers.",
    "acquisition": "M&A reshapes ownership and roadmap; ask how it affects the area you are meeting about.",
    "litigation": "Legal exposure can constrain what they say and do; consider raising it early and directly.",
    "regulation": "Regulatory attention can slow plans or add cost; ask how they are preparing.",
    "leadership": "Leadership changes affect who decides; confirm who owns the topic now.",
    "partnerships": "Partnerships signal strategy and possible competitors or alternatives to your proposal.",
    "product": "Product moves show where effort is going; ask what is shipping versus announced.",
    "expansion": "Expansion shows ambition and strain; ask what it means for support and priorities.",
    "hiring": "Headcount moves hint at confidence and cost pressure.",
    "customers": "Customer news shows what is working in the market.",
    "markets": "Market reaction shows how outsiders read the story.",
    "social": "Public commentary shows how they are perceived.",
    "analysis": "Analysis pieces show the prevailing outside view of the company.",
}
POSITIVE = ("raises", "secures", "wins", "growth", "record", "launches", "expands", "partnership", "profit", "surges", "beats", "approved", "milestone", "rises")
NEGATIVE = ("lawsuit", "sues", "sued", "fined", "probe", "investigation", "layoffs", "cuts", "falls", "plunges", "loss", "recall", "breach", "fraud", "resigns", "slump", "bankruptcy", "misses", "halts", "delays")


@dataclass(frozen=True)
class Query:
    category: str
    text: str


def resolve_type(subject: str, requested: str) -> SubjectType:
    """INTERIM: Gemini resolves ambiguous subjects in Phase 4. Users can always force the type."""
    if requested in ("company", "person"):
        return requested  # type: ignore[return-value]
    if _HONORIFIC.match(subject.strip()) and not _CORPORATE.search(subject):
        return "person"
    return "company"


def build_queries(subject: str, type_: SubjectType, focus: str | None) -> list[Query]:
    s = subject
    if type_ == "company":
        defaults = [
            Query("analysis", f'"{s}"'),
            Query("funding", f"{s} funding raises investment valuation"),
            Query("leadership", f"{s} CEO executive appointment leadership"),
            Query("litigation", f"{s} lawsuit regulatory investigation"),
            Query("product", f"{s} launches new product announcement"),
            Query("partnerships", f"{s} partnership deal agreement"),
            Query("earnings", f"{s} earnings revenue quarterly results"),
            Query("regulation", f"{s} regulatory compliance fine investigation"),
            Query("acquisition", f"{s} acquisition merger acquires"),
        ]
    else:
        defaults = [
            Query("analysis", f'"{s}"'),
            Query("leadership", f"{s} appointed role joins steps down"),
            Query("litigation", f"{s} lawsuit investigation controversy"),
            Query("partnerships", f"{s} invests backs partnership"),
            Query("analysis", f"{s} interview says"),
            Query("product", f"{s} announces product launch"),
        ]
    steer: list[Query] = []
    for term in re.split(r"[,;\n]+", focus or ""):
        term = term.strip()
        if term:
            steer.append(Query(classify(term, "analysis"), f"{s} {term}"))
    out: list[Query] = []
    seen: set[str] = set()
    for q in [*steer[:3], *defaults]:  # focus first: it is the user's explicit intent
        if q.text.lower() not in seen:
            seen.add(q.text.lower())
            out.append(q)
    return out[:MAX_QUERIES]


def classify(text: str, hint: str) -> str:
    t = f" {text.lower()} "
    best, best_n = hint, 0
    for cat, words in CATEGORY_KEYWORDS.items():
        n = sum(1 for w in words if w in t)
        if n > best_n:
            best, best_n = cat, n
    return best


def sentiment_of(title: str, content: str) -> str:
    t, c = title.lower(), content.lower()
    score = 0
    for w in POSITIVE:
        score += 2 * (w in t) + (w in c)
    for w in NEGATIVE:
        score -= 2 * (w in t) + (w in c)
    return "positive" if score >= 2 else "negative" if score <= -2 else "neutral"


# -------------------------------------------------------------------- dates --
def parse_published(raw: Any) -> datetime | None:
    """Accepts ISO-8601 and RFC-2822 strings. Returns None rather than guessing."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    s = raw.strip()
    dt: datetime | None = None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = parsedate_to_datetime(s)
        except (TypeError, ValueError):
            return None
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


# ------------------------------------------------------------------- dedupe --
_TRACKING = re.compile(r"^(utm_|fbclid|gclid|mc_|ref$|ref_src$)", re.I)


def normalize_url(url: str) -> str:
    p = urlsplit(url.strip())
    host = p.netloc.lower().removeprefix("www.")
    q = urlencode([(k, v) for k, v in parse_qsl(p.query) if not _TRACKING.match(k)])
    return urlunsplit((p.scheme.lower(), host, p.path.rstrip("/"), q, ""))


def _title_key(t: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", t.lower()).strip()


def is_relevant(subject: str, title: str, content: str) -> bool:
    text = f"{title} {content}".lower()
    s = subject.lower().strip()
    if s in text:
        return True
    tokens = [t for t in re.split(r"\W+", s) if len(t) > 2]
    return bool(tokens) and all(t in text for t in tokens)


def summarize(content: str, title: str, limit: int = 280) -> str:
    """Extractive only: a trimmed excerpt of the source text. Nothing is generated."""
    text = re.sub(r"\s+", " ", content or "").strip()
    if not text:
        return title
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    return cut[: end + 1] if end > 80 else cut.rsplit(" ", 1)[0] + "…"


@dataclass
class Candidate:
    title: str
    url: str
    content: str
    score: float
    published: datetime
    hint: str
    image_url: str | None = None
    image_source: str | None = None


_STOP = {"a", "an", "the", "of", "to", "in", "on", "for", "and", "by", "with", "at", "as", "its", "is", "after", "over", "from"}
_UNITS = (("million", "m"), ("billion", "b"), ("thousand", "k"))


def _tokens(title: str, subject: str) -> frozenset[str]:
    t = title.lower()
    for word, short in _UNITS:  # "$48 million" == "$48M"
        t = re.sub(rf"(\d)\s*{word}\b", rf"\1{short}", t)
    subj = {w for w in re.split(r"\W+", subject.lower()) if w}
    return frozenset(w for w in re.split(r"\W+", t) if w and w not in _STOP and w not in subj)


def _same_story(a: Candidate, b: Candidate, subject: str) -> bool:
    if SequenceMatcher(None, _title_key(a.title), _title_key(b.title)).ratio() >= 0.88:
        return True
    ta, tb = _tokens(a.title, subject), _tokens(b.title, subject)
    smaller = min(len(ta), len(tb))
    # Subject name and stopwords are removed first, so "X sued by supplier" and
    # "X sued by regulator" (1/2 shared) stay separate while a headline and its longer
    # rewrite (all content words shared) merge.
    return smaller >= 3 and len(ta & tb) / smaller >= 0.9


def dedupe(cands: list[Candidate], subject: str = "") -> tuple[list[Candidate], int]:
    ordered = sorted(cands, key=lambda c: (-c.score, -c.published.timestamp()))
    kept: list[Candidate] = []
    urls: set[str] = set()
    for c in ordered:
        nu = normalize_url(c.url)
        if nu in urls or any(_same_story(c, k, subject) for k in kept):
            continue
        urls.add(nu)
        kept.append(c)
    return kept, len(cands) - len(kept)


def impact_for(category: str, score: float) -> int:
    base = 2 if category in HIGH_IMPACT else 1
    if score >= 0.8:
        base += 1
    elif score < 0.4:
        base -= 1
    return max(1, min(3, base))


def source_name(url: str) -> str:
    return urlsplit(url).netloc.lower().removeprefix("www.") or "unknown"


# ----------------------------------------------------------------- pipeline --
async def run_research(
    req: BriefingRequest, client: TavilyClient, *, now: datetime | None = None, max_results: int = 8
) -> BriefingResult:
    # Stage 4: prefer meeting_at as the window anchor when provided
    if getattr(req, "meeting_at", None):
        try:
            from app.services.research_pipeline.window import compute_window, parse_meeting_at

            meeting_dt = parse_meeting_at(req.meeting_at)  # type: ignore[arg-type]
            start, end, _ = compute_window(meeting_dt, int(req.days))
            now = end
            start_floor = start
        except ValueError:
            now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
            start = now - timedelta(days=req.days)
            start_floor = start.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        start = now - timedelta(days=req.days)
        start_floor = start.replace(hour=0, minute=0, second=0, microsecond=0)
    type_ = resolve_type(req.subject, req.type)
    queries = build_queries(req.subject, type_, req.focus)

    async def _news_search(q: Query):
        return await client.search_full(
            q.text,
            topic="news",
            start_date=start_floor.strftime("%Y-%m-%d"),
            end_date=now.strftime("%Y-%m-%d"),
            max_results=max_results,
            include_images=True,
            include_image_descriptions=False,
        )

    results = await asyncio.gather(
        *(_news_search(q) for q in queries),
        return_exceptions=True,
    )
    failures = [r for r in results if isinstance(r, Exception)]
    if len(failures) == len(queries):
        first = failures[0]
        raise first if isinstance(first, UpstreamError) else UpstreamError()

    raw_count = undated = off_topic = out_of_window = 0
    cands: list[Candidate] = []
    for q, res in zip(queries, results):
        if isinstance(res, Exception):
            continue
        rows = res.get("results") if isinstance(res, dict) else res
        if not isinstance(rows, list):
            continue
        for hit in rows:
            if not isinstance(hit, dict):
                continue
            raw_count += 1
            url, title = hit.get("url"), (hit.get("title") or "").strip()
            if not url or not title:
                continue
            content = hit.get("content") or ""
            published = parse_published(
                hit.get("published_date") or hit.get("publishedDate") or hit.get("date")
            )
            if published is None:
                undated += 1  # never guess a date
                continue
            if published > now + timedelta(days=1) or published < start_floor:
                out_of_window += 1
                continue
            if not is_relevant(req.subject, title, content):
                off_topic += 1
                continue
            # Prefer source-linked images from this article only
            thumb = None
            imgs = hit.get("images") or []
            if imgs:
                first_img = imgs[0]
                if isinstance(first_img, str) and first_img.startswith("http"):
                    thumb = first_img
                elif isinstance(first_img, dict):
                    u = (first_img.get("url") or "").strip()
                    if u.startswith("http"):
                        thumb = u
            cands.append(
                Candidate(
                    title,
                    url,
                    content,
                    float(hit.get("score") or 0.0),
                    published,
                    q.category,
                    image_url=thumb,
                    image_source=source_name(url) if thumb else None,
                )
            )

    kept, dupes = dedupe(cands, req.subject)
    kept.sort(key=lambda c: c.published, reverse=True)

    # Cluster near-duplicates for UI (cluster_id on survivors that shared a story)
    news: list[NewsItem] = []
    for i, c in enumerate(kept):
        cat = classify(f"{c.title} {c.content}", c.hint)
        # Sentiment/impact are keyword heuristics — labelled as interpretation
        news.append(
            NewsItem(
                id=f"n-{i}",
                headline=c.title,
                summary=summarize(c.content, c.title),
                why_it_matters=CATEGORY_WHY.get(cat, CATEGORY_WHY["analysis"]),
                source=source_name(c.url),
                source_url=c.url,
                published_at=iso_z(c.published),
                category=cat,  # type: ignore[arg-type]
                sentiment=sentiment_of(c.title, c.content),  # type: ignore[arg-type]
                impact=impact_for(cat, c.score),  # type: ignore[arg-type]
                entities=[req.subject],
                in_window=True,
                image_url=c.image_url,
                image_source=c.image_source,
                cluster_id=f"c-{i}",
                relevance_score=round(min(1.0, max(0.0, c.score)), 3),
                is_interpretation=True,
            )
        )
    top = sorted((n for n in news if n.impact == 3), key=lambda n: n.published_at, reverse=True)[:3]
    for n in top:
        n.is_key = True

    # Visual profile (company/person images) — parallel-safe after news
    images = []
    try:
        images = await discover_images(client, req.subject, type_)
    except Exception:
        images = []

    stats = derive.build_stats(news)
    sources = [
        SourceEntry(
            id=f"s-{n.id}",
            name=n.source,
            url=n.source_url,
            published_at=n.published_at,
            headline=n.headline,
            category=n.category,
            in_window=n.in_window,
        )
        for n in news
    ]
    outlets = sorted({n.source for n in news})
    grounding = [
        f"{stats.articles} news items published within the last {req.days} days from {stats.sources} outlets, retrieved via Tavily on {now.strftime('%Y-%m-%d')}.",
        f"{len(queries)} searches run; {len(failures)} failed." if failures else f"{len(queries)} searches run.",
        f"{dupes} duplicate or near-duplicate results merged; {off_topic} off-topic and {out_of_window} out-of-window results excluded.",
        f"{undated} results had no publication date and were excluded rather than guessed.",
        f"Source diversity: {len(outlets)} unique outlets." if outlets else "No outlets in window.",
        "Sentiment and impact scores are keyword heuristics, not objective measures.",
        f"{len(images)} subject images retrieved with attribution metadata." if images else "No subject images retrieved.",
    ]
    slug = re.sub(r"[^a-z0-9]+", "-", req.subject.lower()).strip("-") or "subject"
    return BriefingResult(
        id=f"b-{slug}-{int(now.timestamp() * 1000)}",
        subject=req.subject,
        type=type_,
        generated_at=iso_z(now),
        window_days=req.days,
        window_start=iso_z(start),
        window_end=iso_z(now),
        snapshot=Snapshot(
            type=type_,
            name=req.subject,
            tagline="Live coverage briefing",
            tags=[],
            facts=[],
            key_people=[],
            watchlist=[],
        ),
        news=news,
        signals=[],
        talking_points=[],
        questions=[],
        sources=sources,
        sentiment_trend=derive.build_trend(news, req.days, now),
        coverage=derive.build_coverage(news),
        stats=stats,
        grounding=grounding,
        synthetic=False,
        images=images or None,
    )

