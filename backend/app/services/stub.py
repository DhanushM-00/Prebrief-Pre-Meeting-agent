"""Stub mode: a tiny, obviously fake briefing so the frontend can be wired without API credits."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.schemas.briefing import BriefingRequest, BriefingResult, NewsItem, Snapshot, SourceEntry
from app.services import derive
from app.services.research import iso_z, resolve_type


def build_stub(req: BriefingRequest, now: datetime | None = None) -> BriefingResult:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    type_ = resolve_type(req.subject, req.type)
    news = [
        NewsItem(
            id=f"n-{i}", headline=f"[stub] Placeholder item {i + 1} about {req.subject}",
            summary="Stub data from BRIEFING_MODE=stub. Not real coverage.",
            why_it_matters="Exists only to exercise the interface.", source="stub.local",
            published_at=iso_z(now - timedelta(days=i * 2 + 1)), category=cat, sentiment=sent, impact=imp,
            entities=[req.subject], in_window=True, is_key=(i == 0),
        )
        for i, (cat, sent, imp) in enumerate([("funding", "positive", 3), ("product", "neutral", 2), ("litigation", "negative", 2)])
    ]
    return BriefingResult(
        id=f"b-stub-{int(now.timestamp() * 1000)}", subject=req.subject, type=type_,
        generated_at=iso_z(now), window_days=req.days, window_start=iso_z(now - timedelta(days=req.days)),
        window_end=iso_z(now),
        snapshot=Snapshot(type=type_, name=req.subject, tagline="Stub briefing", tags=[], facts=[], key_people=[], watchlist=[]),
        news=news, signals=[], talking_points=[], questions=[],
        sources=[SourceEntry(id=f"s-{n.id}", name=n.source, published_at=n.published_at, headline=n.headline,
                             category=n.category, in_window=True) for n in news],
        sentiment_trend=derive.build_trend(news, req.days, now), coverage=derive.build_coverage(news),
        stats=derive.build_stats(news), grounding=["Stub data (BRIEFING_MODE=stub)."], synthetic=True,
    )
