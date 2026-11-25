from __future__ import annotations

from collections.abc import Callable
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session, sessionmaker

from fps_platform.modules.audit.domain.enums import AuditAction
from fps_platform.modules.audit.infrastructure.persistence.repository import (
    SqlAlchemyAuditEventRepository,
)
from fps_platform.modules.outbox.domain.enums import OutboxEventType, OutboxStatus
from fps_platform.modules.outbox.infrastructure.persistence.repository import (
    SqlAlchemyOutboxEventRepository,
)
from fps_platform.shared.domain.errors import ConflictError
from fps_platform.shared.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from tests.fixtures.persistence_probe import PersistenceProbeRepository
from tests.integration.test_transactions import new_probe

MakeUow = Callable[..., SqlAlchemyUnitOfWork]
pytestmark = pytest.mark.integration


def test_mutation_and_audit_commit_together(
    make_uow: MakeUow, session_factory: sessionmaker[Session]
) -> None:
    parent, probe = new_probe()
    with make_uow() as uow:
        repository = PersistenceProbeRepository(uow.session)
        repository.add_parent(parent)
        repository.add(probe)
        event = uow.audit_recorder.record(
            action=AuditAction.PERSISTENCE_PROBE_CREATED,
            resource_type="PersistenceProbe",
            resource_id=probe.id,
            metadata={"probe_code": probe.code},
        )
        uow.commit()
    with session_factory() as session:
        assert PersistenceProbeRepository(session).get(probe.id) is not None
        stored = SqlAlchemyAuditEventRepository(session).get(event.id)
        assert stored is not None
        assert stored.action is AuditAction.PERSISTENCE_PROBE_CREATED
        assert dict(stored.metadata) == {"probe_code": probe.code}


def test_audit_is_absent_after_exception(
    make_uow: MakeUow, session_factory: sessionmaker[Session]
) -> None:
    parent, probe = new_probe()
    event_id: UUID | None = None
    with pytest.raises(RuntimeError), make_uow() as uow:
        repository = PersistenceProbeRepository(uow.session)
        repository.add_parent(parent)
        repository.add(probe)
        event = uow.audit_recorder.record(
            action=AuditAction.PERSISTENCE_PROBE_CREATED,
            resource_type="PersistenceProbe",
            resource_id=probe.id,
            metadata={"probe_code": probe.code},
        )
        event_id = event.id
        raise RuntimeError("failure before commit")
    with session_factory() as session:
        assert PersistenceProbeRepository(session).get(probe.id) is None
        if event_id is not None:
            assert SqlAlchemyAuditEventRepository(session).get(event_id) is None


def test_mutation_audit_and_outbox_commit_together(
    make_uow: MakeUow, session_factory: sessionmaker[Session]
) -> None:
    parent, probe = new_probe()
    with make_uow() as uow:
        repository = PersistenceProbeRepository(uow.session)
        repository.add_parent(parent)
        repository.add(probe)
        audit_event = uow.audit_recorder.record(
            action=AuditAction.CONTACT_DELIVERY_REQUESTED,
            resource_type="PersistenceProbe",
            resource_id=probe.id,
            metadata={"template_code": "contact-v1", "recipient_group_code": "admin"},
        )
        outbox_event = uow.outbox_recorder.record(
            event_type=OutboxEventType.CONTACT_DELIVERY_REQUESTED,
            aggregate_type="PersistenceProbe",
            aggregate_id=probe.id,
            operation_id=f"operation-{uuid4()}",
            dedup_key=f"dedup-{uuid4()}",
            payload={
                "contact_submission_id": str(uuid4()),
                "delivery_intent_id": str(uuid4()),
                "template_code": "contact-v1",
                "recipient_group_code": "admin",
            },
        )
        uow.commit()
    with session_factory() as session:
        assert SqlAlchemyAuditEventRepository(session).get(audit_event.id) is not None
        assert SqlAlchemyOutboxEventRepository(session).get(outbox_event.id) is not None


def test_outbox_conflict_rolls_back_all_writes(
    make_uow: MakeUow, session_factory: sessionmaker[Session]
) -> None:
    parent, probe = new_probe()
    dedup_key = f"dedup-{uuid4()}"
    with pytest.raises(ConflictError), make_uow() as uow:
        repository = PersistenceProbeRepository(uow.session)
        repository.add_parent(parent)
        repository.add(probe)
        uow.audit_recorder.record(
            action=AuditAction.PERSISTENCE_PROBE_CREATED,
            resource_type="PersistenceProbe",
            resource_id=probe.id,
            metadata={"probe_code": probe.code},
        )
        payload = {
            "contact_submission_id": str(uuid4()),
            "delivery_intent_id": str(uuid4()),
            "template_code": "contact-v1",
            "recipient_group_code": "admin",
        }
        for index in range(2):
            uow.outbox_recorder.record(
                event_type=OutboxEventType.CONTACT_DELIVERY_REQUESTED,
                aggregate_type="PersistenceProbe",
                aggregate_id=probe.id,
                operation_id=f"operation-{index}-{uuid4()}",
                dedup_key=dedup_key,
                payload=payload,
            )
        uow.commit()
    with session_factory() as session:
        assert PersistenceProbeRepository(session).get(probe.id) is None
        assert (
            SqlAlchemyAuditEventRepository(session).list_by_resource(
                resource_type="PersistenceProbe", resource_id=probe.id
            )
            == []
        )
        assert (
            SqlAlchemyOutboxEventRepository(session).list_available(status=OutboxStatus.PENDING)
            == []
        )


def test_audit_metadata_rejects_personal_data(make_uow: MakeUow) -> None:
    with make_uow() as uow, pytest.raises(ValueError):
        uow.audit_recorder.record(
            action=AuditAction.PERSISTENCE_PROBE_CREATED,
            resource_type="PersistenceProbe",
            resource_id=uuid4(),
            metadata={"email": "test@example.invalid"},
        )
