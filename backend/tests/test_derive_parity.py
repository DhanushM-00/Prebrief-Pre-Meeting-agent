"""The Python analytics must reproduce what the frontend generator computed."""
import json
import pathlib
from datetime import datetime

import pytest

from app.schemas import BriefingResult
from app.services import derive

FIXTURES = sorted((pathlib.Path(__file__).parent / "fixtures").glob("briefing_*.json"))


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_derive_matches_frontend_output(path):
    raw = json.loads(path.read_text())
    b = BriefingResult.model_validate(raw)
    end = datetime.fromisoformat(raw["windowEnd"].replace("Z", "+00:00"))

    trend = derive.build_trend(b.news, b.window_days, end)
    assert [p.model_dump(by_alias=True) for p in trend] == raw["sentimentTrend"]
    assert [c.model_dump(by_alias=True) for c in derive.build_coverage(b.news)] == raw["coverage"]
    assert derive.build_stats(b.news).model_dump(by_alias=True) == raw["stats"]
