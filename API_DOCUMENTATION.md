# PreBrief API — Final (Stage 3)

Base: `/api/v1` · Version 3.0.0

## Research

`POST /research` — entity research with optional `research_depth`, `subject_url`, `research_question`.

`GET|DELETE /research/sessions[/{id}]` — library.

## Chat & compare

`POST /chat` — grounded answers.

`POST /compare` — `{ left_session_id, right_session_id, focus? }`.

## Reports (Stage 3)

`POST /reports/generate`

```json
{
  "research_session_id": "rs-...",
  "format": "pdf",
  "title": "Acme — Q4 brief",
  "include_sources": true,
  "include_timeline": true,
  "include_intelligence": true,
  "meeting_context": "Partnership review",
  "save": true
}
```

Formats: `pdf` | `json` | `csv` | `markdown` | `html`

`GET /reports` — saved reports for the session.

`GET /reports/{id}?format=pdf` — re-download.

`PATCH /reports/{id}?title=...` — rename.

`DELETE /reports/{id}`.

## One-pager

`POST /one-pager`, `POST /one-pager/pdf` — A4 meeting brief.

## Documents

Upload / list / get / delete under anonymous session ownership.

Full interactive schema: `/api/v1/docs`.
