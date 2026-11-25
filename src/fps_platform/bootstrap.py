from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from fps_platform.api.errors import install_exception_handlers
from fps_platform.api.health import router as health_router
from fps_platform.api.test_routes import router as test_router
from fps_platform.config import Settings
from fps_platform.observability.middleware import CorrelationIdMiddleware


def build_db_engine(database_url: str) -> Engine:
    connect_args = (
        {"connect_timeout": 2}
        if database_url.startswith(("postgresql://", "postgresql+psycopg://"))
        else {}
    )
    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_timeout=5,
        connect_args=connect_args,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    engine: Engine | None = None
    if settings.database_url is not None:
        engine = build_db_engine(settings.database_url.get_secret_value())
    app.state.db_engine = engine
    try:
        yield
    finally:
        if engine is not None:
            engine.dispose()


def create_app(settings: Settings | None = None, *, include_test_routes: bool = False) -> FastAPI:
    resolved = settings or Settings()
    app = FastAPI(
        title=resolved.api_name,
        version=resolved.api_version,
        description="Backend API de la FPS Content Platform",
        docs_url="/docs" if resolved.docs_enabled else None,
        openapi_url="/openapi.json" if resolved.docs_enabled else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.settings = resolved
    app.state.db_engine = None
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Correlation-ID", "X-Request-ID"],
        max_age=600,
    )
    app.add_middleware(CorrelationIdMiddleware, settings=resolved)
    install_exception_handlers(app)
    app.include_router(health_router)
    if include_test_routes:
        app.include_router(test_router)
    return app
