from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from types import MappingProxyType
from uuid import UUID

from fps_platform.modules.audit.domain.enums import AuditAction, AuditSource
from fps_platform.shared.domain.actor import CORRELATION_ID_PATTERN, REQUEST_ID_PATTERN, ActorType

type AuditMetadataValue = str | int | bool

ALLOWED_METADATA_KEYS: dict[AuditAction, frozenset[str]] = {
    AuditAction.PERSISTENCE_PROBE_CREATED: frozenset({"probe_code"}),
    AuditAction.PERSISTENCE_PROBE_UPDATED: frozenset({"from_version", "to_version"}),
    AuditAction.CONTACT_DELIVERY_REQUESTED: frozenset({"template_code", "recipient_group_code"}),
    AuditAction.CONTACT_DELIVERY_RETRIED: frozenset({"attempt_number"}),
    AuditAction.CONTACT_DELIVERY_SUCCEEDED: frozenset({"attempt_number", "provider_code"}),
    AuditAction.CONTACT_DELIVERY_FAILED: frozenset({"attempt_number", "failure_code"}),
    AuditAction.CONTACT_MARKED_CONTACTED: frozenset({"from_status", "to_status"}),
    AuditAction.CONTACT_CLOSED: frozenset({"from_status", "to_status", "reason_code"}),
    AuditAction.CONTACT_REOPENED: frozenset({"from_status", "to_status"}),
    AuditAction.CONTACT_ARCHIVED: frozenset({"from_status", "to_status"}),
    AuditAction.CONTENT_REVALIDATION_REQUESTED: frozenset({"resource_type", "locale"}),
    AuditAction.USER_CREATED: frozenset({"created_by"}),
    AuditAction.ROLE_ASSIGNED: frozenset({"role_code", "assigned_by"}),
    AuditAction.ROLE_REMOVED: frozenset({"role_code", "removed_by"}),
    AuditAction.USER_SUSPENDED: frozenset({"reason_code"}),
    AuditAction.USER_ACTIVATED: frozenset({"reason_code"}),
    AuditAction.USER_DISABLED: frozenset({"reason_code"}),
    AuditAction.MEDIA_UPLOAD_REQUESTED: frozenset({"media_asset_status", "declared_mime"}),
    AuditAction.MEDIA_UPLOAD_CONFIRMED: frozenset({"from_status", "to_status"}),
    AuditAction.MEDIA_METADATA_UPDATED: frozenset({"from_version", "to_version"}),
    AuditAction.MEDIA_ARCHIVED: frozenset({"from_status", "to_status"}),
    AuditAction.MEDIA_RESTORED: frozenset({"from_status", "to_status"}),
    AuditAction.MEDIA_RECONCILIATION_REPORTED: frozenset({"finding_count", "dry_run"}),
}
FORBIDDEN_METADATA_TERMS = (
    "authorization",
    "token",
    "password",
    "secret",
    "email",
    "phone",
    "message",
)


def normalize_metadata(
    action: AuditAction, metadata: Mapping[str, AuditMetadataValue]
) -> Mapping[str, AuditMetadataValue]:
    allowed = ALLOWED_METADATA_KEYS[action]
    normalized: dict[str, AuditMetadataValue] = {}
    for key, value in metadata.items():
        lowered = key.lower()
        if key not in allowed or any(term in lowered for term in FORBIDDEN_METADATA_TERMS):
            raise ValueError("Audit metadata key is not allowed")
        if isinstance(value, bool):
            normalized[key] = value
            continue
        if isinstance(value, int) and not isinstance(value, bool):
            if value < -(2**31) or value > 2**31 - 1:
                raise ValueError("Audit metadata integer is out of range")
            normalized[key] = value
            continue
        if isinstance(value, str):
            if len(value) > 128 or any(character in value for character in "\r\n\t"):
                raise ValueError("Audit metadata string is invalid")
            normalized[key] = value
            continue
        raise ValueError("Audit metadata value type is not allowed")
    return MappingProxyType(normalized)


@dataclass(frozen=True, slots=True)
class AuditEvent:
    id: UUID
    actor_type: ActorType
    action: AuditAction
    resource_type: str
    resource_id: UUID
    occurred_at: datetime
    correlation_id: str
    metadata: Mapping[str, AuditMetadataValue]
    source: AuditSource
    actor_id: UUID | None = None
    request_id: str | None = None

    def __post_init__(self) -> None:
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() != timedelta(0):
            raise ValueError("AuditEvent.occurred_at must be aware UTC")
        if not self.resource_type or len(self.resource_type) > 64:
            raise ValueError("AuditEvent.resource_type is invalid")
        if not CORRELATION_ID_PATTERN.fullmatch(self.correlation_id):
            raise ValueError("AuditEvent.correlation_id is invalid")
        if self.request_id is not None and not REQUEST_ID_PATTERN.fullmatch(self.request_id):
            raise ValueError("AuditEvent.request_id is invalid")
        if self.actor_type is ActorType.SYSTEM and self.actor_id is not None:
            raise ValueError("SYSTEM audit actors must not carry actor_id")
