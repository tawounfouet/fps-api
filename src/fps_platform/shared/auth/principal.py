from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fps_platform.modules.identity.domain.value_objects import (
    EmailAddress,
    ExternalIdentity,
    PermissionCode,
    RoleCode,
    UserStatus,
)
from fps_platform.shared.domain.actor import ActorContext, ActorType


@dataclass(frozen=True, slots=True)
class CurrentPrincipal:
    user_id: UUID
    email: EmailAddress
    display_name: str
    status: UserStatus
    external_identity: ExternalIdentity
    roles: tuple[RoleCode, ...]
    permissions: frozenset[PermissionCode]

    def actor_context(self, *, correlation_id: str, request_id: str | None = None) -> ActorContext:
        return ActorContext(
            actor_type=ActorType.USER,
            actor_id=self.user_id,
            correlation_id=correlation_id,
            request_id=request_id,
        )
