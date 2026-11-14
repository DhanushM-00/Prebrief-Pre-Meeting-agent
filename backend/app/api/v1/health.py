"""Health and readiness probes."""
from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.config import get_settings
from app.db import SessionLocal

router = APIRouter(tags=["meta"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "api": "v1"}


@router.get("/health/ready")
def ready() -> dict:
    """Readiness: API + database + research provider configuration."""
    settings = get_settings()
    checks: dict[str, str] = {"api": "ok"}
    overall = "ok"

    # Database
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            checks["database"] = "ok"
        finally:
            db.close()
    except Exception as e:
        checks["database"] = f"error: {e}"
        overall = "degraded"

    # Research provider
    if settings.briefing_mode == "stub":
        checks["research"] = "stub"
    elif settings.tavily_api_key:
        checks["research"] = "configured"
    else:
        checks["research"] = "unavailable"
        overall = "degraded"

    return {"status": overall, "checks": checks}
