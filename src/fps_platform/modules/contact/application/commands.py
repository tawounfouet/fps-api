from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fps_platform.modules.contact.domain.entities import ContactDelivery, ContactSubmission
from fps_platform.modules.contact.domain.enums import (
    ContactDeliveryStatus,
    ContactLocale,
    ContactSubject,
    ContactWorkflowStatus,
)
from fps_platform.modules.contact.domain.value_objects import (
    ContactCloseReason,
    ContactEmailAddress,
    ContactIdempotencyKey,
    ContactMessage,
    ContactOptionalText,
    PersonName,
    PhoneNumber,
)


@dataclass(frozen=True, slots=True)
class SubmitContactCommand:
    idempotency_key: ContactIdempotencyKey
    first_name: PersonName
    last_name: PersonName
    email: ContactEmailAddress
    phone: PhoneNumber | None
    organisation: ContactOptionalText | None
    job_title: ContactOptionalText | None
    subject: ContactSubject
    message: ContactMessage
    locale: ContactLocale
    rgpd_consent: bool
    provider: str
    template_code: str
    recipient_group_code: str
    max_attempts: int


@dataclass(frozen=True, slots=True)
class ContactSubmissionResult:
    submission_id: UUID
    workflow_status: ContactWorkflowStatus
    delivery_status: ContactDeliveryStatus
    replayed: bool


@dataclass(frozen=True, slots=True)
class ContactCommandResult:
    submission_id: UUID
    workflow_status: ContactWorkflowStatus
    delivery_status: ContactDeliveryStatus
    version: int


@dataclass(frozen=True, slots=True)
class MarkContactedCommand:
    submission_id: UUID
    expected_version: int | None = None


@dataclass(frozen=True, slots=True)
class CloseContactCommand:
    submission_id: UUID
    reason: ContactCloseReason
    expected_version: int | None = None


@dataclass(frozen=True, slots=True)
class ReopenContactCommand:
    submission_id: UUID
    expected_version: int | None = None


@dataclass(frozen=True, slots=True)
class ArchiveContactCommand:
    submission_id: UUID
    expected_version: int | None = None


@dataclass(frozen=True, slots=True)
class RetryContactDeliveryCommand:
    submission_id: UUID
    provider: str
    max_attempts: int
    expected_version: int | None = None


@dataclass(frozen=True, slots=True)
class ContactSubmissionWithDelivery:
    submission: ContactSubmission
    delivery: ContactDelivery | None
