"""Password hashing, JWT, and opaque token helpers."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import Settings, get_settings

# Argon2 is preferred; passlib falls back to bcrypt if argon2-cffi missing.
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


def validate_password_strength(password: str) -> str | None:
    """Return an error message if the password is weak, else None."""
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if len(password) > 128:
        return "Password must be at most 128 characters."
    if not any(c.isalpha() for c in password):
        return "Password must contain at least one letter."
    if not any(c.isdigit() for c in password):
        return "Password must contain at least one digit."
    return None


def create_access_token(
    subject: str,
    *,
    extra: dict[str, Any] | None = None,
    settings: Settings | None = None,
) -> tuple[str, int]:
    """Return (token, expires_in_seconds)."""
    settings = settings or get_settings()
    expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
    expire = datetime.now(timezone.utc) + expires_delta
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    if extra:
        payload.update(extra)
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str, settings: Settings | None = None) -> dict[str, Any] | None:
    settings = settings or get_settings()
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def generate_opaque_token() -> str:
    """Cryptographically secure opaque token (for refresh / reset)."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """SHA-256 hex digest — store this, never the raw token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expiry(settings: Settings | None = None) -> datetime:
    settings = settings or get_settings()
    return datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)


def password_reset_expiry(settings: Settings | None = None) -> datetime:
    settings = settings or get_settings()
    return datetime.now(timezone.utc) + timedelta(minutes=settings.password_reset_expire_minutes)
