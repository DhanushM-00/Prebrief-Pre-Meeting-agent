"""Business logic for registration, login, refresh, and password flows."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    password_reset_expiry,
    refresh_token_expiry,
    validate_password_strength,
    verify_password,
)
from app.models.user import PasswordResetToken, RefreshToken, User, UserPreferences


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _user_out(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "created_at": user.created_at.isoformat() if user.created_at else "",
        "is_verified": user.is_verified,
        "status": user.status,
    }


def register_user(
    db: Session,
    *,
    email: str,
    password: str,
    name: str | None = None,
) -> User:
    email_norm = email.strip().lower()
    strength = validate_password_strength(password)
    if strength:
        raise AuthError(strength, 422)

    existing = db.scalar(select(User).where(User.email == email_norm))
    if existing:
        raise AuthError("An account with this email already exists.", 409)

    user = User(
        email=email_norm,
        hashed_password=hash_password(password),
        name=(name or "").strip() or None,
        is_active=True,
        is_verified=False,
        status="active",
    )
    db.add(user)
    db.flush()

    prefs = UserPreferences(user_id=user.id, data="{}")
    db.add(prefs)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    email_norm = email.strip().lower()
    user = db.scalar(select(User).where(User.email == email_norm))
    if not user or not verify_password(password, user.hashed_password):
        raise AuthError("Invalid email or password.", 401)
    if not user.is_active or user.status in ("suspended", "deleted"):
        raise AuthError("This account is not active.", 403)
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return user


def issue_tokens(
    db: Session,
    user: User,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
    settings: Settings | None = None,
) -> tuple[str, int, str]:
    """Return (access_token, expires_in, refresh_token_plain)."""
    settings = settings or get_settings()
    access, expires_in = create_access_token(user.id, extra={"email": user.email}, settings=settings)

    plain_refresh = generate_opaque_token()
    family_id = generate_opaque_token()[:36]
    rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(plain_refresh),
        family_id=family_id,
        expires_at=refresh_token_expiry(settings),
        user_agent=(user_agent or "")[:512] or None,
        ip_address=(ip_address or "")[:64] or None,
    )
    db.add(rt)
    db.commit()
    return access, expires_in, plain_refresh


def rotate_refresh_token(
    db: Session,
    plain_refresh: str,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
    settings: Settings | None = None,
) -> tuple[str, int, str, User]:
    """Validate, revoke old, issue new. Implements refresh-token rotation."""
    settings = settings or get_settings()
    th = hash_token(plain_refresh)
    now = datetime.now(timezone.utc)

    rt = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == th))
    if not rt or rt.revoked_at is not None:
        # Possible reuse — revoke entire family if we can identify it
        if rt and rt.family_id:
            _revoke_family(db, rt.family_id)
        raise AuthError("Invalid or expired refresh token.", 401)
    if rt.expires_at.replace(tzinfo=timezone.utc) < now:
        rt.revoked_at = now
        db.commit()
        raise AuthError("Refresh token has expired.", 401)

    user = db.get(User, rt.user_id)
    if not user or not user.is_active or user.status in ("suspended", "deleted"):
        raise AuthError("Account is not active.", 403)

    # Rotate: revoke old, issue new in same family
    rt.revoked_at = now
    new_plain = generate_opaque_token()
    new_rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(new_plain),
        family_id=rt.family_id,
        expires_at=refresh_token_expiry(settings),
        user_agent=(user_agent or "")[:512] or None,
        ip_address=(ip_address or "")[:64] or None,
    )
    db.add(new_rt)
    db.commit()

    access, expires_in = create_access_token(user.id, extra={"email": user.email}, settings=settings)
    return access, expires_in, new_plain, user


def revoke_refresh_token(db: Session, plain_refresh: str) -> None:
    th = hash_token(plain_refresh)
    rt = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == th))
    if rt and rt.revoked_at is None:
        rt.revoked_at = datetime.now(timezone.utc)
        db.commit()


def revoke_all_user_sessions(db: Session, user_id: str) -> int:
    now = datetime.now(timezone.utc)
    tokens = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
    ).all()
    for t in tokens:
        t.revoked_at = now
    db.commit()
    return len(tokens)


def _revoke_family(db: Session, family_id: str) -> None:
    now = datetime.now(timezone.utc)
    tokens = db.scalars(
        select(RefreshToken).where(
            RefreshToken.family_id == family_id,
            RefreshToken.revoked_at.is_(None),
        )
    ).all()
    for t in tokens:
        t.revoked_at = now
    db.commit()


def create_password_reset(db: Session, email: str, settings: Settings | None = None) -> str | None:
    """Return plain token if user exists (caller may email it). Always silent on missing user."""
    settings = settings or get_settings()
    email_norm = email.strip().lower()
    user = db.scalar(select(User).where(User.email == email_norm))
    if not user or not user.is_active:
        return None
    plain = generate_opaque_token()
    prt = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(plain),
        expires_at=password_reset_expiry(settings),
    )
    db.add(prt)
    db.commit()
    return plain


def reset_password(db: Session, plain_token: str, new_password: str) -> User:
    strength = validate_password_strength(new_password)
    if strength:
        raise AuthError(strength, 422)

    th = hash_token(plain_token)
    now = datetime.now(timezone.utc)
    prt = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == th))
    if not prt or prt.used_at is not None:
        raise AuthError("Invalid or already used reset token.", 400)
    exp = prt.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < now:
        raise AuthError("Reset token has expired.", 400)

    user = db.get(User, prt.user_id)
    if not user:
        raise AuthError("Invalid reset token.", 400)

    user.hashed_password = hash_password(new_password)
    prt.used_at = now
    # Invalidate all sessions after password change
    revoke_all_user_sessions(db, user.id)
    db.commit()
    db.refresh(user)
    return user


def change_password(
    db: Session, user: User, current_password: str, new_password: str
) -> None:
    if not verify_password(current_password, user.hashed_password):
        raise AuthError("Current password is incorrect.", 400)
    strength = validate_password_strength(new_password)
    if strength:
        raise AuthError(strength, 422)
    user.hashed_password = hash_password(new_password)
    revoke_all_user_sessions(db, user.id)
    db.commit()


def get_preferences(db: Session, user: User) -> dict:
    prefs = user.preferences
    if not prefs:
        prefs = UserPreferences(user_id=user.id, data="{}")
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    try:
        return json.loads(prefs.data or "{}")
    except json.JSONDecodeError:
        return {}


def update_preferences(db: Session, user: User, data: dict) -> dict:
    prefs = user.preferences
    if not prefs:
        prefs = UserPreferences(user_id=user.id, data="{}")
        db.add(prefs)
        db.flush()
    prefs.data = json.dumps(data)
    db.commit()
    return data
