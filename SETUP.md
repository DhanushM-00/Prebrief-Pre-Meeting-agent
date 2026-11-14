# PreBrief Final — Setup

## Requirements

- Python 3.11+
- Node.js 18+
- Optional: Tavily API key

## Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

## Frontend

```bash
cd frontend
cp .env.example .env
# VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
npm ci && npm run dev
```

## Live research

In `backend/.env`:

```
BRIEFING_MODE=live
TAVILY_API_KEY=tvly-...
```

## Generate a PDF after research

```bash
# After POST /research returns an id (and cookie is set):
curl -s -X POST http://127.0.0.1:8000/api/v1/reports/generate \
  -H 'Content-Type: application/json' \
  -b cookies.txt -c cookies.txt \
  -d '{"research_session_id":"rs-...","format":"pdf","save":true}' \
  -o report.pdf
```

## Tests

```bash
cd backend
BRIEFING_MODE=stub pytest -q
```
