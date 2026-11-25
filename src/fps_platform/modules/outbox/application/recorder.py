from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from fps_platform.modules.outbox.domain.enums import OutboxEventType, OutboxStatus
from fps_platform.modules.outbox.domain.outbox_event import (
    OutboxEvent,
    OutboxPayloadValue,
    normalize_payload,
)
from fps_platform.modules.outbox.domain.ports import OutboxEventRepository
from fps_platform.shared.domain.clock import Clock
from fps_platform.shared.domain.identifiers import IdGenerator


@dataclass(frozen=True, slots=True)
class OutboxRecorder:
    repository: OutboxEventRepository
    clock: Clock
    id_generator: IdGenerator

    def record(
        self,
        *,
        event_type: OutboxEventType,
        aggregate_type: str,
        aggregate_id: UUID,
        operation_id: str,
        dedup_key: str,
        payload: Mapping[str, OutboxPayloadValue],
        payload_version: int = 1,
        max_attempts: int = 8,
    ) -> OutboxEvent:
        created_at = self.clock.now()
        event = OutboxEvent(
            id=self.id_generator.new_id(),
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            operation_id=operation_id,
            dedup_key=dedup_key,
            payload_version=payload_version,
            payload=normalize_payload(event_type, payload),
            status=OutboxStatus.PENDING,
            created_at=created_at,
            available_at=created_at,
            max_attempts=max_attempts,
        )
        self.repository.append(event)
        return event
