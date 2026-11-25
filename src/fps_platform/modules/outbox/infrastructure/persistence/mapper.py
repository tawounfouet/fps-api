from __future__ import annotations

from types import MappingProxyType
from typing import TypeGuard

from fps_platform.modules.outbox.domain.enums import OutboxEventType, OutboxStatus
from fps_platform.modules.outbox.domain.outbox_event import OutboxEvent, OutboxPayloadValue
from fps_platform.modules.outbox.infrastructure.persistence.models import OutboxEventRecord


def is_payload_value(value: object) -> TypeGuard[OutboxPayloadValue]:
    return isinstance(value, (bool, int, str)) or (
        isinstance(value, list) and all(isinstance(item, str) for item in value)
    )


def decode_payload(raw: dict[str, object]) -> dict[str, OutboxPayloadValue]:
    decoded: dict[str, OutboxPayloadValue] = {}
    for key, value in raw.items():
        if not is_payload_value(value):
            raise ValueError("Outbox payload contains an unsupported value")
        decoded[key] = value
    return decoded


def to_record(event: OutboxEvent) -> OutboxEventRecord:
    return OutboxEventRecord(
        id=event.id,
        event_type=event.event_type.value,
        aggregate_type=event.aggregate_type,
        aggregate_id=event.aggregate_id,
        operation_id=event.operation_id,
        dedup_key=event.dedup_key,
        payload_version=event.payload_version,
        payload_={key: value for key, value in event.payload.items()},
        status=event.status.value,
        created_at=event.created_at,
        available_at=event.available_at,
        completed_at=event.completed_at,
        attempt_count=event.attempt_count,
        max_attempts=event.max_attempts,
        lease_token=event.lease_token,
        leased_until=event.leased_until,
        locked_by=event.locked_by,
        last_error_code=event.last_error_code,
    )


def to_domain(record: OutboxEventRecord) -> OutboxEvent:
    return OutboxEvent(
        id=record.id,
        event_type=OutboxEventType(record.event_type),
        aggregate_type=record.aggregate_type,
        aggregate_id=record.aggregate_id,
        operation_id=record.operation_id,
        dedup_key=record.dedup_key,
        payload_version=record.payload_version,
        payload=MappingProxyType(decode_payload(record.payload_ or {})),
        status=OutboxStatus(record.status),
        created_at=record.created_at,
        available_at=record.available_at,
        completed_at=record.completed_at,
        attempt_count=record.attempt_count,
        max_attempts=record.max_attempts,
        lease_token=record.lease_token,
        leased_until=record.leased_until,
        locked_by=record.locked_by,
        last_error_code=record.last_error_code,
    )
