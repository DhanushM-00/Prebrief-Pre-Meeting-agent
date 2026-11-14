# PreBrief — AI Research & Intelligence Platform

PreBrief is an AI-assisted research workspace for investigating companies and people, organizing evidence, preparing meeting briefs, and exporting professional reports.

It combines a React frontend with a FastAPI backend. Research can use live web search through Tavily or run in stub mode for local development without external research calls.

> **Current release:** 3.0.0 — Stage 1 + Stage 2 + Stage 3 final product

## Highlights

### Research and intelligence
- Research companies, people, or automatically detected entity types.
- Choose **Quick**, **Standard**, or **Deep** research depth.
- Set a meeting-date research window and provide a research question or URL.
- Use Tavily for live web research, with source verification and evidence-oriented findings.
- Review claims, confidence labels, evidence items, timelines, intelligence profiles, and open questions.
- Ask follow-up questions in an evidence-grounded research chat.
- Save, reopen, list, and delete research sessions.
- Compare company research sessions or person research sessions.

### Briefings and exports
- Generate multi-page PDF research reports with a cover, findings, intelligence, timeline, sources, and methodology.
- Create a one-page A4 meeting brief and export it as PDF.
- Export reports as **PDF, JSON, CSV, Markdown, or print-ready HTML**.
- Manage saved reports: list, rename, download again, and delete.
- Configure report sections such as sources, timeline, intelligence, and meeting context.

### Documents and application
- Upload supported documents and ask questions grounded in their contents.
- Responsive React user interface.
- FastAPI REST API.
- SQLite database by default for local development.
- Anonymous session ownership; a login is not required for the default workflow.

## Tech stack

| Area | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite |
| UI / charts | Tailwind CSS, Lucide React, Recharts |
| Backend | Python, FastAPI, Pydantic |
| Database | SQLAlchemy, SQLite by default |
| Research provider | Tavily (optional, for live research) |
| PDF generation | ReportLab |
| Document processing | pypdf and document extraction pipeline |
| Testing | pytest |

## Project structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/v1/             # REST API routes
│   │   ├── core/               # Security, errors, rate limiting
│   │   ├── models/             # Database models
│   │   ├── schemas/            # Request and response schemas
│   │   └── services/
│   │       ├── documents/      # Upload, extraction, indexing, retrieval
│   │       ├── one_pager/      # One-page brief generation and PDF
│   │       ├── reports/        # Report generation and export formats
│   │       └── research_pipeline/ # Research, claims, verification, entity resolution
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── package.json
│   └── .env.example
├── API_DOCUMENTATION.md
├── SETUP.md
├── TEST_RESULTS.md
└── KNOWN_LIMITATIONS.md
```

## Requirements

- Python **3.11 or newer**
- Node.js **18 or newer**
- npm
- A Tavily API key only if you want live web research

## Getting started

Run the backend and frontend in separate terminal windows.

### 1. Clone the repository

```bash
git clone https://github.com/DhanushM-00/Prebrief-Pre-Meeting-agent
cd Prebrief-Pre-Meeting-agent
```

### 2. Configure and start the backend

Create and activate a virtual environment:

**macOS / Linux**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
```

**Windows PowerShell**
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies and create the environment file:

```bash
pip install -r requirements.txt
```

Copy `backend/.env.example` to `backend/.env`, then configure it as needed.

Start the API from the `backend` directory:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at:

- API base: `http://127.0.0.1:8000/api/v1`
- Interactive API docs: `http://127.0.0.1:8000/api/v1/docs`

### 3. Configure and start the frontend

In a second terminal:

```bash
cd frontend
```

Copy `frontend/.env.example` to `frontend/.env`. The default API URL is:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Install dependencies and run the development server:

```bash
npm ci
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`).

## Research configuration

PreBrief supports two backend research modes.

### Stub mode (default)

```env
BRIEFING_MODE=stub
```

Stub mode is intended for development and UI testing. It does not make live research calls and does not fabricate news or findings; unavailable research is represented through explicit gaps.

### Live Tavily research

In `backend/.env`:

```env
BRIEFING_MODE=live
TAVILY_API_KEY=your_tavily_api_key
TAVILY_BASE_URL=https://api.tavily.com
TAVILY_TIMEOUT_SECONDS=20
TAVILY_MAX_RESULTS=8
```

