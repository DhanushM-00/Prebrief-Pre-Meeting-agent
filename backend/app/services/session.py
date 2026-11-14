"""Anonymous session management via HttpOnly cookie.

No login required. Each browser gets a stable session identifier that owns
uploaded documents and research sessions. Sessions expire after a configurable
TTL and can be cleaned up.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, Request, Response
from sqlalchemy import DateTime, String, select
from sqlalchemy.orm import Mapped, mapped_column, Session

from app.config import Settings, get_settings
from app.db import Base, get_db


SESSION_COOKIE = "prebrief_session"
SESSION_HEADER = "X-Prebrief-Session"  # optional override for non-browser clients


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_session_id() -> str:
    return str(uuid.uuid4())


class AnonymousSession(Base):
    """Lightweight ownership record for anonymous browser sessions."""

    __tablename__ = "anonymous_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_session_id)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def create_session_record(db: Session, settings: Settings) -> AnonymousSession:
    now = _utcnow()
    ttl_days = getattr(settings, "anonymous_session_ttl_days", 30)
    row = AnonymousSession(
        id=_new_session_id(),
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(days=ttl_days),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def touch_session(db: Session, session_id: str, settings: Settings) -> AnonymousSession | None:
    row = db.get(AnonymousSession, session_id)
    if row is None:
        return None
    now = _utcnow()
    if row.expires_at.replace(tzinfo=timezone.utc) if row.expires_at.tzinfo is None else row.expires_at < now:
        return None
    ttl_days = getattr(settings, "anonymous_session_ttl_days", 30)
    row.last_seen_at = now
    row.expires_at = now + timedelta(days=ttl_days)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def set_session_cookie(response: Response, session_id: str, settings: Settings) -> None:
    secure = bool(getattr(settings, "session_cookie_secure", False) or settings.app_env == "production")
    samesite = getattr(settings, "session_cookie_samesite", "lax")
    max_age = int(getattr(settings, "anonymous_session_ttl_days", 30) * 24 * 3600)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_id,
        httponly=True,
        secure=secure,
        samesite=samesite,
        max_age=max_age,
        path="/",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    secure = bool(getattr(settings, "session_cookie_secure", False) or settings.app_env == "production")
    samesite = getattr(settings, "session_cookie_samesite", "lax")
    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        secure=secure,
        samesite=samesite,
    )


def get_or_create_session(
    request: Request,
    response: Response,
    db: Session,
    settings: Settings,
) -> str:
    """Resolve session id from cookie (or header), create if missing, set cookie."""
    raw = request.cookies.get(SESSION_COOKIE) or request.headers.get(SESSION_HEADER)
    if raw:
        row = touch_session(db, raw, settings)
        if row is not None:
            set_session_cookie(response, row.id, settings)
            return row.id
    # New session
    row = create_session_record(db, settings)
    set_session_cookie(response, row.id, settings)
    return row.id


def require_session(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> str:
    """FastAPI dependency: always returns a valid anonymous session id."""
    return get_or_create_session(request, response, db, settings)


# Type alias for route signatures
from typing import Annotated as _Ann

AnonymousSessionId = _Ann[str, Depends(require_session)]
