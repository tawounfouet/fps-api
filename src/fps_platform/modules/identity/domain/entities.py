from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID

from fps_platform.modules.identity.domain.exceptions import InvalidUserTransitionError
from fps_platform.modules.identity.domain.permissions import permissions_for
from fps_platform.modules.identity.domain.value_objects import (
    EmailAddress,
    ExternalIdentity,
    PermissionCode,
    RoleCode,
    UserStatus,
)


def require_aware_utc(value: datetime, label: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(f"{label} must be aware UTC")
    return value


@dataclass(frozen=True, slots=True)
class Role:
    id: UUID
    code: RoleCode
    name: str
    description: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        require_aware_utc(self.created_at, "created_at")
        require_aware_utc(self.updated_at, "updated_at")
        if not self.name or len(self.name) > 128:
            raise ValueError("role name is invalid")
        if len(self.description) > 256:
            raise ValueError("role description is invalid")


@dataclass(slots=True)
class User:
    id: UUID
    external_identity: ExternalIdentity
    email: EmailAddress
    display_name: str
    status: UserStatus
    role_ids: set[UUID] = field(default_factory=set)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_login_at: datetime | None = None
    suspended_at: datetime | None = None
    disabled_at: datetime | None = None
    version: int = 1

    def __post_init__(self) -> None:
        if not self.display_name or len(self.display_name) > 128:
            raise ValueError("display_name is invalid")
        if self.version < 1:
            raise ValueError("version must be positive")
        if self.created_at is not None:
            require_aware_utc(self.created_at, "created_at")
        if self.updated_at is not None:
            require_aware_utc(self.updated_at, "updated_at")
        if self.last_login_at is not None:
            require_aware_utc(self.last_login_at, "last_login_at")
        if self.suspended_at is not None:
            require_aware_utc(self.suspended_at, "suspended_at")
        if self.disabled_at is not None:
            require_aware_utc(self.disabled_at, "disabled_at")

    def _touch(self, now: datetime) -> None:
        self.updated_at = require_aware_utc(now, "now")
        self.version += 1

    def replace_email(self, email: EmailAddress, now: datetime) -> None:
        self.email = email
        self._touch(now)

    def assign_role(self, role_id: UUID, now: datetime) -> bool:
        if self.status is not UserStatus.ACTIVE:
            raise InvalidUserTransitionError("roles can only change for ACTIVE users")
        if role_id in self.role_ids:
            return False
        self.role_ids.add(role_id)
        self._touch(now)
        return True

    def remove_role(self, role_id: UUID, now: datetime) -> bool:
        if self.status is not UserStatus.ACTIVE:
            raise InvalidUserTransitionError("roles can only change for ACTIVE users")
        if role_id not in self.role_ids:
            return False
        self.role_ids.remove(role_id)
        self._touch(now)
        return True

    def suspend(self, now: datetime) -> None:
        if self.status is not UserStatus.ACTIVE:
            raise InvalidUserTransitionError("only ACTIVE users can be suspended")
        self.status = UserStatus.SUSPENDED
        self.suspended_at = require_aware_utc(now, "now")
        self._touch(now)

    def activate(self, now: datetime) -> None:
        if self.status is not UserStatus.SUSPENDED:
            raise InvalidUserTransitionError("only SUSPENDED users can be activated")
        self.status = UserStatus.ACTIVE
        self.suspended_at = None
        self._touch(now)

    def disable(self, now: datetime) -> None:
        if self.status is UserStatus.DISABLED:
            raise InvalidUserTransitionError("user is already disabled")
        self.status = UserStatus.DISABLED
        self.disabled_at = require_aware_utc(now, "now")
        self._touch(now)

    def effective_permissions(self, roles_by_id: dict[UUID, Role]) -> frozenset[PermissionCode]:
        codes = [roles_by_id[role_id].code for role_id in self.role_ids if role_id in roles_by_id]
        return permissions_for(codes)


def role_code_by_id(roles: list[Role]) -> dict[UUID, RoleCode]:
    return {role.id: role.code for role in roles}
