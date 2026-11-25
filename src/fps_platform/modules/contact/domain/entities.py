from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fps_platform.modules.contact.domain.enums import (
    ContactDeliveryChannel,
    ContactDeliveryStatus,
    ContactLocale,
    ContactSource,
    ContactSubject,
    ContactWorkflowStatus,
)
from fps_platform.modules.contact.domain.exceptions import (
    InvalidContactTransitionError,
)
from fps_platform.modules.contact.domain.value_objects import (
    ContactCloseReason,
    ContactEmailAddress,
    ContactMessage,
    ContactOptionalText,
    PersonName,
    PhoneNumber,
    normalize_failure_code,
    normalize_provider_reference,
)


def require_aware_utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must be aware UTC")
    return value.astimezone(UTC)


@dataclass(slots=True)
class ContactSubmission:
    id: UUID
    first_name: PersonName
    last_name: PersonName
    email: ContactEmailAddress
    subject: ContactSubject
    message: ContactMessage
    locale: ContactLocale
    source: ContactSource
    workflow_status: ContactWorkflowStatus
    received_at: datetime
    updated_at: datetime
    version: int
    phone: PhoneNumber | None = None
    organisation: ContactOptionalText | None = None
    job_title: ContactOptionalText | None = None
    rgpd_consent: bool = False
    contacted_at: datetime | None = None
    closed_at: datetime | None = None
    archived_at: datetime | None = None
    close_reason: ContactCloseReason | None = None

    def __post_init__(self) -> None:
        require_aware_utc(self.received_at, "received_at")
        require_aware_utc(self.updated_at, "updated_at")
        if self.version < 1:
            raise ValueError("version must be positive")

    def _touch(self, now: datetime) -> None:
        self.updated_at = require_aware_utc(now, "now")
        self.version += 1

    def mark_contacted(self, now: datetime) -> None:
        if self.workflow_status is not ContactWorkflowStatus.RECEIVED:
            raise InvalidContactTransitionError("only RECEIVED contacts can be marked CONTACTED")
        moment = require_aware_utc(now, "now")
        self.workflow_status = ContactWorkflowStatus.CONTACTED
        self.contacted_at = moment
        self._touch(moment)

    def close(self, now: datetime, reason: ContactCloseReason) -> None:
        if self.workflow_status not in {
            ContactWorkflowStatus.RECEIVED,
            ContactWorkflowStatus.CONTACTED,
        }:
            raise InvalidContactTransitionError("only RECEIVED or CONTACTED contacts can be closed")
        moment = require_aware_utc(now, "now")
        self.workflow_status = ContactWorkflowStatus.CLOSED
        self.closed_at = moment
        self.close_reason = reason
        self._touch(moment)

    def reopen(self, now: datetime) -> None:
        if self.workflow_status is not ContactWorkflowStatus.CLOSED:
            raise InvalidContactTransitionError("only CLOSED contacts can be reopened")
        moment = require_aware_utc(now, "now")
        self.workflow_status = ContactWorkflowStatus.CONTACTED
        self.closed_at = None
        self.close_reason = None
        self._touch(moment)

    def archive(self, now: datetime) -> None:
        if self.workflow_status is not ContactWorkflowStatus.CLOSED:
            raise InvalidContactTransitionError("only CLOSED contacts can be archived")
        moment = require_aware_utc(now, "now")
        self.workflow_status = ContactWorkflowStatus.ARCHIVED
        self.archived_at = moment
        self._touch(moment)


@dataclass(slots=True)
class ContactDelivery:
    id: UUID
    submission_id: UUID
    channel: ContactDeliveryChannel
    provider: str
    status: ContactDeliveryStatus
    attempt_number: int
    requested_at: datetime
    attempted_at: datetime | None = None
    completed_at: datetime | None = None
    provider_reference: str | None = None
    failure_code: str | None = None

    def __post_init__(self) -> None:
        require_aware_utc(self.requested_at, "requested_at")
        if self.attempt_number < 1:
            raise ValueError("attempt_number must be positive")
        if not self.provider or len(self.provider) > 64:
            raise ValueError("provider is invalid")

    def mark_in_progress(self, now: datetime) -> None:
        if self.status is not ContactDeliveryStatus.PENDING:
            raise InvalidContactTransitionError("only PENDING deliveries can be started")
        moment = require_aware_utc(now, "now")
        self.status = ContactDeliveryStatus.IN_PROGRESS
        self.attempted_at = moment

    def mark_succeeded(self, now: datetime, provider_reference: str) -> None:
        if self.status is not ContactDeliveryStatus.IN_PROGRESS:
            raise InvalidContactTransitionError("only IN_PROGRESS deliveries can succeed")
        moment = require_aware_utc(now, "now")
        reference = normalize_provider_reference(provider_reference)
        self.status = ContactDeliveryStatus.SUCCEEDED
        self.completed_at = moment
        self.provider_reference = reference
        self.failure_code = None

    def mark_failed(self, now: datetime, failure_code: str) -> None:
        if self.status is not ContactDeliveryStatus.IN_PROGRESS:
            raise InvalidContactTransitionError("only IN_PROGRESS deliveries can fail")
        moment = require_aware_utc(now, "now")
        self.status = ContactDeliveryStatus.FAILED
        self.completed_at = moment
        self.failure_code = normalize_failure_code(failure_code)
        self.provider_reference = None
