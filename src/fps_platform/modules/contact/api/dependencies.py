from __future__ import annotations

from collections.abc import Iterator
from typing import cast

from fastapi import Depends, Request

from fps_platform.config import Settings
from fps_platform.modules.contact.application.ports import (
    ContactRateLimiter,
    ContactUnitOfWork,
    EmailDeliveryPort,
)
from fps_platform.observability.request_context import get_correlation_id, get_request_id
from fps_platform.shared.auth.dependencies import get_session_factory, get_uow_for_principal
from fps_platform.shared.domain.actor import ActorContext, ActorType
from fps_platform.shared.domain.clock import SystemClock
from fps_platform.shared.domain.identifiers import Uuid4IdGenerator
from fps_platform.shared.infrastructure.persistence.uow import SqlAlchemyUnitOfWork


def get_contact_settings(request: Request) -> Settings:
    return cast(Settings, request.app.state.settings)


def get_contact_rate_limiter(request: Request) -> ContactRateLimiter:
    return cast(ContactRateLimiter, request.app.state.contact_rate_limiter)


def get_email_delivery_port(request: Request) -> EmailDeliveryPort:
    return cast(EmailDeliveryPort, request.app.state.email_delivery_port)


def resolve_client_ip(request: Request, settings: Settings) -> str:
    trusted_proxies = settings.contact_trusted_proxy_count
    if trusted_proxies > 0:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            candidates = [value.strip() for value in forwarded.split(",") if value.strip()]
            if candidates:
                index = max(0, len(candidates) - trusted_proxies)
                return candidates[index]
    return request.client.host if request.client is not None else "unknown"


def get_public_contact_uow(request: Request) -> Iterator[ContactUnitOfWork]:
    factory = get_session_factory(request)
    actor = ActorContext(
        actor_type=ActorType.SYSTEM,
        correlation_id=get_correlation_id(),
        request_id=get_request_id(),
    )
    with SqlAlchemyUnitOfWork(
        session_factory=factory,
        clock=SystemClock(),
        id_generator=Uuid4IdGenerator(),
        actor_context=actor,
    ) as uow:
        yield cast(ContactUnitOfWork, uow)


def get_admin_contact_uow(
    uow: SqlAlchemyUnitOfWork = Depends(get_uow_for_principal),
) -> ContactUnitOfWork:
    return cast(ContactUnitOfWork, uow)
