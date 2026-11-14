# Known limitations (Final)

1. **Live research** requires `BRIEFING_MODE=live` and a valid `TAVILY_API_KEY`. Stub mode returns empty findings with explicit gap messages and never fabricates news.
2. **SQLite** is the default database for local/demo use. Set `DATABASE_URL` for production deployments.
3. **Frontend wiring**: Export and compare UIs exist; ensure they pass `research_session_id` values to `/reports/generate` and `/compare` when integrating deeply.
4. **OCR** for scanned PDFs is optional (`ENABLE_OCR`) and requires system tesseract.
5. **Rate limiting** depends on optional `slowapi` package.
6. **Anonymous sessions** expire after `ANONYMOUS_SESSION_TTL_DAYS` (default 30).
7. Chat is evidence-retrieval based over stored findings (no mandatory LLM). Optional Gemini key is reserved for future enrichment.
