from __future__ import annotations

from collections.abc import Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from fps_platform.modules.identity.domain.entities import Role, User
from fps_platform.modules.identity.domain.value_objects import (
    ExternalIdentity,
    RoleCode,
    UserStatus,
)


class UserRepository(Protocol):
    def add(self, user: User) -> None: ...

    def get(self, user_id: UUID) -> User | None: ...

    def get_by_external_identity(self, identity: ExternalIdentity) -> User | None: ...

    def list(
        self,
        *,
        limit: int,
        offset: int,
        status: UserStatus | None = None,
    ) -> Sequence[User]: ...

    def count(self, *, status: UserStatus | None = None) -> int: ...

    def save(self, user: User, *, expected_version: int | None = None) -> None: ...

    def count_active_with_role(self, role_code: RoleCode) -> int: ...

    def add_role_assignment(self, user_id: UUID, role_id: UUID) -> None: ...

    def remove_role_assignment(self, user_id: UUID, role_id: UUID) -> None: ...

    def has_role_assignment(self, user_id: UUID, role_id: UUID) -> bool: ...


class RoleRepository(Protocol):
    def add(self, role: Role) -> None: ...

    def get(self, role_id: UUID) -> Role | None: ...

    def get_by_code(self, code: RoleCode) -> Role | None: ...

    def list(self) -> Sequence[Role]: ...

    def list_by_ids(self, role_ids: Sequence[UUID]) -> Sequence[Role]: ...


class SuperAdminGuard(Protocol):
    def lock(self) -> AbstractContextManager[None]: ...


@dataclass(frozen=True, slots=True)
class VerifiedIdentity:
    issuer: str
    subject: str


class VerifiedIdentityProvider(Protocol):
    def validate(self, token: str) -> VerifiedIdentity: ...
