# PreBrief API

Base URL: `http://127.0.0.1:8000/api/v1`  
JSON fields use camelCase on the wire (`response_model_by_alias`).

## Health

`GET /health` → `{ "status": "ok", "api": "v1" }`

## One-page brief (primary deliverable)

### `POST /one-pager`

```json
{
  "entityName": "Acme Robotics",
  "entityType": "company",
  "meetingAt": "2026-11-12T10:00:00Z",
  "meetingContext": "Partnership discussion",
  "windowDays": 30
}
```

Returns structured one-page brief with sections A–D, citation list, limitations.

### `POST /one-pager/pdf`

Same body → `application/pdf` attachment (A4, one page, clickable links).

### `POST /one-pager/json`

Same body → brief + full research payload for debugging.

## Research (Stage 4)

### `POST /research`

```json
{
  "entityName": "Jane Doe",
  "entityType": "person",
  "meetingAt": "2026-11-12",
  "windowDays": 30
}
```

Meeting date drives the inclusive 30-day window. Undated articles are excluded.

## Briefing (extended dossier)

### `POST /briefing`

```json
{
  "subject": "Acme Robotics",
  "type": "company",
  "days": 30,
  "meetingAt": "2026-11-12T10:00:00Z",
  "focus": "funding"
}
```

## Auth

`POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `GET /auth/me`, …

Access token: `Authorization: Bearer <token>`  
Refresh: HttpOnly cookie.

## Errors

```json
{ "error": { "code": "validation_error", "message": "…", "requestId": "…" } }
```

Keys and upstream secrets are never returned to the client.
