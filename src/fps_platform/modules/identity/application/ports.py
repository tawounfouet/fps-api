from __future__ import annotations

from typing import Protocol

from fps_platform.modules.audit.application.recorder import AuditRecorder
from fps_platform.modules.identity.domain.ports import (
    RoleRepository,
    SuperAdminGuard,
    UserRepository,
)
from fps_platform.shared.domain.clock import Clock
from fps_platform.shared.domain.identifiers import IdGenerator


class IdentityUnitOfWork(Protocol):
    clock: Clock
    id_generator: IdGenerator

    @property
    def users(self) -> UserRepository: ...

    @property
    def roles(self) -> RoleRepository: ...

    @property
    def super_admin_guard(self) -> SuperAdminGuard: ...

    @property
    def audit_recorder(self) -> AuditRecorder: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
