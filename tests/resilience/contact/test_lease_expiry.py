from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Event
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from fps_platform.modules.contact.application.ports import (
    ContactEmailMessage,
    EmailDeliveryPort,
    EmailDeliveryReceipt,
)
from fps_platform.modules.contact.domain.enums import ContactDeliveryStatus
from fps_platform.modules.contact.infrastructure.email import MockEmailDeliveryPort
from fps_platform.modules.contact.infrastructure.persistence.models import ContactDeliveryRecord
from fps_platform.modules.outbox.domain.enums import OutboxStatus
from fps_platform.modules.outbox.infrastructure.persistence.models import OutboxEventRecord
from fps_platform.shared.domain.clock import FakeClock
from tests.fixtures.contact import build_worker, submit_contact
from tests.integration.conftest import MakeUow

pytestmark = pytest.mark.integration

MOMENT = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)


class GatedEmailPort(EmailDeliveryPort):
    def __init__(self, entered: Event, release: Event, delegate: EmailDeliveryPort) -> None:
        self._entered = entered
        self._release = release
        self._delegate = delegate
        self.calls: list[tuple[UUID, str]] = []

    def send(self, message: ContactEmailMessage) -> EmailDeliveryReceipt:
        self.calls.append((message.submission_id, message.idempotency_key))
        self._entered.set()
        if not self._release.wait(10):
            raise TimeoutError("email port was not released")
        return self._delegate.send(message)


def test_lease_expiry_keeps_db_consistent_and_reuses_provider_key(
    make_uow: MakeUow, session_factory: sessionmaker[Session]
) -> None:
    clock = FakeClock(MOMENT)
    submission_id = submit_contact(make_uow, clock=clock)
    shared_provider = MockEmailDeliveryPort()
    first_entered = Event()
    first_release = Event()
    second_entered = Event()
    second_release = Event()
    first_port = GatedEmailPort(first_entered, first_release, shared_provider)
    second_port = GatedEmailPort(second_entered, second_release, shared_provider)
    first_worker = build_worker(
        make_uow,
        first_port,
        clock,
        worker_id="slow-worker",
        lease_seconds=1,
        retry_delays_seconds=(0,),
    )
    second_worker = build_worker(
        make_uow,
        second_port,
        clock,
        worker_id="replacement-worker",
        lease_seconds=1,
        retry_delays_seconds=(0,),
    )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_result = pool.submit(first_worker.run_once, limit=20)
        assert first_entered.wait(10)
        clock.advance(seconds=2)
        stale_result = pool.submit(second_worker.run_once, limit=20)
        stale_stats = stale_result.result(timeout=20)
        final_result = pool.submit(second_worker.run_once, limit=20)
        assert second_entered.wait(10)
        second_release.set()
        final_stats = final_result.result(timeout=20)
        first_release.set()
        first_stats = first_result.result(timeout=20)

    assert stale_stats.retried == 1
    assert stale_stats.succeeded == 0
    assert final_stats.succeeded == 1
    assert first_stats.succeeded == 0
    assert first_port.calls[0][0] == submission_id
    assert second_port.calls[0][0] == submission_id
    assert first_port.calls[0][1] == second_port.calls[0][1]
    assert len(shared_provider._receipts) == 1

    with session_factory() as session:
        events = list(session.scalars(select(OutboxEventRecord)).all())
        deliveries = list(session.scalars(select(ContactDeliveryRecord)).all())
    assert len(events) == 1
    assert events[0].status == OutboxStatus.COMPLETED.value
    succeeded = [
        item for item in deliveries if item.status == ContactDeliveryStatus.SUCCEEDED.value
    ]
    assert len(succeeded) == 1
