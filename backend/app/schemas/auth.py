"""Account contract (user accounts requirement). Endpoints land in Phase 6;
the shapes are fixed now so the frontend and every other endpoint can rely on them."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import EmailStr, Field, field_validator

from app.schemas.base import WireModel


class RegisterRequest(WireModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str | None = Field(default=None, max_length=100)
    accept_terms: bool = True

    @field_validator("accept_terms")
    @classmethod
    def terms_must_be_accepted(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must accept the terms of service.")
        return v


class LoginRequest(WireModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = False


class TokenResponse(WireModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    user: "UserOut | None" = None


class UserOut(WireModel):
    id: str
    email: EmailStr
    name: str | None = None
    created_at: str
    is_verified: bool = False
    status: str = "active"


class ForgotPasswordRequest(WireModel):
    email: EmailStr


class ResetPasswordRequest(WireModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=8, max_length=128)


class ChangePasswordRequest(WireModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UpdateProfileRequest(WireModel):
    name: str | None = Field(default=None, max_length=100)


class PreferencesOut(WireModel):
    data: dict[str, Any] = Field(default_factory=dict)


class UpdatePreferencesRequest(WireModel):
    data: dict[str, Any]


class MessageResponse(WireModel):
    message: str


class LogoutResponse(WireModel):
    message: str = "Logged out"
