from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.orm import Session

from fps_platform.modules.identity.domain.ports import SuperAdminGuard

SUPER_ADMIN_ADVISORY_LOCK_KEY = 731982641


class PostgresSuperAdminGuard(SuperAdminGuard):
    def __init__(self, session: Session) -> None:
        self._session = session

    @contextmanager
    def lock(self) -> Iterator[None]:
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": SUPER_ADMIN_ADVISORY_LOCK_KEY},
        )
        yield
