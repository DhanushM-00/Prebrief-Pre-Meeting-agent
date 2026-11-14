"""Tests for the evidence-grounded chat agent."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import create_app
from app.db import init_db, engine, SessionLocal
from app.models.research import ResearchSession
from app.services.session import create_session_record
from app.config import get_settings


def _client():
    app = create_app()
    return TestClient(app)


def test_chat_without_session_returns_clear_message():
    client = _client()
    # Mint anonymous session via health or research
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    # Chat without prior research
    res = client.post(
        "/api/v1/chat",
        json={"question": "What are the risks?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert data.get("grounded") is False or "No research session" in data["answer"] or "not available" in data["answer"].lower()


def test_chat_with_stub_research_then_question():
    client = _client()
    # Ensure cookie is set
    client.get("/api/v1/health")
    # Create a stub research (BRIEFING_MODE defaults may vary; force via env is hard in test)
    # Instead insert a session directly
    from sqlalchemy.orm import sessionmaker
    # from app.db import get_engine

    # engine = get_engine()
    # SessionLocal already imported
    db = SessionLocal()
    try:
        # Get or create anonymous session from cookie path is complex; insert with known user_id
        # Use the cookie the TestClient will send after first request
        settings = get_settings()
        anon = create_session_record(db, settings)
        owner = anon.id

        payload = {
            "id": "rs-test-1",
            "entity_name": "Acme Corp",
            "entity_type": "company",
            "meeting_at": "2026-11-20T10:00:00Z",
            "window_start": "2026-10-21T00:00:00Z",
            "window_end": "2026-11-20T00:00:00Z",
            "window_days": 30,
            "window_convention": "inclusive",
            "findings": [
                {
                    "id": "f1",
                    "category": "risks_and_challenges",
                    "statement": "Acme Corp faces a regulatory investigation into data practices.",
                    "event_date": "2026-11-01",
                    "confidence": "supported",
                    "source_ids": ["s1"],
                    "sources": [],
                    "claims": [],
                },
                {
                    "id": "f2",
                    "category": "product_and_service_launches",
                    "statement": "Acme launched a new analytics product line.",
                    "event_date": "2026-10-28",
                    "confidence": "single_source",
                    "source_ids": ["s2"],
                    "sources": [],
                    "claims": [],
                },
            ],
            "sources": [
                {
                    "id": "s1",
                    "headline": "Regulator opens probe into Acme",
                    "publisher": "Reuters",
                    "url": "https://example.com/probe",
                    "published_at": "2026-11-01T12:00:00Z",
                    "retrieved_at": "2026-11-14T10:00:00Z",
                    "excerpt": "The regulator opened an investigation...",
                    "category": "risks_and_challenges",
                    "target_entity": "Acme Corp",
                    "relevance_score": 0.9,
                    "credibility": "high",
                    "in_window": True,
                    "undated": False,
                },
                {
                    "id": "s2",
                    "headline": "Acme launches analytics suite",
                    "publisher": "TechCrunch",
                    "url": "https://example.com/launch",
                    "published_at": "2026-10-28T09:00:00Z",
                    "retrieved_at": "2026-11-14T10:00:00Z",
                    "excerpt": "Acme announced...",
                    "category": "product_and_service_launches",
                    "target_entity": "Acme Corp",
                    "relevance_score": 0.8,
                    "credibility": "medium",
                    "in_window": True,
                    "undated": False,
                },
            ],
            "open_questions": [
                {
                    "id": "oq1",
                    "question": "How is Acme responding to the regulatory probe?",
                    "rationale": "Material risk for any near-term partnership.",
                    "grounding": "verified_development",
                    "related_finding_ids": ["f1"],
                    "category": "strategy",
                }
            ],
            "gaps": ["No recent funding data in window"],
            "contradictions": [],
            "stats": {"sources": 2, "findings": 2},
            "grounding_notes": ["Test fixture"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "completed",
        }
        row = ResearchSession(
            id="rs-test-1",
            user_id=owner,
            entity_name="Acme Corp",
            entity_type="company",
            meeting_at="2026-11-20T10:00:00Z",
            window_start="2026-10-21T00:00:00Z",
            window_end="2026-11-20T00:00:00Z",
            window_days=30,
            status="completed",
            result_json=json.dumps(payload),
        )
        db.add(row)
        db.commit()
    finally:
        db.close()

    # Manually set the session cookie that matches owner
    client.cookies.set("prebrief_session", owner)

    res = client.post(
        "/api/v1/chat",
        json={
            "question": "What are the biggest risks?",
            "research_session_id": "rs-test-1",
        },
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert "answer" in data
    assert "regulatory" in data["answer"].lower() or "investigation" in data["answer"].lower()
    assert data.get("grounded") is True
    assert "s1" in (data.get("citations") or [])


def test_chat_greeting():
    client = _client()
    client.get("/api/v1/health")
    res = client.post("/api/v1/chat", json={"question": "Hello"})
    assert res.status_code == 200
    assert "answer" in res.json()
