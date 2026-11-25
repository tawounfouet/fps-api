from __future__ import annotations

from typing import cast

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from fps_platform.modules.contact.application import handlers
from fps_platform.modules.contact.application.ports import ContactUnitOfWork
from tests.fixtures.contact import CONTACT_TABLES, INJECTION_TARGETS, new_command
from tests.integration.conftest import MakeUow

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("target", sorted(INJECTION_TARGETS))
def test_failure_at_each_contact_write_boundary_rolls_back_everything(
    make_uow: MakeUow,
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
    target: str,
) -> None:
    owner, method = INJECTION_TARGETS[target]
    message = f"injected failure at {target}"

    def fail(*args: object, **kwargs: object) -> None:
        raise RuntimeError(message)

    monkeypatch.setattr(owner, method, fail)

    with pytest.raises(RuntimeError, match=message), make_uow() as uow:
        handlers.submit_contact(cast(ContactUnitOfWork, uow), new_command())
        uow.commit()

    with session_factory() as session:
        for model in CONTACT_TABLES:
            assert session.scalar(select(func.count()).select_from(model)) == 0
