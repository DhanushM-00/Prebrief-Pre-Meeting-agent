"""Stage 7: precise 30×24h window and timezone handling."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.services.research_pipeline.window import compute_window, in_window, parse_meeting_at


def test_exact_30x24h_lookback():
    meeting = parse_meeting_at("2026-11-12T10:00:00+05:30")
    start, end, note = compute_window(meeting, 30)
    assert end == meeting.astimezone(timezone.utc)
    assert end - start == timedelta(days=30)
    assert "30×24h" in note or "30x24h" in note.lower() or "30" in note


def test_kolkata_offset_preserved_as_utc_instant():
    # 10:00 IST = 04:30 UTC
    meeting = parse_meeting_at("2026-11-12T10:00:00+05:30")
    assert meeting.hour == 4 and meeting.minute == 30
    start, end, _ = compute_window(meeting, 30)
    assert end.isoformat().startswith("2026-11-12T04:30:00")


def test_utc_meeting():
    meeting = parse_meeting_at("2026-11-12T10:00:00Z")
    start, end, _ = compute_window(meeting, 30)
    assert end == datetime(2026, 11, 12, 10, 0, tzinfo=timezone.utc)
    assert start == datetime(2026, 10, 13, 10, 0, tzinfo=timezone.utc)


def test_us_eastern_offset():
    meeting = parse_meeting_at("2026-07-01T09:00:00-04:00")
    start, end, _ = compute_window(meeting, 30)
    assert end - start == timedelta(days=30)
    # 09:00 EDT = 13:00 UTC
    assert end.hour == 13


def test_no_extra_calendar_day():
    """Calendar-day window would include midnight of start day earlier; exact lookback does not."""
    meeting = parse_meeting_at("2026-11-12T10:00:00Z")
    start, end, _ = compute_window(meeting, 30)
    just_before = start - timedelta(seconds=1)
    assert not in_window(just_before, start, end)
    assert in_window(start, start, end)
    assert in_window(end, start, end)
    assert not in_window(end + timedelta(seconds=1), start, end)


def test_future_article_excluded():
    meeting = parse_meeting_at("2026-11-12T10:00:00Z")
    start, end, _ = compute_window(meeting, 30)
    future = end + timedelta(hours=1)
    assert not in_window(future, start, end)


def test_undated_excluded():
    meeting = parse_meeting_at("2026-11-12T10:00:00Z")
    start, end, _ = compute_window(meeting, 30)
    assert not in_window(None, start, end)


def test_naive_treated_as_utc():
    meeting = parse_meeting_at("2026-11-12T10:00:00")
    assert meeting.tzinfo is not None
    assert meeting.utcoffset() == timedelta(0)
