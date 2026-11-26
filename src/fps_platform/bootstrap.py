from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from fps_platform.api.body_limit import BodySizeLimitMiddleware
from fps_platform.api.errors import install_exception_handlers
from fps_platform.api.health import router as health_router
from fps_platform.api.no_store import AdminNoStoreMiddleware
from fps_platform.api.test_routes import router as test_router
from fps_platform.api.v1.admin.media_routes import router as media_admin_router
from fps_platform.api.v1.public.media_routes import router as media_public_router
from fps_platform.config import Settings
from fps_platform.modules.contact.api.admin_routes import router as contact_admin_router
from fps_platform.modules.contact.api.routes import router as contact_router
from fps_platform.modules.contact.application.ports import EmailDeliveryPort
from fps_platform.modules.contact.domain.enums import ContactEmailProviderMode
from fps_platform.modules.contact.infrastructure.email import (
    DisabledEmailDeliveryPort,
    MockEmailDeliveryPort,
)
from fps_platform.modules.contact.infrastructure.imap import ImapInboxProbePort
from fps_platform.modules.contact.infrastructure.rate_limit import InMemoryContactRateLimiter
from fps_platform.modules.contact.infrastructure.resend import ResendEmailDeliveryPort
from fps_platform.modules.contact.infrastructure.smtp import SmtpEmailDeliveryPort
from fps_platform.modules.identity.api.routes import router as admin_router
from fps_platform.modules.identity.infrastructure.oidc.factory import build_token_validator
from fps_platform.modules.media.application.commands.request_upload import (
    MediaIntentIdempotencyStore,
)
from fps_platform.modules.media.application.ports import MediaStoragePort
from fps_platform.modules.media.domain.enums import MediaStorageMode
from fps_platform.modules.media.infrastructure.fake_storage import InMemoryMediaStoragePort
from fps_platform.modules.media.infrastructure.public_url_resolver import (
    StorageBackedPublicUrlResolver,
)
from fps_platform.modules.media.infrastructure.s3_storage import S3MediaStoragePort
from fps_platform.observability.metrics import MetricsRegistry
from fps_platform.observability.middleware import CorrelationIdMiddleware
from fps_platform.shared.domain.clock import Clock, SystemClock
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
        email_port = app.state.email_delivery_port
        close = getattr(email_port, "close", None)
        if callable(close):
            close()
        media_port = app.state.media_storage_port
        close_media = getattr(media_port, "close", None)
        if callable(close_media):
            close_media()
        if engine is not None:
            engine.dispose()
        app.state.session_factory = None


def build_email_port(settings: Settings) -> EmailDeliveryPort:
    if settings.contact_email_provider_mode is ContactEmailProviderMode.DISABLED:
        return DisabledEmailDeliveryPort()
    if settings.contact_email_provider_mode is ContactEmailProviderMode.RESEND:
        if (
            settings.resend_api_key is None
            or settings.resend_base_url is None
            or settings.sender_email is None
            or settings.notify_email is None
        ):
            raise RuntimeError("resend configuration is incomplete")
        return ResendEmailDeliveryPort(
            api_key=settings.resend_api_key.get_secret_value(),
            base_url=settings.resend_base_url,
            sender_email=settings.sender_email,
            recipient_email=settings.notify_email,
            timeout_seconds=settings.email_request_timeout_seconds,
        )
    if settings.contact_email_provider_mode is ContactEmailProviderMode.SMTP:
        if (
            settings.smtp_host is None
            or settings.smtp_user is None
            or settings.smtp_password is None
            or settings.sender_email is None
            or settings.notify_email is None
        ):
            raise RuntimeError("smtp configuration is incomplete")
        return SmtpEmailDeliveryPort(
            host=settings.smtp_host,
            port=settings.smtp_port,
            user=settings.smtp_user,
            password=settings.smtp_password.get_secret_value(),
            sender_email=settings.sender_email,
            recipient_email=settings.notify_email,
            use_ssl=settings.smtp_use_ssl,
            timeout_seconds=settings.email_request_timeout_seconds,
        )
    return MockEmailDeliveryPort(settings.contact_email_provider)


def build_imap_probe(settings: Settings) -> ImapInboxProbePort | None:
    if settings.imap_host is None or settings.imap_user is None or settings.imap_password is None:
        return None
    return ImapInboxProbePort(
        host=settings.imap_host,
        port=settings.imap_port,
        user=settings.imap_user,
        password=settings.imap_password.get_secret_value(),
        use_ssl=settings.imap_use_ssl,
        timeout_seconds=settings.email_request_timeout_seconds,
    )


def build_media_storage_port(settings: Settings, clock: Clock) -> MediaStoragePort:
    if settings.media_storage_mode is MediaStorageMode.FAKE:
        return InMemoryMediaStoragePort(
            clock,
            public_base_url=settings.media_public_base_url or "https://media.example.test",
            max_bytes=settings.media_max_bytes,
        )
    if (
        settings.media_bucket is None
        or settings.media_region is None
        or settings.media_access_key_id is None
        or settings.media_secret_access_key is None
        or settings.media_public_base_url is None
    ):
        raise RuntimeError("media storage configuration is incomplete")
    return S3MediaStoragePort(
        bucket=settings.media_bucket,
        region=settings.media_region,
        access_key_id=settings.media_access_key_id.get_secret_value(),
        secret_access_key=settings.media_secret_access_key.get_secret_value(),
        public_base_url=settings.media_public_base_url,
        clock=clock,
        endpoint_url=settings.media_endpoint_url,
        force_path_style=settings.media_force_path_style,
        signed_url_ttl_seconds=settings.media_signed_url_ttl_seconds,
        request_timeout_seconds=settings.media_request_timeout_seconds,
    )


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
    app.state.clock = SystemClock()
    app.state.contact_rate_limiter = InMemoryContactRateLimiter(app.state.clock)
    app.state.email_delivery_port = build_email_port(resolved)
    app.state.imap_inbox_probe = build_imap_probe(resolved)
    app.state.media_storage_port = build_media_storage_port(resolved, app.state.clock)
    app.state.public_url_resolver = StorageBackedPublicUrlResolver(
        storage=app.state.media_storage_port
    )
    app.state.metrics = MetricsRegistry()
    app.state.media_intent_idempotency = MediaIntentIdempotencyStore(
        app.state.clock, ttl_seconds=resolved.media_signed_url_ttl_seconds
    )
    app.state.token_validator = build_token_validator(resolved)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "Idempotency-Key",
            "X-Correlation-ID",
            "X-Request-ID",
        ],
        max_age=600,
    )
    app.add_middleware(AdminNoStoreMiddleware)
    app.add_middleware(
        BodySizeLimitMiddleware,
        path="/api/v1/contact",
        max_bytes=resolved.contact_max_body_bytes,
    )
    app.add_middleware(CorrelationIdMiddleware, settings=resolved)
    install_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(contact_router)
    app.include_router(contact_admin_router)
    app.include_router(admin_router)
    app.include_router(media_admin_router)
    app.include_router(media_public_router)
    if include_test_routes:
        app.include_router(test_router)
    return app
