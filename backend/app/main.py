from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import briefings, chat, compare, documents, health, one_pager, reports, research
from app.config import get_settings
from app.core.errors import RequestIdMiddleware, install_error_handlers
from app.core.rate_limit import install_rate_limiting
from app.db import init_db
import app.models  # noqa: F401  — register models on Base.metadata

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="PreBrief API",
        version="3.0.0",
        docs_url=f"{API_PREFIX}/docs",
        openapi_url=f"{API_PREFIX}/openapi.json",
        lifespan=lifespan,
    )

    install_rate_limiting(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-Id",
            "X-CSRF-Token",
            "X-Prebrief-Session",
        ],
        expose_headers=["X-Request-Id"],
    )
    app.add_middleware(RequestIdMiddleware)
    install_error_handlers(app)

    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(briefings.router, prefix=API_PREFIX)
    app.include_router(documents.router, prefix=API_PREFIX)
    app.include_router(research.router, prefix=API_PREFIX)
    app.include_router(one_pager.router, prefix=API_PREFIX)
    app.include_router(chat.router, prefix=API_PREFIX)
    app.include_router(compare.router, prefix=API_PREFIX)
    app.include_router(reports.router, prefix=API_PREFIX)
    return app


app = create_app()
