from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from fps_platform.modules.contact.application import handlers
from fps_platform.modules.contact.application.commands import SubmitContactCommand
from fps_platform.modules.contact.application.ports import (
    ContactEmailMessage,
    ContactUnitOfWork,
    EmailDeliveryPort,
    EmailDeliveryReceipt,
)
from fps_platform.modules.contact.domain.enums import (
    ContactDeliveryStatus,
    ContactLocale,
    ContactSubject,
)
from fps_platform.modules.contact.domain.exceptions import RetryableContactDeliveryError
from fps_platform.modules.contact.domain.value_objects import (
    ContactEmailAddress,
    ContactIdempotencyKey,
    ContactMessage,
    ContactOptionalText,
    PersonName,
)
from fps_platform.modules.contact.infrastructure.email import MockEmailDeliveryPort
from fps_platform.modules.contact.infrastructure.persistence.models import ContactDeliveryRecord
from fps_platform.modules.outbox.domain.enums import OutboxStatus
from fps_platform.modules.outbox.infrastructure.persistence.models import OutboxEventRecord
from fps_platform.shared.domain.clock import Clock, FakeClock, SystemClock
from fps_platform.workers.contact_delivery import (
    ContactDeliveryWorker,
    build_contact_delivery_worker,
)
from tests.integration.conftest import MakeUow

pytestmark = pytest.mark.integration

MOMENT = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)


class FailingEmailPort(EmailDeliveryPort):
    def send(self, message: ContactEmailMessage) -> EmailDeliveryReceipt:
        raise RetryableContactDeliveryError("provider timeout")


def submit(make_uow: MakeUow, clock: Clock | None = None) -> None:
    with make_uow(clock=clock) as uow:
        handlers.submit_contact(
            cast(ContactUnitOfWork, uow),
            SubmitContactCommand(
                idempotency_key=ContactIdempotencyKey("worker_submission_0001"),
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
            ),
        )
        uow.commit()


def build_worker(
    make_uow: MakeUow,
    email_port: EmailDeliveryPort,
    clock: Clock,
    *,
    delays: tuple[int, ...] = (60, 300, 1500, 7200),
) -> ContactDeliveryWorker:
    def uow_factory() -> ContactUnitOfWork:
        return cast(ContactUnitOfWork, make_uow())

    return build_contact_delivery_worker(
        uow_factory=uow_factory,
        email_port=email_port,
        clock=clock,
        provider="mock",
        retry_delays_seconds=list(delays),
        lease_seconds=60,
    )


def test_worker_marks_delivery_and_outbox_as_succeeded(
    make_uow: MakeUow,
    session_factory: sessionmaker[Session],
) -> None:
    submit(make_uow)
    worker = build_worker(make_uow, MockEmailDeliveryPort(), SystemClock())
    stats = worker.run_once(limit=20)
    assert stats.succeeded == 1
    with session_factory() as session:
        deliveries = session.scalars(select(ContactDeliveryRecord)).all()
        events = session.scalars(select(OutboxEventRecord)).all()
    assert len(deliveries) == 1
    assert deliveries[0].status == ContactDeliveryStatus.SUCCEEDED.value
    assert deliveries[0].provider_reference is not None
    assert events[0].status == OutboxStatus.COMPLETED.value


def test_worker_exhausts_retries_then_marks_outbox_dead(
    make_uow: MakeUow,
    session_factory: sessionmaker[Session],
) -> None:
    clock = FakeClock(MOMENT)
    submit(make_uow, clock)
    worker = build_worker(make_uow, FailingEmailPort(), clock, delays=(0, 0, 0, 0))
    for _ in range(5):
        worker.run_once(limit=20)
    with session_factory() as session:
        deliveries = session.scalars(select(ContactDeliveryRecord)).all()
        events = session.scalars(select(OutboxEventRecord)).all()
    assert len(deliveries) == 5
    assert all(item.status == ContactDeliveryStatus.FAILED.value for item in deliveries)
    assert events[0].status == OutboxStatus.DEAD.value
    assert events[0].attempt_count == 5
