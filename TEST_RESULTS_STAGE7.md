# Stage 7 test log

Executed 2026-11-12 against the fixed codebase.

## Window / timezone
- PASS Kolkata +05:30 → UTC instant 04:30
- PASS Exact 30×24h lookback (end - start == 30 days)
- PASS UTC meeting start/end alignment
- PASS Future articles excluded
- PASS Undated excluded
- PASS US Eastern -04:00 delta and UTC hour

## PDF / citations
- PASS Company PDF generated, fits one page, has [n] markers and entity name
- PASS Person PDF generated, fits one page
- PASS Unsupported claim stripped by validation

## Auth wiring
- Research / one-pager / briefing endpoints require `CurrentUser`
- Research session reuse checks `user_id` ownership (403 if mismatch)

## Frontend
- `datetime-local` converted with explicit timezone offset (no bare `Z`)

Live Tavily scenarios require `TAVILY_API_KEY` and were not exercised in this offline log.
