"""Derived analytics, ported from buildTrend/buildCoverage/stats in src/lib/mock.ts.

tests/test_derive_parity.py proves this reproduces the frontend generator's output
for the same news list, so charts mean the same thing in demo and live mode.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from app.schemas.briefing import BriefingStats, CoverageSlice, NewsItem, SentimentPoint

SMOOTH_DAYS = 7  # trailing mean, so quiet days don't draw a false "neutral"
_VALUE = {"positive": 1, "neutral": 0, "negative": -1}


def _round2(x: float) -> float:
    # JS Number(x.toFixed(2)) rounds half away from zero on the decimal repr.
    return float(Decimal(repr(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def in_window(news: list[NewsItem]) -> list[NewsItem]:
    return [n for n in news if n.in_window]


def build_trend(news: list[NewsItem], days: int, end: datetime) -> list[SentimentPoint]:
    end = end.astimezone(timezone.utc)
    buckets: dict[str, list[int]] = {}  # date -> [score_sum, count]
    for i in range(days):
        buckets[(end - timedelta(days=i)).strftime("%Y-%m-%d")] = [0, 0]
    for n in in_window(news):
        b = buckets.get(n.published_at[:10])
        if b is None:
            continue
        b[0] += _VALUE[n.sentiment]
        b[1] += 1
    ordered = sorted(buckets.items())
    out: list[SentimentPoint] = []
    for idx, (date, b) in enumerate(ordered):
        window = ordered[max(0, idx - (SMOOTH_DAYS - 1)): idx + 1]
        total = sum(v[1] for _, v in window)
        s = sum(v[0] for _, v in window)
        out.append(SentimentPoint(date=date, score=_round2(s / total) if total else None, volume=b[1]))
    return out


def build_coverage(news: list[NewsItem]) -> list[CoverageSlice]:
    counts: dict[str, int] = {}
    for n in in_window(news):
        counts[n.category] = counts.get(n.category, 0) + 1
    # stable sort by count desc, first-seen order on ties (same as the JS Map + sort)
    return [CoverageSlice(category=c, count=k) for c, k in sorted(counts.items(), key=lambda kv: -kv[1])]


def build_stats(news: list[NewsItem]) -> BriefingStats:
    win = in_window(news)
    vals = [_VALUE[n.sentiment] for n in win]
    avg = sum(vals) / len(vals) if vals else 0.0
    return BriefingStats(
        articles=len(win),
        sources=len({n.source for n in win}),
        key_items=sum(1 for n in win if n.is_key),
        avg_sentiment=_round2(avg),
        days_covered=len({n.published_at[:10] for n in win}),
        categories_covered=len(build_coverage(news)),
    )
