from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session, sessionmaker

from fps_platform.shared.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from tests.fixtures.persistence_probe import (
    PersistenceProbe,
    PersistenceProbeRepository,
    ProbeParent,
)

MakeUow = Callable[..., SqlAlchemyUnitOfWork]
pytestmark = pytest.mark.integration


def new_probe() -> tuple[ProbeParent, PersistenceProbe]:
    parent = ProbeParent(id=uuid4(), code=f"parent-{uuid4().hex[:12]}")
    probe = PersistenceProbe(
        id=uuid4(),
        parent_id=parent.id,
        code=f"probe-{uuid4().hex[:12]}",
        version=1,
        metadata={"stage": "m2", "attempt": 1, "enabled": True},
        created_at=datetime.now(UTC),
    )
    return parent, probe


def test_explicit_commit_persists_probe(
    make_uow: MakeUow, session_factory: sessionmaker[Session]
) -> None:
    parent, probe = new_probe()
    with make_uow() as uow:
        repository = PersistenceProbeRepository(uow.session)
        repository.add_parent(parent)
        repository.add(probe)
        uow.commit()
    with session_factory() as session:
        loaded = PersistenceProbeRepository(session).get(probe.id)
        assert loaded is not None
        assert loaded.code == probe.code
        assert loaded.version == 1


def test_exception_rolls_back_every_change(
    make_uow: MakeUow, session_factory: sessionmaker[Session]
) -> None:
    parent, probe = new_probe()
    with pytest.raises(RuntimeError, match="failure before commit"), make_uow() as uow:
        repository = PersistenceProbeRepository(uow.session)
        repository.add_parent(parent)
        repository.add(probe)
        raise RuntimeError("failure before commit")
    with session_factory() as session:
        assert PersistenceProbeRepository(session).get(probe.id) is None


def test_exit_without_commit_rolls_back(
    make_uow: MakeUow, session_factory: sessionmaker[Session]
) -> None:
    parent, probe = new_probe()
    with make_uow() as uow:
        repository = PersistenceProbeRepository(uow.session)
        repository.add_parent(parent)
        repository.add(probe)
    with session_factory() as session:
        assert PersistenceProbeRepository(session).get(probe.id) is None
