"""Shared FastAPI dependencies: DB session and anonymous session ownership."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db import get_db
from app.services.session import get_or_create_session, require_session


# Re-export for route signatures
AnonymousSessionId = Annotated[str, Depends(require_session)]
DbSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def get_session_id(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> str:
    """Always resolve (and mint if needed) an anonymous session id."""
    return get_or_create_session(request, response, db, settings)
