from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from fps_platform.modules.outbox.domain.enums import OutboxStatus
from fps_platform.modules.outbox.domain.outbox_event import OutboxEvent


class OutboxEventRepository(Protocol):
    def append(self, event: OutboxEvent) -> None: ...

    def get(self, event_id: UUID) -> OutboxEvent | None: ...

    def list_available(self, *, status: OutboxStatus, limit: int = 20) -> list[OutboxEvent]: ...

    def list_due(self, *, now: datetime, limit: int = 20) -> list[OutboxEvent]: ...

    def claim(
        self,
        *,
        event_id: UUID,
        lease_token: UUID,
        leased_until: datetime,
        locked_by: str,
        now: datetime,
    ) -> bool: ...

    def complete(self, *, event_id: UUID, completed_at: datetime) -> None: ...

    def mark_retry_wait(
        self,
        *,
        event_id: UUID,
        available_at: datetime,
        last_error_code: str,
    ) -> None: ...

    def mark_dead(self, *, event_id: UUID, last_error_code: str) -> None: ...

    def release_expired(self, *, now: datetime, limit: int = 20) -> int: ...
