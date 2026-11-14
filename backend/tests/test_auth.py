"""Auth system removed — PreBrief uses anonymous sessions only."""
import pytest

pytestmark = pytest.mark.skip(reason="Authentication system removed in Stage 1")


def test_placeholder():
    assert True
