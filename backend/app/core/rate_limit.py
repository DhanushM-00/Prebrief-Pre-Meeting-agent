"""Optional SlowAPI rate limiting — no-op fallback when slowapi is not installed."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    from slowapi.util import get_remote_address

    HAS_SLOWAPI = True
except ImportError:  # pragma: no cover
    HAS_SLOWAPI = False
    RateLimitExceeded = type("RateLimitExceeded", (Exception,), {})  # type: ignore
    SlowAPIMiddleware = None  # type: ignore
    _rate_limit_exceeded_handler = None  # type: ignore

    def get_remote_address(request: Any) -> str:  # type: ignore
        return "127.0.0.1"

    class Limiter:  # type: ignore
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def limit(self, *args: Any, **kwargs: Any) -> Callable:
            def decorator(func: Callable) -> Callable:
                return func

            return decorator


limiter = Limiter(key_func=get_remote_address)


def install_rate_limiting(app: Any) -> None:
    """Attach SlowAPI middleware when available; otherwise do nothing."""
    if not HAS_SLOWAPI:
        return
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
