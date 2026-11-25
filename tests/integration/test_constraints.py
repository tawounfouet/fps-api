from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from fps_platform.modules.audit.domain.enums import AuditAction
from fps_platform.modules.audit.infrastructure.persistence.repository import (
    SqlAlchemyAuditEventRepository,
)
from fps_platform.modules.outbox.domain.enums import OutboxEventType
from fps_platform.shared.domain.errors import ConflictError
from fps_platform.shared.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from tests.fixtures.persistence_probe import (
    PersistenceProbe,
    PersistenceProbeRecord,
    PersistenceProbeRepository,
    ProbeParent,
    ProbeParentRecord,
)

MakeUow = Callable[..., SqlAlchemyUnitOfWork]
pytestmark = pytest.mark.integration


def test_unique_constraint_rejects_duplicate_code(make_uow: MakeUow) -> None:
    parent = ProbeParent(id=uuid4(), code=f"parent-{uuid4().hex[:12]}")
    with pytest.raises(ConflictError), make_uow() as uow:
        repository = PersistenceProbeRepository(uow.session)
        repository.add_parent(parent)
        repository.add_parent(ProbeParent(id=uuid4(), code=parent.code))
        uow.commit()


def test_foreign_key_rejects_missing_parent(make_uow: MakeUow) -> None:
    probe = PersistenceProbe(
        id=uuid4(),
        parent_id=uuid4(),
        code=f"probe-{uuid4().hex[:12]}",
        version=1,
        metadata={"stage": "m2"},
        created_at=datetime.now(UTC),
    )
    with pytest.raises(ConflictError), make_uow() as uow:
        PersistenceProbeRepository(uow.session).add(probe)
        uow.commit()


def test_check_constraint_rejects_non_positive_version(
    session_factory: sessionmaker[Session],
) -> None:
    parent_id = uuid4()
    with session_factory() as session:
        session.add(ProbeParentRecord(id=parent_id, code=f"parent-{uuid4().hex[:12]}"))
        session.flush()
        with pytest.raises(IntegrityError):
            session.execute(
                insert(PersistenceProbeRecord).values(
                    id=uuid4(),
                    parent_id=parent_id,
                    code=f"probe-{uuid4().hex[:12]}",
                    version=0,
                    metadata={},
                    created_at=datetime.now(UTC),
                )
            )


def test_jsonb_roundtrip_preserves_typed_values(
    make_uow: MakeUow, session_factory: sessionmaker[Session]
) -> None:
    parent = ProbeParent(id=uuid4(), code=f"parent-{uuid4().hex[:12]}")
    probe = PersistenceProbe(
        id=uuid4(),
        parent_id=parent.id,
        code=f"probe-{uuid4().hex[:12]}",
        version=1,
        metadata={"stage": "m2", "attempt": 7, "enabled": False},
        created_at=datetime.now(UTC),
    )
    with make_uow() as uow:
        repository = PersistenceProbeRepository(uow.session)
        repository.add_parent(parent)
        repository.add(probe)
        uow.commit()
    with session_factory() as session:
        loaded = PersistenceProbeRepository(session).get(probe.id)
        assert loaded is not None
        assert dict(loaded.metadata) == {"stage": "m2", "attempt": 7, "enabled": False}


def test_outbox_dedup_key_is_unique(make_uow: MakeUow) -> None:
    dedup_key = f"dedup-{uuid4()}"
    with pytest.raises(ConflictError), make_uow() as uow:
        recorder = uow.outbox_recorder
        payload = {
            "contact_submission_id": str(uuid4()),
            "delivery_intent_id": str(uuid4()),
            "template_code": "contact-v1",
            "recipient_group_code": "admin",
        }
        for index in range(2):
            recorder.record(
                event_type=OutboxEventType.CONTACT_DELIVERY_REQUESTED,
                aggregate_type="Probe",
                aggregate_id=uuid4(),
                operation_id=f"operation-{index}",
                dedup_key=dedup_key,
                payload=payload,
            )
        uow.commit()


def test_audit_update_is_not_exposed_through_repository(
    make_uow: MakeUow, session_factory: sessionmaker[Session]
) -> None:
    with make_uow() as uow:
        uow.audit_recorder.record(
            action=AuditAction.PERSISTENCE_PROBE_CREATED,
            resource_type="Probe",
            resource_id=uuid4(),
            metadata={"probe_code": f"probe-{uuid4().hex[:12]}"},
        )
        uow.commit()
    with session_factory() as session:
        repository = SqlAlchemyAuditEventRepository(session)
        assert not hasattr(repository, "update")
        assert not hasattr(repository, "delete")
