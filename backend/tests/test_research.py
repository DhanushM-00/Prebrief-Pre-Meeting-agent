import asyncio
import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.core.errors import UpstreamError
from app.schemas import BriefingRequest, BriefingResult
from app.services import derive
from app.services.cache import SearchCache
from app.services.research import (
    build_queries, normalize_url, parse_published, resolve_type, run_research, sentiment_of, summarize,
)
from app.services.tavily_client import TavilyClient

NOW = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)


def ago(days: float) -> str:
    return (NOW - timedelta(days=days)).strftime("%a, %d %b %Y %H:%M:%S GMT")  # RFC-2822 style


def hit(title, url, days=3, content="Helio Grid said on Monday it would expand.", score=0.7, **extra):
    h = {"title": title, "url": url, "content": content, "score": score}
    if days is not None:
        h["published_date"] = ago(days)
    return {**h, **extra}


def make_client(handler, **kw):
    return TavilyClient("tvly-test", transport=httpx.MockTransport(handler), backoff=0, **kw)


def respond(results):
    return lambda request: httpx.Response(200, json={"results": results})


def run(coro):
    return asyncio.run(coro)


REQ = BriefingRequest(subject="Helio Grid", type="company", days=30)


# ------------------------------------------------------------------ helpers --
def test_parse_published_formats():
    assert parse_published("2026-10-28T07:30:00Z") == datetime(2026, 10, 28, 7, 30, tzinfo=timezone.utc)
    assert parse_published("2026-10-28") == datetime(2026, 10, 28, tzinfo=timezone.utc)
    assert parse_published("Tue, 28 Oct 2026 07:30:00 GMT") == datetime(2026, 10, 28, 7, 30, tzinfo=timezone.utc)
    assert parse_published("yesterday-ish") is None and parse_published(None) is None and parse_published("") is None


def test_normalize_url_strips_tracking_and_www():
    assert normalize_url("https://www.Example.com/a/?utm_source=x&id=2#top") == "https://example.com/a?id=2"


def test_summary_is_an_excerpt_of_source_text():
    text = "First sentence here. " + "word " * 100
    out = summarize(text, "T")
    assert len(out) <= 281
    assert text.startswith(out.rstrip("…").rstrip())          # a prefix of the source: nothing generated
    assert summarize("Short.", "T") == "Short."
    assert summarize("", "Fallback title") == "Fallback title"
    # prefers a sentence boundary once the excerpt is substantial (>80 chars); ignores tiny first sentences
    long_first = "This opening sentence is deliberately long enough to be a worthwhile summary on its own merits here. "
    assert summarize(long_first + "x " * 200, "T").endswith("merits here.")
    assert summarize("Tiny. " + "x " * 200, "T").endswith("…")


def test_sentiment_heuristic():
    assert sentiment_of("Helio Grid raises $48M", "") == "positive"
    assert sentiment_of("Helio Grid sued over fraud", "") == "negative"
    assert sentiment_of("Helio Grid names new office", "") == "neutral"


def test_type_resolution_is_conservative():
    assert resolve_type("Dr. Ada Chen", "auto") == "person"
    assert resolve_type("Helio Grid", "auto") == "company"
    assert resolve_type("Helio Grid", "person") == "person"


def test_focus_queries_come_first_and_total_is_capped():
    qs = build_queries("Acme", "company", "India expansion, litigation, fundraising, extra, more")
    assert qs[0].text == "Acme India expansion" and len(qs) <= 8
    assert len({q.text for q in qs}) == len(qs)


# ----------------------------------------------------------------- pipeline --
def test_window_enforced_and_unreliable_results_excluded():
    results = [
        hit("Helio Grid raises $48M Series B", "https://reuters.com/a", days=2),
        hit("Helio Grid old news", "https://x.com/old", days=45),                 # outside window
        hit("Helio Grid from the future", "https://x.com/future", days=-10),      # impossible date
        hit("Helio Grid undated piece", "https://x.com/undated", days=None),      # no date: never guessed
        hit("Unrelated company wins", "https://x.com/other", content="Nothing about the subject."),
    ]
    b = run(run_research(REQ, make_client(respond(results)), now=NOW))
    assert [n.headline for n in b.news] == ["Helio Grid raises $48M Series B"]
    assert all(n.in_window for n in b.news)
    text = " ".join(b.grounding)
    assert "1 had no publication date" not in text and "had no publication date and were excluded" in text
    BriefingResult.model_validate(b.model_dump(mode="json", by_alias=True))  # valid contract output


def test_dedupe_by_url_and_title_across_queries():
    results = [
        hit("Helio Grid raises $48M Series B", "https://www.reuters.com/a?utm_source=tw", score=0.9),
        hit("Helio Grid raises $48M Series B", "https://reuters.com/a", score=0.5),           # same URL
        hit("Helio Grid raises $48 million Series B", "https://other.com/b", score=0.4),      # near-identical title
        hit("Helio Grid opens Berlin office", "https://news.com/c", score=0.6),
    ]
    b = run(run_research(REQ, make_client(respond(results)), now=NOW))
    assert len(b.news) == 2
    assert b.news[0].source_url and b.news[0].source_url.startswith("http")  # real URLs, never fabricated


