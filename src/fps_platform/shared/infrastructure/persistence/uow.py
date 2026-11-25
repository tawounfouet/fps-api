from __future__ import annotations

from dataclasses import dataclass, field
from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session, sessionmaker

from fps_platform.modules.audit.application.recorder import AuditRecorder
from fps_platform.modules.audit.infrastructure.persistence.repository import (
    SqlAlchemyAuditEventRepository,
)
from fps_platform.modules.outbox.application.recorder import OutboxRecorder
from fps_platform.modules.outbox.infrastructure.persistence.repository import (
    SqlAlchemyOutboxEventRepository,
)
from fps_platform.shared.application.uow import UnitOfWork
from fps_platform.shared.domain.actor import ActorContext
from fps_platform.shared.domain.clock import Clock
from fps_platform.shared.domain.identifiers import IdGenerator


@dataclass(slots=True)
class SqlAlchemyUnitOfWork(UnitOfWork):
    session_factory: sessionmaker[Session]
    clock: Clock
    id_generator: IdGenerator
    actor_context: ActorContext
    _session: Session | None = field(default=None, init=False)
    _committed: bool = field(default=False, init=False)

    @property
    def session(self) -> Session:
        if self._session is None:
            raise RuntimeError("UnitOfWork is not active")
        return self._session

    @property
    def audit_events(self) -> SqlAlchemyAuditEventRepository:
        return SqlAlchemyAuditEventRepository(self.session)

    @property
    def outbox_events(self) -> SqlAlchemyOutboxEventRepository:
        return SqlAlchemyOutboxEventRepository(self.session)

    @property
    def audit_recorder(self) -> AuditRecorder:
        return AuditRecorder(
            repository=self.audit_events,
            clock=self.clock,
            id_generator=self.id_generator,
            actor_context=self.actor_context,
        )

    @property
    def outbox_recorder(self) -> OutboxRecorder:
        return OutboxRecorder(
            repository=self.outbox_events,
            clock=self.clock,
            id_generator=self.id_generator,
        )

    def __enter__(self) -> Self:
        if self._session is not None:
            raise RuntimeError("UnitOfWork is already active")
        self._session = self.session_factory()
        self._committed = False
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        session = self._session
        if session is None:
            return
        try:
            if exc_type is not None or not self._committed:
                session.rollback()
        finally:
            session.close()
            self._session = None
            self._committed = False

    def commit(self) -> None:
        self.session.commit()
        self._committed = True

    def rollback(self) -> None:
        self.session.rollback()
        self._committed = False
