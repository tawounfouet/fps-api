from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session, sessionmaker

from fps_platform.modules.identity.domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    TokenValidationError,
)
from fps_platform.modules.identity.domain.permissions import permissions_for
from fps_platform.modules.identity.domain.ports import VerifiedIdentityProvider
from fps_platform.modules.identity.domain.value_objects import (
    ExternalIdentity,
    PermissionCode,
    UserStatus,
)
from fps_platform.observability.request_context import get_correlation_id, get_request_id
from fps_platform.shared.auth.principal import CurrentPrincipal
from fps_platform.shared.domain.actor import ActorContext, ActorType
from fps_platform.shared.domain.clock import SystemClock
from fps_platform.shared.domain.identifiers import Uuid4IdGenerator
from fps_platform.shared.infrastructure.persistence.uow import SqlAlchemyUnitOfWork

bearer_scheme = HTTPBearer(auto_error=False, description="API access token for the FPS admin API")
SessionFactory = sessionmaker[Session]


def get_bearer_credential(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> HTTPAuthorizationCredentials:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("AUTHENTICATION_REQUIRED")
    return credentials


def get_token_validator(request: Request) -> VerifiedIdentityProvider:
    validator: VerifiedIdentityProvider | None = getattr(request.app.state, "token_validator", None)
    if validator is None:
        raise AuthenticationError("INVALID_TOKEN")
    return validator


def get_session_factory(request: Request) -> SessionFactory:
    factory: SessionFactory | None = getattr(request.app.state, "session_factory", None)
    if factory is None:
        raise AuthenticationError("USER_NOT_PROVISIONED")
    return factory


def build_uow(
    session_factory: SessionFactory,
    *,
    actor: ActorContext,
) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(
        session_factory=session_factory,
        clock=SystemClock(),
        id_generator=Uuid4IdGenerator(),
        actor_context=actor,
    )


def _service_actor() -> ActorContext:
    return ActorContext(
        actor_type=ActorType.SERVICE,
        correlation_id=get_correlation_id(),
        request_id=get_request_id(),
    )


def get_current_principal(
    credential: HTTPAuthorizationCredentials = Depends(get_bearer_credential),
    validator: VerifiedIdentityProvider = Depends(get_token_validator),
    session_factory: SessionFactory = Depends(get_session_factory),
) -> CurrentPrincipal:
    try:
        verified = validator.validate(credential.credentials)
    except TokenValidationError as exc:
        raise AuthenticationError("INVALID_TOKEN") from exc

    identity = ExternalIdentity(verified.issuer, verified.subject)
    with build_uow(session_factory, actor=_service_actor()) as uow:
        user = uow.users.get_by_external_identity(identity)
        if user is None:
            raise AuthorizationError("USER_NOT_PROVISIONED")
        if user.status is not UserStatus.ACTIVE:
            raise AuthorizationError(f"USER_{user.status.value}")
        roles = uow.roles.list_by_ids(list(user.role_ids))
        role_codes = tuple(role.code for role in roles)
        return CurrentPrincipal(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            status=user.status,
            external_identity=identity,
            roles=role_codes,
            permissions=permissions_for(role_codes),
        )


def get_uow_for_principal(
    principal: CurrentPrincipal = Depends(get_current_principal),
    session_factory: SessionFactory = Depends(get_session_factory),
) -> Iterator[SqlAlchemyUnitOfWork]:
    actor = principal.actor_context(
        correlation_id=get_correlation_id(),
        request_id=get_request_id(),
    )
    with build_uow(session_factory, actor=actor) as uow:
        yield uow


def require_permission(permission: PermissionCode) -> Any:
    def dependency(
        principal: CurrentPrincipal = Depends(get_current_principal),
    ) -> CurrentPrincipal:
        if permission not in principal.permissions:
            raise AuthorizationError("PERMISSION_DENIED")
        return principal

    return dependency
