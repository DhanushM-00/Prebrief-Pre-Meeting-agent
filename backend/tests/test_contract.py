"""Contract tests: the Python models must accept exactly what the frontend's own
generator produces, and reproduce it byte-for-byte as JSON."""
import json
import pathlib

import pytest
from pydantic import ValidationError

from app.schemas.briefing import BriefingRequest, BriefingResult

FIXTURES = sorted((pathlib.Path(__file__).parent / "fixtures").glob("briefing_*.json"))


def test_fixtures_exist():
    assert len(FIXTURES) >= 3


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_briefing_round_trips_exactly(path):
    raw = json.loads(path.read_text())
    model = BriefingResult.model_validate(raw)
    # Same keys, same values; optional fields stay absent, null scores stay null.
    assert model.model_dump(mode="json", by_alias=True) == raw


def test_null_sentiment_score_is_preserved_not_dropped():
    raw = json.loads(FIXTURES[0].read_text())
    assert any(p["score"] is None for p in raw["sentimentTrend"])  # fixture really has gaps
    out = BriefingResult.model_validate(raw).model_dump(mode="json", by_alias=True)
    assert [p["score"] for p in out["sentimentTrend"]] == [p["score"] for p in raw["sentimentTrend"]]


def test_unknown_fields_are_rejected():
    raw = json.loads(FIXTURES[0].read_text())
    raw["news"][0]["bogus"] = 1
    with pytest.raises(ValidationError):
        BriefingResult.model_validate(raw)


def test_invalid_enum_rejected():
    raw = json.loads(FIXTURES[0].read_text())
    raw["news"][0]["category"] = "gossip"
    with pytest.raises(ValidationError):
        BriefingResult.model_validate(raw)


# ----------------------------------------------------------------- requests --
def test_request_accepts_what_the_frontend_sends_today():
    r = BriefingRequest.model_validate({"subject": " Helio Grid ", "type": "auto", "days": 30})
    assert r.subject == "Helio Grid" and r.focus is None


@pytest.mark.parametrize("days", [0, 5, 45, 365])
def test_unsupported_windows_rejected(days):
    with pytest.raises(ValidationError):
        BriefingRequest.model_validate({"subject": "X", "type": "auto", "days": days})


def test_blank_subject_rejected():
    with pytest.raises(ValidationError):
        BriefingRequest.model_validate({"subject": "   ", "type": "auto", "days": 30})


def test_meeting_context_is_optional_and_validated():
    r = BriefingRequest.model_validate({
        "subject": "Acme", "type": "company", "days": 14,
        "meeting": {"title": "Intro", "date": "2026-11-10", "attendees": ["A", "B"], "note": ""},
    })
    assert r.meeting and r.meeting.attendees == ["A", "B"]


# --------------------------------------------------------------------- chat --
def _turn(role, content):
    return ChatTurn(id="t", role=role, content=content, created_at="2026-11-02T00:00:00.000Z")


@pytest.mark.skip(reason="chat endpoint removed")
def test_chat_drops_duplicated_trailing_question():
    req = ChatRequest(briefing_id="b1", question="What is risky?",
                      history=[_turn("user", "Hi"), _turn("agent", "Hello"), _turn("user", "What is risky?")])
    assert [t.content for t in req.prior_turns()] == ["Hi", "Hello"]


@pytest.mark.skip(reason="chat endpoint removed")
def test_chat_keeps_history_when_no_duplicate():
    req = ChatRequest(briefing_id="b1", question="Next?", history=[_turn("user", "Hi")])
    assert len(req.prior_turns()) == 1


@pytest.mark.skip(reason="chat endpoint removed")
def test_chat_accepts_frontend_payload_shape():
    req = ChatRequest.model_validate({
        "briefingId": "b-x-1", "question": "Q",
        "history": [{"id": "u-1", "role": "user", "content": "Q", "createdAt": "2026-11-02T00:00:00Z"}],
    })
    assert req.briefing_id == "b-x-1"


@pytest.mark.skip(reason="chat endpoint removed")
def test_chat_response_defaults_citations():
    assert ChatResponse(answer="x").model_dump(by_alias=True) == {"answer": "x", "citations": []}
