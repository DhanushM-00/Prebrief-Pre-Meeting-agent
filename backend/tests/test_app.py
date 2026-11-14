from fastapi.testclient import TestClient

from app.main import app
from app.core.errors import UpstreamError

client = TestClient(app, raise_server_exceptions=False)


def test_health_under_versioned_prefix():
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json() == {"status": "ok", "api": "v1"}
    assert r.headers["X-Request-Id"]


def test_unknown_route_uses_error_envelope():
    r = client.get("/api/v1/nope")
    body = r.json()
    assert r.status_code == 404
    assert body["error"]["code"] == "not_found"
    assert body["error"]["requestId"] == r.headers["X-Request-Id"]


def test_request_id_is_echoed():
    r = client.get("/api/v1/health", headers={"X-Request-Id": "abc123"})
    assert r.headers["X-Request-Id"] == "abc123"


def test_cors_allows_dev_frontend():
    r = client.options("/api/v1/health", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_blocks_other_origins():
    r = client.options("/api/v1/health", headers={
        "Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in r.headers


def test_validation_errors_use_envelope(monkeypatch):
    from fastapi import APIRouter
    from app.schemas import BriefingRequest

    router = APIRouter()

    @router.post("/_t/validate")
    def _v(req: BriefingRequest):  # noqa: ANN202
        return {"ok": True}

    @router.get("/_t/upstream")
    def _u():
        raise UpstreamError("Tavily timed out")

    @router.get("/_t/boom")
    def _b():
        raise RuntimeError("secret internal detail")

    app.include_router(router, prefix="/api/v1")
    r = client.post("/api/v1/_t/validate", json={"subject": "X", "days": 45})
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"

    r = client.get("/api/v1/_t/upstream")
    assert r.status_code == 502 and r.json()["error"]["code"] == "upstream_unavailable"

    r = client.get("/api/v1/_t/boom")
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "internal_error"
    assert "secret" not in r.text
