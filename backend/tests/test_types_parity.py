"""Drift guard: src/types.ts and app/schemas/briefing.py must describe the same contract."""
import pathlib
import re
import typing

import pytest

from app.schemas import briefing as B

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_TS_CANDIDATES = [_ROOT / "frontend" / "src" / "types.ts", _ROOT / "src" / "types.ts"]
_TS_PATH = next((p for p in _TS_CANDIDATES if p.is_file()), _TS_CANDIDATES[0])
TS = _TS_PATH.read_text(encoding="utf-8") if _TS_PATH.is_file() else ""


def ts_union(name: str) -> set[str]:
    m = re.search(rf"export type {name}\s*=\s*((?:\s*\|?\s*'[^']+')+)", TS)
    assert m, f"union {name} not found in types.ts"
    return set(re.findall(r"'([^']+)'", m.group(1)))


def ts_interface(name: str) -> dict[str, bool]:
    """field name -> is_optional"""
    m = re.search(rf"export interface {name} \{{\n(.*?)\n\}}", TS, re.S)
    assert m, f"interface {name} not found in types.ts"
    fields = {}
    for line in m.group(1).splitlines():
        if re.match(r"^\s*(/\*|\*|//)", line):
            continue
        fm = re.match(r"^  (\w+)(\?)?:", line)
        if fm:
            fields[fm.group(1)] = bool(fm.group(2))
    return fields


@pytest.mark.parametrize("name", [
    "SubjectType", "Sentiment", "SignalKind", "QuestionCategory", "NewsCategory",
])
def test_enums_match(name):
    py = set(typing.get_args(getattr(B, name)))
    assert py == ts_union(name)


@pytest.mark.parametrize("name", [
    "NewsItem", "BriefFact", "KeyPerson", "Snapshot", "Signal", "TalkingPoint", "OpenQuestion",
    "SourceEntry", "SentimentPoint", "CoverageSlice", "BriefingStats", "BriefingResult",
    "BriefingRequest", "ChatTurn", "MeetingContext",
])
def test_interface_fields_and_optionality_match(name):
    model = getattr(B, name)
    py = {f.alias or n: not f.is_required() for n, f in model.model_fields.items()}
    ts = ts_interface(name)
    assert set(py) == set(ts), f"{name}: field names differ"
    # Responses must match optionality exactly: a field the UI treats as required must
    # never be optional on the Python side (the backend could then omit it).
    # Requests may be stricter-defaulted in Python (e.g. BriefingRequest.days = 30).
    for field, ts_optional in ts.items():
        if name == "BriefingRequest":
            if ts_optional:
                assert py[field], f"{name}.{field} is optional in types.ts but required in Python"
        else:
            assert py[field] == ts_optional, (
                f"{name}.{field}: optional in types.ts={ts_optional}, optional in Python={py[field]}"
            )
