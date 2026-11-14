# PreBrief backend (FastAPI)

Current state: contract models, error envelope, `/api/v1/health`, and `POST /api/v1/briefing` backed by Tavily
(Phase 3, interim scoring). No Gemini, accounts or persistent briefings yet -- read `../docs/PHASE3_NOTES.md` first.

    cd backend
    python -m venv .venv && . .venv/bin/activate
    pip install -r requirements-dev.txt
    pytest -q
    uvicorn app.main:app --reload      # http://localhost:8000/api/v1/health

Regenerate frontend-derived fixtures after changing the mock generator or `src/types.ts`:

    npx tsx scripts/export-fixtures.ts     # from the repo root

Run it against real Tavily (set your key in `backend/.env`, copied from `.env.example`):

    python scripts/smoke_tavily.py "Some Company"   # verify the live response shape (1 credit)
    uvicorn app.main:app --reload
    # frontend: VITE_API_BASE_URL=http://localhost:8000/api/v1 npm run dev

Use `BRIEFING_MODE=stub` to develop the UI without spending credits.
