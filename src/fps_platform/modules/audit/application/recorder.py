from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from fps_platform.modules.audit.domain.audit_event import (
    AuditEvent,
    AuditMetadataValue,
    normalize_metadata,
)
from fps_platform.modules.audit.domain.enums import AuditAction, AuditSource
from fps_platform.modules.audit.domain.ports import AuditEventRepository
from fps_platform.shared.domain.actor import ActorContext
from fps_platform.shared.domain.clock import Clock
from fps_platform.shared.domain.identifiers import IdGenerator


@dataclass(frozen=True, slots=True)
class AuditRecorder:
    repository: AuditEventRepository
    clock: Clock
    id_generator: IdGenerator
    actor_context: ActorContext

    def record(
        self,
        *,
        action: AuditAction,
        resource_type: str,
        resource_id: UUID,
        metadata: Mapping[str, AuditMetadataValue] | None = None,
        source: AuditSource = AuditSource.APPLICATION,
    ) -> AuditEvent:
        event = AuditEvent(
            id=self.id_generator.new_id(),
            actor_type=self.actor_context.actor_type,
            actor_id=self.actor_context.actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            occurred_at=self.clock.now(),
            correlation_id=self.actor_context.correlation_id,
            request_id=self.actor_context.request_id,
            metadata=normalize_metadata(action, metadata or {}),
            source=source,
        )
        self.repository.append(event)
        return event
