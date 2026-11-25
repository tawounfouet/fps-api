from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Event

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from fps_platform.modules.contact.domain.enums import ContactDeliveryStatus
from fps_platform.modules.contact.infrastructure.email import MockEmailDeliveryPort
from fps_platform.modules.contact.infrastructure.persistence.models import (
    ContactDeliveryRecord,
)
from fps_platform.modules.outbox.domain.enums import OutboxStatus
from fps_platform.modules.outbox.infrastructure.persistence.models import OutboxEventRecord
from fps_platform.shared.domain.clock import FakeClock
from tests.fixtures.contact import BlockingEmailPort, build_worker, submit_contact
from tests.integration.conftest import MakeUow

pytestmark = pytest.mark.integration

MOMENT = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)


def test_two_workers_never_deliver_the_same_event_twice(
    make_uow: MakeUow, session_factory: sessionmaker[Session]
) -> None:
    clock = FakeClock(MOMENT)
    submission_id = submit_contact(make_uow, clock=clock)
    entered = Event()
    release = Event()
    blocking_port = BlockingEmailPort(entered, release)
    first = build_worker(
        make_uow,
        blocking_port,
        clock,
        worker_id="worker-a",
        retry_delays_seconds=(0,),
    )
    second = build_worker(
        make_uow,
        MockEmailDeliveryPort(),
        clock,
        worker_id="worker-b",
        retry_delays_seconds=(0,),
    )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first_result = pool.submit(first.run_once, limit=20)
        assert entered.wait(10)
        second_result = pool.submit(second.run_once, limit=20)
        release.set()
        first_stats = first_result.result(timeout=20)
        second_stats = second_result.result(timeout=20)

    assert first_stats.succeeded == 1
    assert second_stats.claimed == 0
    assert second_stats.succeeded == 0
    assert [call[0] for call in blocking_port.calls] == [submission_id]

    with session_factory() as session:
        deliveries = list(session.scalars(select(ContactDeliveryRecord)).all())
        events = list(session.scalars(select(OutboxEventRecord)).all())

    assert len(deliveries) == 1
    assert deliveries[0].status == ContactDeliveryStatus.SUCCEEDED.value
    assert len(events) == 1
    assert events[0].status == OutboxStatus.COMPLETED.value
