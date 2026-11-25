from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from fps_platform.api.errors import install_exception_handlers
from fps_platform.api.health import router as health_router
from fps_platform.api.no_store import AdminNoStoreMiddleware
from fps_platform.api.test_routes import router as test_router
from fps_platform.config import Settings
from fps_platform.modules.identity.api.routes import router as admin_router
from fps_platform.modules.identity.infrastructure.oidc.factory import build_token_validator
from fps_platform.observability.middleware import CorrelationIdMiddleware
from fps_platform.shared.infrastructure.persistence.engine import (
    DatabaseRuntimeSettings,
    create_db_engine,
)


def build_db_engine(database_url: str, settings: Settings | None = None) -> Engine:
    runtime = (
        DatabaseRuntimeSettings(
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            pool_recycle=settings.db_pool_recycle,
            connect_timeout=settings.db_connect_timeout,
        )
        if settings is not None
        else None
    )
    return create_db_engine(database_url, runtime)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    engine: Engine | None = None
    if settings.database_url is not None:
        engine = build_db_engine(settings.database_url.get_secret_value(), settings)
    app.state.db_engine = engine
    app.state.session_factory = (
        sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)
        if engine is not None
        else None
    )
    try:
        yield
    finally:
        if engine is not None:
            engine.dispose()
        app.state.session_factory = None


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
    app.state.session_factory = None
    app.state.token_validator = build_token_validator(resolved)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Correlation-ID",
            "X-Request-ID",
        ],
        max_age=600,
    )
    app.add_middleware(AdminNoStoreMiddleware)
    app.add_middleware(CorrelationIdMiddleware, settings=resolved)
    install_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(admin_router)
    if include_test_routes:
        app.include_router(test_router)
    return app
