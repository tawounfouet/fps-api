from __future__ import annotations

from datetime import UTC
from types import MappingProxyType
from typing import TypeGuard

from fps_platform.modules.audit.domain.audit_event import AuditEvent, AuditMetadataValue
from fps_platform.modules.audit.domain.enums import AuditAction, AuditSource
from fps_platform.modules.audit.infrastructure.persistence.models import AuditEventRecord
from fps_platform.shared.domain.actor import ActorType


def is_metadata_value(value: object) -> TypeGuard[AuditMetadataValue]:
    return isinstance(value, (bool, int, str))


def to_record(event: AuditEvent) -> AuditEventRecord:
    return AuditEventRecord(
        id=event.id,
        actor_type=event.actor_type.value,
        actor_id=event.actor_id,
        action=event.action.value,
        resource_type=event.resource_type,
        resource_id=event.resource_id,
        occurred_at=event.occurred_at.astimezone(UTC),
        correlation_id=event.correlation_id,
        request_id=event.request_id,
        metadata_={key: value for key, value in event.metadata.items()},
        source=event.source.value,
    )


def to_domain(record: AuditEventRecord) -> AuditEvent:
    metadata = {
        key: value for key, value in (record.metadata_ or {}).items() if is_metadata_value(value)
    }
    return AuditEvent(
        id=record.id,
        actor_type=ActorType(record.actor_type),
        actor_id=record.actor_id,
        action=AuditAction(record.action),
        resource_type=record.resource_type,
        resource_id=record.resource_id,
        occurred_at=record.occurred_at,
        correlation_id=record.correlation_id,
        request_id=record.request_id,
        metadata=MappingProxyType(dict(metadata)),
        source=AuditSource(record.source),
    )
