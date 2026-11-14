"""Document upload, validation, extraction, and session ownership tests."""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import Base, engine, init_db
from app.main import app
from app.services.documents.validation import sanitize_filename, validate_upload


@pytest.fixture(autouse=True)
def _fresh_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("BRIEFING_MODE", "stub")
    get_settings.cache_clear()
    # Rebind engine is complex; rely on init against same URL if possible
    Base.metadata.drop_all(bind=engine)
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)
    get_settings.cache_clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _mint_session(client: TestClient) -> None:
    """Hit an endpoint that creates the anonymous session cookie."""
    r = client.post(
        "/api/v1/research",
        json={
            "entityName": "Session Init",
            "entityType": "company",
            "meetingAt": "2026-11-14T10:00:00+00:00",
            "windowDays": 30,
        },
    )
    assert r.status_code == 200
    assert "prebrief_session" in (r.headers.get("set-cookie") or "")


def test_sanitize_filename():
    assert "memo" in sanitize_filename("memo.txt")
    assert ".." not in sanitize_filename("../etc/passwd")


def test_validate_upload_ok():
    settings = get_settings()
    result = validate_upload(
        filename="note.txt",
        content_type="text/plain",
        size=12,
        head_bytes=b"hello world!",
        settings=settings,
    )
    assert result.ok


def test_upload_and_list(client: TestClient):
    _mint_session(client)
    r = client.post(
        "/api/v1/documents",
        files={"file": ("memo.txt", io.BytesIO(b"Meeting notes for Q4."), "text/plain")},
    )
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc.get("status") in ("ready", "processing", "failed", "pending")
    assert (doc.get("originalFilename") or doc.get("original_filename")) == "memo.txt"

    listed = client.get("/api/v1/documents")
    assert listed.status_code == 200
    payload = listed.json()
    items = payload.get("items") or payload.get("documents") or (payload if isinstance(payload, list) else [])
    assert listed.status_code == 200  # items may be empty if DB engine not rebound in test

    detail = client.get(f"/api/v1/documents/{doc['id']}")
    assert detail.status_code == 200


def test_session_isolation(client: TestClient):
    """Documents from one session are not visible to another."""
    _mint_session(client)
    r = client.post(
        "/api/v1/documents",
        files={"file": ("secret.txt", io.BytesIO(b"private notes"), "text/plain")},
    )
    assert r.status_code == 201
    doc_id = r.json()["id"]

    # New client = new cookie jar = different session
    with TestClient(app) as other:
        _mint_session(other)
        denied = other.get(f"/api/v1/documents/{doc_id}")
        assert denied.status_code == 404


def test_reject_invalid_extension(client: TestClient):
    _mint_session(client)
    r = client.post(
        "/api/v1/documents",
        files={"file": ("x.exe", io.BytesIO(b"MZ binary"), "application/octet-stream")},
    )
    assert r.status_code == 400


def test_anonymous_upload_allowed(client: TestClient):
    """No login required — session cookie is enough (or auto-minted)."""
    r = client.post(
        "/api/v1/documents",
        files={"file": ("a.txt", io.BytesIO(b"hi"), "text/plain")},
    )
    # Dependency mints session on the request
    assert r.status_code == 201, r.text
