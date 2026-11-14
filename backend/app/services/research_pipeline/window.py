"""Meeting-timestamp research window helpers.

Convention (documented on every ResearchResult and PDF):
  window_end   = meeting timestamp (inclusive)
  window_start = meeting timestamp minus exactly window_days × 24 hours (inclusive)
  Example: meeting 2026-11-12T10:00:00+05:30 → start = meeting - 30 days at the same clock time.

Rules:
- Naive datetimes (no offset) are treated as UTC and callers should send an explicit offset.
- Publication times are compared in UTC.
- Articles without a parseable publication date are undated and excluded from verified findings.
- Articles strictly after window_end are excluded (no future articles relative to the meeting).
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone


def parse_meeting_at(raw: str) -> datetime:
    """Parse ISO-8601 date or datetime.

    - Date-only (YYYY-MM-DD): interpreted as end of that calendar day in UTC.
    - Datetime with Z or numeric offset: converted to UTC, original offset preserved via conversion.
    - Naive datetime (no offset): treated as UTC (callers should prefer explicit offsets).
    """
    s = (raw or "").strip()
    if not s:
        raise ValueError("meeting_at is required")
    # Date only → end of that UTC day
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        d = date.fromisoformat(s)
        return datetime.combine(d, time(23, 59, 59), tzinfo=timezone.utc)
    try:
        # Support trailing Z
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValueError(f"Invalid meeting_at: {raw}") from e
    if dt.tzinfo is None:
        # Explicit policy: naive → UTC (frontend must send offset for local times)
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def compute_window(meeting_at: datetime, window_days: int = 30) -> tuple[datetime, datetime, str]:
    """Exact window_days × 24h lookback ending at the meeting timestamp.

    Returns (window_start, window_end, convention_note). Both bounds are inclusive.
    """
    if meeting_at.tzinfo is None:
        meeting_at = meeting_at.replace(tzinfo=timezone.utc)
    end = meeting_at.astimezone(timezone.utc)
    start = end - timedelta(days=window_days)
    note = (
        f"Inclusive {window_days}×24h lookback: {start.isoformat().replace('+00:00', 'Z')} "
        f"through {end.isoformat().replace('+00:00', 'Z')} (meeting timestamp). "
        "Undated articles are excluded from verified findings; articles after the meeting are excluded."
    )
    return start, end, note


def in_window(published: datetime | None, start: datetime, end: datetime) -> bool:
    """True only when published is known and within [start, end] inclusive (UTC)."""
    if published is None:
        return False
    p = published if published.tzinfo else published.replace(tzinfo=timezone.utc)
    p = p.astimezone(timezone.utc)
    s = start if start.tzinfo else start.replace(tzinfo=timezone.utc)
    e = end if end.tzinfo else end.replace(tzinfo=timezone.utc)
    return s.astimezone(timezone.utc) <= p <= e.astimezone(timezone.utc)


def format_window_display(start: datetime, end: datetime) -> str:
    """Human-readable UTC range for PDFs and UI."""
    s = start.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    e = end.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"{s} – {e}"
