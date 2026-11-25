from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fps_platform.modules.identity.domain.value_objects import ReasonCode, RoleCode


@dataclass(frozen=True, slots=True)
class BootstrapSuperAdminCommand:
    issuer: str
    subject: str
    email: str
    display_name: str


@dataclass(frozen=True, slots=True)
class SeedRolesCommand:
    pass


@dataclass(frozen=True, slots=True)
class AssignRoleCommand:
    user_id: UUID
    role_code: RoleCode
    expected_version: int | None = None


@dataclass(frozen=True, slots=True)
class RemoveRoleCommand:
    user_id: UUID
    role_code: RoleCode
    expected_version: int | None = None


@dataclass(frozen=True, slots=True)
class SuspendUserCommand:
    user_id: UUID
    reason_code: ReasonCode
    expected_version: int | None = None


@dataclass(frozen=True, slots=True)
class ActivateUserCommand:
    user_id: UUID
    reason_code: ReasonCode
    expected_version: int | None = None


@dataclass(frozen=True, slots=True)
class DisableUserCommand:
    user_id: UUID
    reason_code: ReasonCode
    expected_version: int | None = None


@dataclass(frozen=True, slots=True)
class IdentityCommandResult:
    user_id: UUID
    changed: bool
    version: int
    created: bool = False
