from __future__ import annotations

from typing import Protocol
from uuid import UUID

from fps_platform.modules.outbox.domain.enums import OutboxStatus
from fps_platform.modules.outbox.domain.outbox_event import OutboxEvent


class OutboxEventRepository(Protocol):
    def append(self, event: OutboxEvent) -> None: ...

    def get(self, event_id: UUID) -> OutboxEvent | None: ...

    def list_available(self, *, status: OutboxStatus, limit: int = 20) -> list[OutboxEvent]: ...