def test_items_sorted_newest_first_with_stable_ids_and_consistent_stats():
    results = [
        hit("Helio Grid launches grid tool", "https://a.com/1", days=10),
        hit("Helio Grid sued by supplier", "https://b.com/2", days=1),
        hit("Helio Grid raises $48M", "https://c.com/3", days=5, score=0.9),
    ]
    b = run(run_research(REQ, make_client(respond(results)), now=NOW))
    assert [n.id for n in b.news] == ["n-0", "n-1", "n-2"]
    assert [n.published_at for n in b.news] == sorted((n.published_at for n in b.news), reverse=True)
    assert b.stats == derive.build_stats(b.news)
    assert len(b.sentiment_trend) == 30
    ids = {n.id for n in b.news}
    assert {s.id for s in b.sources} == {f"s-{i}" for i in ids}
    assert b.synthetic is False


def test_ai_fields_left_empty_not_invented():
    b = run(run_research(REQ, make_client(respond([hit("Helio Grid raises $48M", "https://a.com/1")])), now=NOW))
    assert b.signals == [] and b.talking_points == [] and b.questions == []
    assert b.snapshot.facts == [] and b.snapshot.key_people == []


def test_request_sends_explicit_dates_not_relative_days():
    seen = []

    def handler(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"results": []})

    run(run_research(REQ, make_client(handler), now=NOW))
    assert seen and all(p["topic"] == "news" for p in seen)
    assert all(p["start_date"] == "2026-10-03" and p["end_date"] == "2026-11-02" for p in seen)
    assert all("days" not in p and "time_range" not in p for p in seen)


def test_partial_failure_degrades_gracefully():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if "funding" in json.loads(request.content)["query"]:
            return httpx.Response(400, json={})
        return httpx.Response(200, json={"results": [hit("Helio Grid launches tool", "https://a.com/1")]})

    b = run(run_research(REQ, make_client(handler), now=NOW))
    assert len(b.news) == 1 and "1 failed" in " ".join(b.grounding)


def test_all_searches_failing_raises_upstream_error():
    with pytest.raises(UpstreamError):
        run(run_research(REQ, make_client(lambda r: httpx.Response(400, json={})), now=NOW))


# ------------------------------------------------------------------- client --
def test_retries_transient_errors_then_succeeds():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(503) if calls["n"] < 3 else httpx.Response(200, json={"results": [{"a": 1}]})

    assert run(make_client(handler).search("q")) == [{"a": 1}] and calls["n"] == 3


def test_gives_up_after_max_attempts():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(429)

    with pytest.raises(UpstreamError):
        run(make_client(handler).search("q"))
    assert calls["n"] == 3


def test_bad_key_is_not_retried_and_never_leaks():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(401)

    with pytest.raises(UpstreamError) as e:
        run(make_client(handler).search("q"))
    assert calls["n"] == 1 and "tvly-test" not in e.value.message


def test_sends_bearer_auth_header():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["authorization"]
        return httpx.Response(200, json={"results": []})

    run(make_client(handler).search("q"))
    assert seen["auth"] == "Bearer tvly-test"


def test_cache_prevents_repeat_upstream_calls(tmp_path):
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(200, json={"results": [{"title": "t"}]})

    c = make_client(handler, cache=SearchCache(str(tmp_path / "c.db"), 3600))
    assert run(c.search("same", start_date="2026-10-01")) == run(c.search("same", start_date="2026-10-01"))
    assert calls["n"] == 1
    run(c.search("different"))
    assert calls["n"] == 2


def test_expired_cache_entries_are_refetched(tmp_path):
    cache = SearchCache(str(tmp_path / "c.db"), 0)
    cache.set("k", [1])
    import time; time.sleep(0.01)
    assert cache.get("k") is None


def test_malformed_provider_payload_is_an_upstream_error():
    with pytest.raises(UpstreamError):
        run(make_client(lambda r: httpx.Response(200, json={"results": "nope"})).search("q"))


def test_dedupe_merges_rewrites_but_not_distinct_stories():
    results = [
        hit("Helio Grid raises $48M Series B led by Northwind", "https://a.com/1", score=0.9),
        hit("Helio Grid raises $48 million Series B", "https://b.com/2", score=0.5),        # same story, rewritten
        hit("Helio Grid sued by supplier over contract", "https://c.com/3", score=0.6),
        hit("Helio Grid sued by regulator over disclosures", "https://d.com/4", score=0.6),  # different story
    ]
    b = run(run_research(REQ, make_client(respond(results)), now=NOW))
    heads = sorted(n.headline for n in b.news)
    assert len(b.news) == 3
    assert "Helio Grid sued by supplier over contract" in heads and "Helio Grid sued by regulator over disclosures" in heads
