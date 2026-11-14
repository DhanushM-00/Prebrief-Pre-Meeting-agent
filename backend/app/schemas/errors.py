from __future__ import annotations

from typing import Literal

from app.schemas.base import WireModel

ErrorCode = Literal[
    "validation_error",
    "unauthorized",
    "forbidden",
    "not_found",
    "rate_limited",
    "upstream_unavailable",  # Tavily / Gemini failed or timed out
    "internal_error",
]


class ErrorDetail(WireModel):
    code: ErrorCode
    message: str
    request_id: str | None = None


class ErrorBody(WireModel):
    error: ErrorDetail
