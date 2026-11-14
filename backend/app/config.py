from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    # Comma-separated; include both localhost and 127.0.0.1 for Vite dev
    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # "live" = real Tavily research (default; the project is scored on real data).
    # "stub" = tiny clearly-labelled synthetic briefing, for wiring/UI work without credits.
    briefing_mode: Literal["live", "stub"] = "live"

    tavily_api_key: str | None = None
    tavily_base_url: str = "https://api.tavily.com"
    tavily_timeout_seconds: float = 20.0
    tavily_max_results: int = 8          # per query
    search_cache_path: str = "./prebrief_cache.db"
    search_cache_ttl_seconds: int = 6 * 3600

    # --- Database / session ---
    database_url: str = "sqlite:///./prebrief.db"

    # Anonymous session (replaces login)
    anonymous_session_ttl_days: int = 30
    session_cookie_name: str = "prebrief_session"
    session_cookie_secure: bool = False  # set True behind HTTPS in production
    session_cookie_samesite: str = "lax"

    # Legacy auth settings kept only so existing .env files do not break; unused.
    jwt_secret_key: str = "CHANGE-ME-dev-only-prebrief-jwt-secret-key-32chars-min"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 14
    refresh_cookie_name: str = "prebrief_refresh"
    refresh_cookie_secure: bool = False
    refresh_cookie_samesite: str = "lax"
    password_reset_expire_minutes: int = 60
    login_rate_limit: str = "10/minute"

    # --- Documents ---
    upload_dir: str = "./data/uploads"
    max_upload_bytes: int = 25 * 1024 * 1024  # 25 MB per file
    max_files_per_user: int = 100
    max_storage_bytes_per_user: int = 500 * 1024 * 1024  # 500 MB
    allowed_extensions: str = "pdf,docx,txt,csv,pptx"
    enable_ocr: bool = False  # optional; requires pytesseract + tesseract binary
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def allowed_ext_set(self) -> set[str]:
        return {e.strip().lower().lstrip(".") for e in self.allowed_extensions.split(",") if e.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
