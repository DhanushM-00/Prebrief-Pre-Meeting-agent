# PreBrief — Windows setup (PowerShell)

PreBrief runs without accounts. An anonymous session cookie isolates your documents and research.

## Prerequisites

- Python 3.11 or 3.12
- Node.js 20+
- (Optional) Tavily API key for live research

## Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env:
#   BRIEFING_MODE=stub          # or live
#   TAVILY_API_KEY=...          # required when BRIEFING_MODE=live
#   ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
python -c "from app.db import init_db; init_db()"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check: http://127.0.0.1:8000/api/v1/health

## Frontend

```powershell
cd frontend
copy .env.example .env
# Ensure: VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
npm ci
npm run dev
```

Open http://127.0.0.1:5173 — the app loads directly (no login).

## Troubleshooting

| Symptom | Fix |
|--------|-----|
| CORS errors | Confirm both origins in backend `ALLOWED_ORIGINS` |
| "Backend is not configured" | Set `VITE_API_BASE_URL` in `frontend/.env` and restart Vite |
| Research provider unavailable | Set `TAVILY_API_KEY` and `BRIEFING_MODE=live` |
| Session lost after restart | Expected for SQLite prototype after DB wipe; cookie is re-minted |
| PDF empty / stub gaps | Live mode needs a valid Tavily key |

No login credentials are required.
