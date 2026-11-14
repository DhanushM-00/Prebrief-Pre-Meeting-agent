"""Stage 4: meeting-window research, claim evidence, classification."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from app.services.research_pipeline.classification import classify_text
from app.services.research_pipeline.entity_resolution import (
    entity_mentioned,
    person_disambiguation_ok,
    resolve_entity_type,
)
from app.services.research_pipeline.window import compute_window, in_window, parse_meeting_at
from app.services.research_pipeline.claims import ClaimDraft, RawSource, extract_claims_from_source, merge_duplicate_claims
from app.services.research_pipeline.source_verification import assess_credibility


def test_meeting_window_example():
    """Meeting 12 Nov 2026 → window starts 13 Oct 2026 (30-day lookback)."""
    meeting = parse_meeting_at("2026-11-12")
    start, end, note = compute_window(meeting, 30)
    assert start.date() == date(2026, 10, 13)
    assert end.date() == date(2026, 11, 12)
    assert "Inclusive 30" in note


def test_window_uses_meeting_not_now():
    meeting = parse_meeting_at("2025-06-15T10:00:00Z")
    start, end, _ = compute_window(meeting, 30)
    assert end.date() == date(2025, 6, 15)
    assert start.date() == date(2025, 5, 16)


def test_in_window_bounds():
    meeting = parse_meeting_at("2026-11-12")
    start, end, _ = compute_window(meeting, 30)
    inside = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
    outside = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    assert in_window(inside, start, end)
    assert not in_window(outside, start, end)
    assert not in_window(None, start, end)


def test_entity_resolution():
    assert resolve_entity_type("Acme Robotics Inc", "auto") == "company"
    assert resolve_entity_type("Jane Doe", "person") == "person"
    assert entity_mentioned("Acme Robotics", "Acme Robotics raises series B", "")
    assert not entity_mentioned("Acme Robotics", "Unrelated industry note", "markets rose")


def test_person_disambiguation():
    assert person_disambiguation_ok(
        "Jane Doe", "Jane Doe appointed CEO of Acme", "executive leadership"
    )
    assert not person_disambiguation_ok(
        "Jane Doe", "Best restaurants near Jane Doe street", "food review"
    )


def test_classification():
    assert classify_text("Acme appoints new CEO", "") == "hires_and_leadership"
    assert classify_text("Acme launches new product line", "") == "product_and_service_launches"
    assert classify_text("Acme faces lawsuit over patents", "") == "risks_and_challenges"
    assert classify_text("Acme raises Series B funding", "") == "business_developments"


def test_claims_require_url_and_merge():
    src = RawSource(
        id="src-1",
        headline="Acme appoints Jane Doe as CEO",
        publisher="reuters.com",
        url="https://reuters.com/acme-ceo",
        published_at="2026-11-01T00:00:00Z",
        retrieved_at="2026-11-12T00:00:00Z",
        excerpt="Acme Robotics appointed Jane Doe as CEO effective November.",
        category="hires_and_leadership",
        target_entity="Acme",
        relevance_score=0.9,
        credibility="high",
        in_window=True,
        undated=False,
    )
    claims = extract_claims_from_source(src, "Acme")
    assert len(claims) == 1
    assert claims[0].source_ids == ["src-1"]
    assert assess_credibility("https://reuters.com/x") == "high"

    c2 = ClaimDraft(
        id="cl-2",
        statement=claims[0].statement,
        event_date="2026-11-01",
        category=claims[0].category,
        confidence="single_source",
        source_ids=["src-2"],
        is_interpretation=False,
    )
    merged = merge_duplicate_claims([claims[0], c2])
    assert len(merged) == 1
    assert set(merged[0].source_ids) == {"src-1", "src-2"}
    assert merged[0].confidence == "verified"


@pytest.mark.asyncio
async def test_stub_research_endpoint_window():
    """Exercise window path without Tavily using the service's parse helpers only."""
    meeting = parse_meeting_at("2026-11-12T09:00:00+05:30")
    start, end, _ = compute_window(meeting, 30)
    assert (end.date() - start.date()).days == 30
