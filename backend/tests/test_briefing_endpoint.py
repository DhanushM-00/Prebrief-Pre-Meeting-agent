import httpx
from fastapi.testclient import TestClient

from app.api.v1.briefings import get_tavily
from app.config import Settings, get_settings
from app.main import app
from app.schemas.briefing import BriefingResult
from app.services.tavily_client import TavilyClient

BODY = {"subject": "Helio Grid", "type": "company", "days": 30}


def with_settings(**kw):
    app.dependency_overrides[get_settings] = lambda: Settings(**kw)


def teardown_function():
    app.dependency_overrides.clear()


def test_stub_mode_returns_valid_clearly_synthetic_briefing():
    with_settings(briefing_mode="stub")
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.post("/api/v1/briefing", json=BODY)
        assert r.status_code == 200, r.text
        BriefingResult.model_validate(r.json())
        assert r.json()["synthetic"] is True


def test_live_mode_without_key_fails_clearly_not_silently_fake():
    with_settings(briefing_mode="live", tavily_api_key=None)
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.post("/api/v1/briefing", json=BODY)
        assert r.status_code == 502
        assert r.json()["error"]["code"] == "upstream_unavailable"
        assert "TAVILY_API_KEY" in r.json()["error"]["message"]


def test_live_mode_end_to_end_with_fake_provider():
    fake = {"results": [{"title": "Helio Grid raises $48M Series B", "url": "https://reuters.com/x",
                          "content": "Helio Grid raised funding.", "score": 0.9,
                          "published_date": "Fri, 30 Oct 2026 07:30:00 GMT"}]}

    async def fake_tavily():
        c = TavilyClient("k", transport=httpx.MockTransport(lambda r: httpx.Response(200, json=fake)), backoff=0)
        yield c
        await c.aclose()

    with_settings(briefing_mode="live", tavily_api_key="k")
    app.dependency_overrides[get_tavily] = fake_tavily
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.post("/api/v1/briefing", json=BODY)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["synthetic"] is False


def test_invalid_request_uses_error_envelope():
    with_settings(briefing_mode="stub")
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.post("/api/v1/briefing", json={"subject": "X", "days": 45})
        assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"
