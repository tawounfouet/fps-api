from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from fps_platform.modules.contact.application.ports import (
    ContactEmailMessage,
    EmailDeliveryReceipt,
)
from fps_platform.modules.contact.domain.enums import ContactDeliveryStatus
from fps_platform.modules.contact.infrastructure.email import MockEmailDeliveryPort
from fps_platform.modules.contact.infrastructure.persistence.models import ContactDeliveryRecord
from fps_platform.modules.outbox.domain.enums import OutboxStatus
from fps_platform.modules.outbox.infrastructure.persistence.models import OutboxEventRecord
from fps_platform.shared.domain.clock import FakeClock
from tests.fixtures.contact import CrashEmailPort, build_worker, submit_contact
from tests.integration.conftest import MakeUow

pytestmark = pytest.mark.integration

MOMENT = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)


class CountingEmailPort(MockEmailDeliveryPort):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[UUID, str]] = []

    def send(self, message: ContactEmailMessage) -> EmailDeliveryReceipt:
        self.calls.append((message.submission_id, message.idempotency_key))
        return super().send(message)


def test_crash_after_claim_is_rediscovered_without_duplicate_delivery(
    make_uow: MakeUow, session_factory: sessionmaker[Session]
) -> None:
    clock = FakeClock(MOMENT)
    submission_id = submit_contact(make_uow, clock=clock)
    crash_port = CrashEmailPort()
    crashed = build_worker(
        make_uow,
        crash_port,
        clock,
        worker_id="crashed-worker",
        retry_delays_seconds=(0,),
        lease_seconds=60,
    )

    with pytest.raises(KeyboardInterrupt):
        crashed.run_once(limit=20)

    assert [call[0] for call in crash_port.calls] == [submission_id]
    idempotency_key = crash_port.calls[0][1]
    with session_factory() as session:
        events_after_crash = list(session.scalars(select(OutboxEventRecord)).all())
        deliveries_after_crash = list(session.scalars(select(ContactDeliveryRecord)).all())
    assert len(events_after_crash) == 1
    assert events_after_crash[0].status == OutboxStatus.LEASED.value
    assert len(deliveries_after_crash) == 1
    assert deliveries_after_crash[0].status == ContactDeliveryStatus.IN_PROGRESS.value

    clock.advance(seconds=61)
    recovery_port = CountingEmailPort()
    recovered = build_worker(
        make_uow,
        recovery_port,
        clock,
        worker_id="recovered-worker",
        retry_delays_seconds=(0,),
        lease_seconds=60,
    )

    stale_stats = recovered.run_once(limit=20)
    assert stale_stats.released == 1
    assert stale_stats.retried == 1
    assert stale_stats.succeeded == 0

    final_stats = recovered.run_once(limit=20)
    assert final_stats.succeeded == 1
    assert recovery_port.calls == [(submission_id, idempotency_key)]

    with session_factory() as session:
        events = list(session.scalars(select(OutboxEventRecord)).all())
        deliveries = list(session.scalars(select(ContactDeliveryRecord)).all())
    assert len(events) == 1
    assert events[0].status == OutboxStatus.COMPLETED.value
    assert len(deliveries) == 2
    succeeded = [
        item for item in deliveries if item.status == ContactDeliveryStatus.SUCCEEDED.value
    ]
    assert len(succeeded) == 1