Restart the backend after changing environment variables. Keep API keys private and never commit `.env` files or real credentials.

## Environment variables

The full list and defaults are documented in `backend/.env.example`. Common settings include:

| Variable | Purpose |
|---|---|
| `APP_ENV` | Application environment |
| `ALLOWED_ORIGINS` | Allowed frontend origins |
| `BRIEFING_MODE` | `stub` or `live` research mode |
| `TAVILY_API_KEY` | Tavily API key for live research |
| `DATABASE_URL` | SQLAlchemy database URL; SQLite by default |
| `ANONYMOUS_SESSION_TTL_DAYS` | Anonymous session lifetime |
| `UPLOAD_DIR` | Uploaded document storage directory |
| `MAX_UPLOAD_BYTES` | Maximum individual upload size |
| `MAX_FILES_PER_USER` | Per-session file count limit |
| `MAX_STORAGE_BYTES_PER_USER` | Per-session storage limit |
| `ALLOWED_EXTENSIONS` | Accepted document extensions |
| `ENABLE_OCR` | Enable optional OCR for scanned PDFs |
| `GEMINI_API_KEY` | Reserved optional enrichment configuration |

## API overview

The API is versioned under `/api/v1`. Main route groups include:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/research` | Start research with entity, depth, date window, question, and optional URL |
| `GET` / `DELETE` | `/research/sessions` and `/research/sessions/{id}` | List and manage research sessions |
| `POST` | `/chat` | Ask questions against stored research evidence |
| `POST` | `/compare` | Compare two research sessions |
| `POST` | `/reports/generate` | Generate PDF, JSON, CSV, Markdown, or HTML report |
| `GET` | `/reports` | List saved reports |
| `GET` / `PATCH` / `DELETE` | `/reports/{id}` | Retrieve, rename, or delete a saved report |
| `POST` | `/one-pager` | Generate a one-page meeting brief |
| `POST` | `/one-pager/pdf` | Export the one-page brief as PDF |
| `GET` | `/health` | Health check |

For exact request and response schemas, see [`API_DOCUMENTATION.md`](API_DOCUMENTATION.md) or open the interactive Swagger documentation while the backend is running.

## Running tests

From the `backend` directory with the virtual environment activated:

```bash
BRIEFING_MODE=stub pytest -q
```

On Windows PowerShell:

```powershell
$env:BRIEFING_MODE = "stub"
pytest -q
```

Frontend type-check and production build:

```bash
cd frontend
npm run typecheck
npm run build
```

See [`TEST_RESULTS.md`](TEST_RESULTS.md) for the project's recorded test information.

## Known limitations

- Live research requires `BRIEFING_MODE=live` and a valid Tavily API key.
- Stub mode intentionally returns no live findings and does not invent information.
- SQLite is the default for local/demo use. Configure `DATABASE_URL` for another supported SQLAlchemy database in a deployment.
- OCR for scanned PDFs is optional. Enabling it requires the relevant Python packages and a system Tesseract installation.
- Rate limiting depends on the optional `slowapi` package.
- Anonymous sessions expire after the configured TTL (30 days by default).
- Chat retrieves answers from stored research findings; a mandatory LLM is not required. Gemini configuration is reserved for optional/future enrichment.
- Review [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) for the maintained project notes.

## Security notes

- Do not commit `.env` files, API keys, database files containing private data, or uploaded documents.
- Configure `ALLOWED_ORIGINS`, secure cookie settings, and a production database before public deployment.
- Set `SESSION_COOKIE_SECURE=true` when serving over HTTPS.
- Apply appropriate authentication, authorization, backup, and storage policies before using the application with sensitive or production data.

## Documentation

- [`SETUP.md`](SETUP.md) — setup instructions
- [`API_DOCUMENTATION.md`](API_DOCUMENTATION.md) — API reference
- [`API.md`](API.md) — API notes
- [`TEST_RESULTS.md`](TEST_RESULTS.md) — test results
- [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) — known limitations
- [`WINDOWS_SETUP.md`](WINDOWS_SETUP.md) — Windows-specific setup

## License

No license file is included in this project package. Add a `LICENSE` file before publishing if you want to grant others explicit permission to use, modify, and distribute the project.
