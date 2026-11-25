from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from fps_platform.modules.outbox.domain.enums import OutboxStatus
from fps_platform.modules.outbox.infrastructure.persistence.models import OutboxEventRecord
from fps_platform.shared.domain.clock import FakeClock
from tests.fixtures.contact import submit_contact
from tests.integration.conftest import MakeUow

pytestmark = pytest.mark.integration

MOMENT = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)


def test_stale_lease_token_cannot_finalize_event(
    make_uow: MakeUow, session_factory: sessionmaker[Session]
) -> None:
    clock = FakeClock(MOMENT)
    submit_contact(make_uow, clock=clock)
    with session_factory() as session:
        event_id = session.scalar(select(OutboxEventRecord.id))
    assert event_id is not None

    token = uuid4()
    with make_uow() as uow:
        claimed = uow.outbox_events.claim(
            event_id=event_id,
            lease_token=token,
            leased_until=MOMENT + timedelta(seconds=60),
            locked_by="owner",
            now=MOMENT,
        )
        uow.commit()
    assert claimed is True

    with make_uow() as uow:
        stale = uow.outbox_events.complete(
            event_id=event_id,
            lease_token=uuid4(),
            completed_at=MOMENT + timedelta(seconds=30),
        )
        uow.commit()
    assert stale is False

    with session_factory() as session:
        event = session.get(OutboxEventRecord, event_id)
    assert event is not None
    assert event.status == OutboxStatus.LEASED.value
    assert event.lease_token == token
