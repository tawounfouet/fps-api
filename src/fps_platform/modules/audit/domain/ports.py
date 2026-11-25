from __future__ import annotations

from typing import Protocol
from uuid import UUID

from fps_platform.modules.audit.domain.audit_event import AuditEvent


class AuditEventRepository(Protocol):
    def append(self, event: AuditEvent) -> None: ...

    def get(self, event_id: UUID) -> AuditEvent | None: ...

    def list_by_resource(
        self, *, resource_type: str, resource_id: UUID, limit: int = 100
    ) -> list[AuditEvent]: ...
