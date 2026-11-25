from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session, sessionmaker

from fps_platform.modules.audit.domain.enums import AuditAction
from fps_platform.modules.audit.infrastructure.persistence.models import AuditEventRecord
from fps_platform.modules.audit.infrastructure.persistence.repository import (
    SqlAlchemyAuditEventRepository,
)
from fps_platform.shared.domain.actor import ActorType
from fps_platform.shared.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from tests.fixtures.persistence_probe import (
    PersistenceProbe,
    PersistenceProbeRepository,
    ProbeParent,
)

MakeUow = Callable[..., SqlAlchemyUnitOfWork]
pytestmark = pytest.mark.integration


def test_audit_mapping_roundtrip_is_detached(
    make_uow: MakeUow, session_factory: sessionmaker[Session]
) -> None:
    parent = ProbeParent(id=uuid4(), code=f"parent-{uuid4().hex[:12]}")
    probe = PersistenceProbe(
        id=uuid4(),
        parent_id=parent.id,
        code=f"probe-{uuid4().hex[:12]}",
        version=1,
        metadata={"stage": "m2"},
        created_at=datetime.now(UTC),
    )
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
        audit_id = event.id
        uow.commit()
    with session_factory() as session:
        loaded = SqlAlchemyAuditEventRepository(session).get(audit_id)
        assert loaded is not None
        assert loaded.id == audit_id
        assert loaded.action is AuditAction.PERSISTENCE_PROBE_CREATED
        assert loaded.actor_type is ActorType.SYSTEM
        assert isinstance(loaded, AuditEventRecord) is False
        assert dict(loaded.metadata) == {"probe_code": probe.code}


def test_probe_mapping_roundtrip_preserves_jsonb(
    make_uow: MakeUow, session_factory: sessionmaker[Session]
) -> None:
    parent = ProbeParent(id=uuid4(), code=f"parent-{uuid4().hex[:12]}")
    probe = PersistenceProbe(
        id=uuid4(),
        parent_id=parent.id,
        code=f"probe-{uuid4().hex[:12]}",
        version=1,
        metadata={"stage": "m2", "attempt": 3, "enabled": True},
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
        assert dict(loaded.metadata) == dict(probe.metadata)
        assert loaded.code == probe.code
