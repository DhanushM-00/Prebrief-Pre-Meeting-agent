"""Authentication endpoints: register, login, refresh, logout, password flows, profile."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.core.rate_limit import limiter
from app.dependencies import CurrentUser, DbSession
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutResponse,
    MessageResponse,
    PreferencesOut,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UpdatePreferencesRequest,
    UpdateProfileRequest,
    UserOut,
)
from app.services.auth_service import (
    AuthError,
    authenticate_user,
    change_password,
    create_password_reset,
    get_preferences,
    issue_tokens,
    register_user,
    reset_password,
    revoke_all_user_sessions,
    revoke_refresh_token,
    rotate_refresh_token,
    update_preferences,
    _user_out,
)

router = APIRouter(tags=["auth"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ua = request.headers.get("user-agent")
    ip = request.client.host if request.client else None
    return ua, ip


def _set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    max_age = settings.refresh_token_expire_days * 24 * 3600
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        max_age=max_age,
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path="/api/v1/auth",
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
    )


@router.post("/auth/register", response_model=TokenResponse, status_code=201)
def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    db: DbSession,
    settings: Settings = Depends(get_settings),
):
    try:
        user = register_user(db, email=body.email, password=body.password, name=body.name)
    except AuthError as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": {"code": "conflict" if e.status_code == 409 else "validation_error", "message": e.message}},
        )
    ua, ip = _client_meta(request)
    access, expires_in, refresh = issue_tokens(db, user, user_agent=ua, ip_address=ip, settings=settings)
    _set_refresh_cookie(response, refresh, settings)
    return TokenResponse(
        access_token=access,
        expires_in=expires_in,
        user=UserOut(**_user_out(user)),
    )


@router.post("/auth/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: DbSession,
    settings: Settings = Depends(get_settings),
):
    try:
        user = authenticate_user(db, body.email, body.password)
    except AuthError as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": {"code": "unauthorized" if e.status_code == 401 else "forbidden", "message": e.message}},
        )
    ua, ip = _client_meta(request)
    access, expires_in, refresh = issue_tokens(db, user, user_agent=ua, ip_address=ip, settings=settings)
    _set_refresh_cookie(response, refresh, settings)
    return TokenResponse(
        access_token=access,
        expires_in=expires_in,
        user=UserOut(**_user_out(user)),
    )


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh(
    request: Request,
    response: Response,
    db: DbSession,
    settings: Settings = Depends(get_settings),
):
    plain = request.cookies.get(settings.refresh_cookie_name)
    if not plain:
        return JSONResponse(
            status_code=401,
            content={"error": {"code": "unauthorized", "message": "No refresh token."}},
        )
    try:
        ua, ip = _client_meta(request)
        access, expires_in, new_refresh, user = rotate_refresh_token(
            db, plain, user_agent=ua, ip_address=ip, settings=settings
        )
    except AuthError as e:
        _clear_refresh_cookie(response, settings)
        return JSONResponse(
            status_code=e.status_code,
            content={"error": {"code": "unauthorized", "message": e.message}},
        )
    _set_refresh_cookie(response, new_refresh, settings)
    return TokenResponse(
        access_token=access,
        expires_in=expires_in,
        user=UserOut(**_user_out(user)),
    )


@router.post("/auth/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    response: Response,
    db: DbSession,
    settings: Settings = Depends(get_settings),
):
    plain = request.cookies.get(settings.refresh_cookie_name)
    if plain:
        revoke_refresh_token(db, plain)
    _clear_refresh_cookie(response, settings)
    return LogoutResponse()


@router.get("/auth/me", response_model=UserOut)
def me(user: CurrentUser):
    return UserOut(**_user_out(user))


@router.post("/auth/forgot-password", response_model=MessageResponse)
def forgot_password(
    body: ForgotPasswordRequest,
    db: DbSession,
    settings: Settings = Depends(get_settings),
):
    # Always return success to avoid email enumeration
    token = create_password_reset(db, body.email, settings)
    # In production, email the token. For prototype, log it when in development.
    if token and settings.app_env == "development":
        import logging
        logging.getLogger("prebrief").info("Password reset token for %s: %s", body.email, token)
    return MessageResponse(message="If an account exists for that email, a reset link has been sent.")


@router.post("/auth/reset-password", response_model=MessageResponse)
def do_reset_password(body: ResetPasswordRequest, db: DbSession):
    try:
        reset_password(db, body.token, body.password)
    except AuthError as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": {"code": "validation_error", "message": e.message}},
        )
    return MessageResponse(message="Password has been reset. You can now log in.")


@router.post("/auth/change-password", response_model=MessageResponse)
def do_change_password(body: ChangePasswordRequest, user: CurrentUser, db: DbSession):
    try:
        change_password(db, user, body.current_password, body.new_password)
    except AuthError as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": {"code": "validation_error", "message": e.message}},
        )
    return MessageResponse(message="Password updated. Other sessions have been signed out.")


@router.patch("/auth/profile", response_model=UserOut)
def update_profile(body: UpdateProfileRequest, user: CurrentUser, db: DbSession):
    if body.name is not None:
        user.name = body.name.strip() or None
    db.commit()
    db.refresh(user)
    return UserOut(**_user_out(user))


@router.get("/auth/preferences", response_model=PreferencesOut)
def read_preferences(user: CurrentUser, db: DbSession):
    return PreferencesOut(data=get_preferences(db, user))


@router.put("/auth/preferences", response_model=PreferencesOut)
def write_preferences(body: UpdatePreferencesRequest, user: CurrentUser, db: DbSession):
    data = update_preferences(db, user, body.data)
    return PreferencesOut(data=data)


@router.post("/auth/logout-all", response_model=MessageResponse)
def logout_all(user: CurrentUser, db: DbSession, response: Response, settings: Settings = Depends(get_settings)):
    n = revoke_all_user_sessions(db, user.id)
    _clear_refresh_cookie(response, settings)
    return MessageResponse(message=f"Signed out of {n} session(s).")


@router.delete("/auth/account", response_model=MessageResponse)
def delete_account(user: CurrentUser, db: DbSession, response: Response, settings: Settings = Depends(get_settings)):
    """Soft-delete: mark status and revoke sessions. Hard delete can be a later job."""
    user.status = "pending_deletion"
    user.is_active = False
    revoke_all_user_sessions(db, user.id)
    db.commit()
    _clear_refresh_cookie(response, settings)
    return MessageResponse(message="Account scheduled for deletion.")
