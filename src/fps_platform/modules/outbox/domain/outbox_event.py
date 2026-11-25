from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import MappingProxyType
from uuid import UUID

from fps_platform.modules.outbox.domain.enums import OutboxEventType, OutboxStatus

type OutboxPayloadValue = str | int | bool | list[str]

ALLOWED_PAYLOAD_KEYS: dict[OutboxEventType, frozenset[str]] = {
    OutboxEventType.CONTACT_DELIVERY_REQUESTED: frozenset(
        {"contact_submission_id", "delivery_intent_id", "template_code", "recipient_group_code"}
    ),
    OutboxEventType.CONTENT_REVALIDATION_REQUESTED: frozenset(
        {
            "resource_type",
            "resource_id",
            "publication_revision_id",
            "locale",
            "normalized_paths",
            "publication_sequence",
        }
    ),
}
FORBIDDEN_PAYLOAD_TERMS = (
    "authorization",
    "token",
    "password",
    "secret",
    "email",
    "phone",
    "message",
)


def normalize_payload(
    event_type: OutboxEventType, payload: Mapping[str, OutboxPayloadValue]
) -> Mapping[str, OutboxPayloadValue]:
    allowed = ALLOWED_PAYLOAD_KEYS[event_type]
    normalized: dict[str, OutboxPayloadValue] = {}
    for key, value in payload.items():
        lowered = key.lower()
        if key not in allowed or any(term in lowered for term in FORBIDDEN_PAYLOAD_TERMS):
            raise ValueError("Outbox payload key is not allowed")
        if isinstance(value, bool):
            normalized[key] = value
            continue
        if isinstance(value, int) and not isinstance(value, bool):
            if value < 0 or value > 2**31 - 1:
                raise ValueError("Outbox payload integer is out of range")
            normalized[key] = value
            continue
        if isinstance(value, str):
            if len(value) > 256 or any(character in value for character in "\r\n\t"):
                raise ValueError("Outbox payload string is invalid")
            normalized[key] = value
            continue
        if isinstance(value, list):
            if len(value) > 20 or any(
                not isinstance(item, str)
                or len(item) > 256
                or any(character in item for character in "\r\n\t")
                for item in value
            ):
                raise ValueError("Outbox payload path list is invalid")
            normalized[key] = value
            continue
        raise ValueError("Outbox payload value type is not allowed")
    return MappingProxyType(normalized)


def require_aware_utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must be aware UTC")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class OutboxEvent:
    id: UUID
    event_type: OutboxEventType
    aggregate_type: str
    aggregate_id: UUID
    operation_id: str
    dedup_key: str
    payload_version: int
    payload: Mapping[str, OutboxPayloadValue]
    status: OutboxStatus
    created_at: datetime
    available_at: datetime
    max_attempts: int
    attempt_count: int = 0
    completed_at: datetime | None = None
    lease_token: UUID | None = None
    leased_until: datetime | None = None
    locked_by: str | None = None
    last_error_code: str | None = None

    def __post_init__(self) -> None:
        require_aware_utc(self.created_at, "created_at")
        require_aware_utc(self.available_at, "available_at")
        if self.completed_at is not None:
            require_aware_utc(self.completed_at, "completed_at")
        if self.leased_until is not None:
            require_aware_utc(self.leased_until, "leased_until")
        if not self.aggregate_type or len(self.aggregate_type) > 64:
            raise ValueError("aggregate_type is invalid")
        if not self.operation_id or len(self.operation_id) > 128:
            raise ValueError("operation_id is invalid")
        if not self.dedup_key or len(self.dedup_key) > 128:
            raise ValueError("dedup_key is invalid")
        if self.payload_version < 1 or self.payload_version > 100:
            raise ValueError("payload_version is invalid")
        if self.max_attempts < 1 or self.max_attempts > 100:
            raise ValueError("max_attempts is invalid")
        if self.attempt_count < 0 or self.attempt_count > self.max_attempts:
            raise ValueError("attempt_count is invalid")
        if self.status is OutboxStatus.COMPLETED and self.completed_at is None:
            raise ValueError("COMPLETED events require completed_at")
        if self.status is OutboxStatus.LEASED and (
            self.lease_token is None or self.leased_until is None
        ):
            raise ValueError("LEASED events require lease fields")
        if self.last_error_code is not None and len(self.last_error_code) > 64:
            raise ValueError("last_error_code is invalid")
