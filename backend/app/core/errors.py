"""One error shape for every failure: {"error": {"code", "message", "requestId"}}."""
from __future__ import annotations

import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.schemas.errors import ErrorBody, ErrorCode, ErrorDetail

log = logging.getLogger("prebrief")

_STATUS_TO_CODE: dict[int, ErrorCode] = {
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    422: "validation_error",
    429: "rate_limited",
    502: "upstream_unavailable",
    503: "upstream_unavailable",
    504: "upstream_unavailable",
}


class UpstreamError(Exception):
    """Raised when Tavily or Gemini fails; mapped to 502 upstream_unavailable."""

    def __init__(self, message: str = "A data provider is temporarily unavailable."):
        super().__init__(message)
        self.message = message


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "-")


def _response(request: Request, status: int, code: ErrorCode, message: str) -> JSONResponse:
    body = ErrorBody(error=ErrorDetail(code=code, message=message, request_id=_request_id(request)))
    return JSONResponse(
        status_code=status,
        content=body.model_dump(by_alias=True),
        headers={"X-Request-Id": _request_id(request)},
    )


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:16]
        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_id
        return response


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(p) for p in first.get("loc", []) if p != "body")
        msg = first.get("msg", "Invalid request")
        return _response(request, 422, "validation_error", f"{where}: {msg}" if where else msg)

    # Starlette's class is the base of FastAPI's, so this also catches router-level 404/405.
    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException):
        code = _STATUS_TO_CODE.get(exc.status_code, "internal_error")
        return _response(request, exc.status_code, code, str(exc.detail))

    @app.exception_handler(UpstreamError)
    async def _upstream(request: Request, exc: UpstreamError):
        log.warning("upstream failure rid=%s: %s", _request_id(request), exc.message)
        return _response(request, 502, "upstream_unavailable", exc.message)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        log.exception("unhandled error rid=%s", _request_id(request))
        # Never leak internals to the client.
        return _response(request, 500, "internal_error", "Something went wrong on our side.")
