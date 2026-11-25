from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session, sessionmaker

from fps_platform.shared.domain.errors import ConcurrentModificationError
from fps_platform.shared.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from tests.fixtures.persistence_probe import PersistenceProbeRepository
from tests.integration.test_transactions import new_probe

MakeUow = Callable[..., SqlAlchemyUnitOfWork]
pytestmark = pytest.mark.integration


def test_concurrent_updates_produce_one_conflict(
    make_uow: MakeUow, session_factory: sessionmaker[Session]
) -> None:
    parent, probe = new_probe()
    with make_uow() as setup:
        repository = PersistenceProbeRepository(setup.session)
        repository.add_parent(parent)
        repository.add(probe)
        setup.commit()

    barrier = Barrier(2)

    def update(code: str) -> str:
        with make_uow() as uow:
            repository = PersistenceProbeRepository(uow.session)
            barrier.wait(timeout=10)
            try:
                repository.update_code(probe_id=probe.id, expected_version=1, code=code)
                uow.commit()
                return "success"
            except ConcurrentModificationError:
                uow.rollback()
                return "conflict"

    first_code = f"first-{uuid4().hex[:8]}"
    second_code = f"second-{uuid4().hex[:8]}"
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(update, (first_code, second_code)))

    assert sorted(outcomes) == ["conflict", "success"]
    with session_factory() as session:
        loaded = PersistenceProbeRepository(session).get(probe.id)
        assert loaded is not None
        assert loaded.version == 2
        assert loaded.code in {first_code, second_code}
