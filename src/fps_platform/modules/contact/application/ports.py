from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from fps_platform.modules.audit.application.recorder import AuditRecorder
from fps_platform.modules.contact.domain.entities import ContactDelivery, ContactSubmission
from fps_platform.modules.contact.domain.enums import (
    ContactLocale,
    ContactSubject,
    ContactWorkflowStatus,
)
from fps_platform.modules.contact.domain.value_objects import (
    ContactEmailAddress,
    ContactMessage,
    ContactOptionalText,
    PersonName,
    PhoneNumber,
)
from fps_platform.modules.outbox.application.recorder import OutboxRecorder
from fps_platform.modules.outbox.domain.ports import OutboxEventRepository
from fps_platform.shared.application.uow import UnitOfWork
from fps_platform.shared.domain.actor import ActorContext
from fps_platform.shared.domain.clock import Clock
from fps_platform.shared.domain.identifiers import IdGenerator


class ContactSubmissionRepository(Protocol):
    def add(self, submission: ContactSubmission) -> None: ...

    def get(self, submission_id: UUID) -> ContactSubmission | None: ...

    def list(
        self,
        *,
        limit: int,
        offset: int,
        workflow_status: ContactWorkflowStatus | None = None,
    ) -> Sequence[ContactSubmission]: ...

    def count(self, *, workflow_status: ContactWorkflowStatus | None = None) -> int: ...

    def save(
        self, submission: ContactSubmission, *, expected_version: int | None = None
    ) -> None: ...


class ContactDeliveryRepository(Protocol):
    def add(self, delivery: ContactDelivery) -> None: ...

    def get(self, delivery_id: UUID) -> ContactDelivery | None: ...

    def list_by_submission(self, submission_id: UUID) -> Sequence[ContactDelivery]: ...

    def latest(self, submission_id: UUID) -> ContactDelivery | None: ...

    def next_attempt_number(self, submission_id: UUID) -> int: ...

    def save(self, delivery: ContactDelivery) -> None: ...


class ContactIdempotencyRepository(Protocol):
    def claim(self, *, key_hash: str, fingerprint: str, submission_id: UUID) -> UUID | None: ...

    def get(self, *, key_hash: str) -> tuple[str, UUID] | None: ...


class ContactRateLimiter(Protocol):
    def retry_after(self, client_ip: str, *, limit: int, window_seconds: int) -> int: ...


@dataclass(frozen=True, slots=True)
class ContactEmailMessage:
    submission_id: UUID
    idempotency_key: str
    template_code: str
    recipient_group_code: str
    locale: ContactLocale
    subject: ContactSubject
    first_name: PersonName
    last_name: PersonName
    email: ContactEmailAddress
    phone: PhoneNumber | None
    organisation: ContactOptionalText | None
    job_title: ContactOptionalText | None
    message: ContactMessage
    rgpd_consent: bool
    correlation_id: str


@dataclass(frozen=True, slots=True)
class EmailDeliveryReceipt:
    provider: str
    provider_reference: str


class EmailDeliveryPort(Protocol):
    def send(self, message: ContactEmailMessage) -> EmailDeliveryReceipt: ...


class ContactUnitOfWork(UnitOfWork, Protocol):
    clock: Clock
    id_generator: IdGenerator
    actor_context: ActorContext
    contacts: ContactSubmissionRepository
    deliveries: ContactDeliveryRepository
    idempotency_keys: ContactIdempotencyRepository
    outbox_recorder: OutboxRecorder
    outbox_events: OutboxEventRepository
    audit_recorder: AuditRecorder

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
