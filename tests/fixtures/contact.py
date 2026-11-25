from __future__ import annotations

from threading import Event
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy.orm import DeclarativeBase

from fps_platform.modules.audit.application.recorder import AuditRecorder
from fps_platform.modules.audit.infrastructure.persistence.models import AuditEventRecord
from fps_platform.modules.contact.application import handlers
from fps_platform.modules.contact.application.commands import SubmitContactCommand
from fps_platform.modules.contact.application.ports import (
    ContactEmailMessage,
    ContactUnitOfWork,
    EmailDeliveryPort,
    EmailDeliveryReceipt,
)
from fps_platform.modules.contact.domain.enums import ContactLocale, ContactSubject
from fps_platform.modules.contact.domain.value_objects import (
    ContactEmailAddress,
    ContactIdempotencyKey,
    ContactMessage,
    ContactOptionalText,
    PersonName,
)
from fps_platform.modules.contact.infrastructure.persistence.models import (
    ContactDeliveryRecord,
    ContactIdempotencyKeyRecord,
    ContactSubmissionRecord,
)
from fps_platform.modules.contact.infrastructure.persistence.repository import (
    SqlAlchemyContactDeliveryRepository,
    SqlAlchemyContactIdempotencyRepository,
    SqlAlchemyContactSubmissionRepository,
)
from fps_platform.modules.outbox.infrastructure.persistence.models import OutboxEventRecord
from fps_platform.modules.outbox.infrastructure.persistence.repository import (
    SqlAlchemyOutboxEventRepository,
)
from fps_platform.shared.domain.clock import Clock
from fps_platform.workers.contact_delivery import (
    ContactDeliveryWorker,
    build_contact_delivery_worker,
)
from tests.integration.conftest import MakeUow


def new_command(*, key: str | None = None) -> SubmitContactCommand:
    return SubmitContactCommand(
        idempotency_key=ContactIdempotencyKey(key or f"closure_{uuid4().hex}"),
        first_name=PersonName("Ada"),
        last_name=PersonName("Lovelace"),
        email=ContactEmailAddress("ada@example.test"),
        phone=None,
        organisation=ContactOptionalText("Analytical Engines"),
        job_title=None,
        subject=ContactSubject.PARTENARIAT,
        message=ContactMessage("Bonjour"),
        locale=ContactLocale.FR,
        rgpd_consent=True,
        provider="mock",
        template_code="contact_request",
        recipient_group_code="contact_team",
        max_attempts=5,
    )


def submit_contact(
    make_uow: MakeUow,
    command: SubmitContactCommand | None = None,
    *,
    clock: Clock | None = None,
) -> UUID:
    payload = command or new_command()
    with make_uow(clock=clock) as uow:
        result = handlers.submit_contact(cast(ContactUnitOfWork, uow), payload)
        uow.commit()
    return result.submission_id


def build_worker(
    make_uow: MakeUow,
    email_port: EmailDeliveryPort,
    clock: Clock,
    *,
    worker_id: str = "worker",
    retry_delays_seconds: tuple[int, ...] = (60, 300, 1500, 7200),
    lease_seconds: int = 60,
) -> ContactDeliveryWorker:
    def uow_factory() -> ContactUnitOfWork:
        return cast(ContactUnitOfWork, make_uow())

    return build_contact_delivery_worker(
        uow_factory=uow_factory,
        email_port=email_port,
        clock=clock,
        provider="mock",
        retry_delays_seconds=list(retry_delays_seconds),
        lease_seconds=lease_seconds,
        worker_id=worker_id,
    )


class BlockingEmailPort(EmailDeliveryPort):
    def __init__(self, entered: Event, release: Event) -> None:
        self._entered = entered
        self._release = release
        self.calls: list[tuple[UUID, str]] = []

    def send(self, message: ContactEmailMessage) -> EmailDeliveryReceipt:
        self.calls.append((message.submission_id, message.idempotency_key))
        self._entered.set()
        if not self._release.wait(10):
            raise TimeoutError("email port was not released")
        return EmailDeliveryReceipt(provider="mock", provider_reference="mock_blocking")


class CrashEmailPort(EmailDeliveryPort):
    def __init__(self) -> None:
        self.calls: list[tuple[UUID, str]] = []

    def send(self, message: ContactEmailMessage) -> EmailDeliveryReceipt:
        self.calls.append((message.submission_id, message.idempotency_key))
        raise KeyboardInterrupt("simulated worker crash")


INJECTION_TARGETS: dict[str, tuple[type[object], str]] = {
    "idempotency": (SqlAlchemyContactIdempotencyRepository, "claim"),
    "submission": (SqlAlchemyContactSubmissionRepository, "add"),
    "delivery": (SqlAlchemyContactDeliveryRepository, "add"),
    "outbox": (SqlAlchemyOutboxEventRepository, "append"),
    "audit": (AuditRecorder, "record"),
}

CONTACT_TABLES: tuple[type[DeclarativeBase], ...] = (
    ContactDeliveryRecord,
    ContactIdempotencyKeyRecord,
    ContactSubmissionRecord,
    OutboxEventRecord,
    AuditEventRecord,
)
