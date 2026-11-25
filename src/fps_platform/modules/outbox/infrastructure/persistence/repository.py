from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fps_platform.modules.outbox.domain.enums import OutboxStatus
from fps_platform.modules.outbox.domain.outbox_event import OutboxEvent
from fps_platform.modules.outbox.domain.ports import OutboxEventRepository
from fps_platform.modules.outbox.infrastructure.persistence.mapper import to_domain, to_record
from fps_platform.modules.outbox.infrastructure.persistence.models import OutboxEventRecord
from fps_platform.shared.domain.errors import ConflictError


class SqlAlchemyOutboxEventRepository(OutboxEventRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def append(self, event: OutboxEvent) -> None:
        self._session.add(to_record(event))
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise ConflictError("Outbox event could not be appended") from exc

    def get(self, event_id: UUID) -> OutboxEvent | None:
        record = self._session.get(OutboxEventRecord, event_id)
        return None if record is None else to_domain(record)

    def list_available(self, *, status: OutboxStatus, limit: int = 20) -> list[OutboxEvent]:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        statement = (
            select(OutboxEventRecord)
            .where(OutboxEventRecord.status == status.value)
            .order_by(
                OutboxEventRecord.available_at.asc(),
                OutboxEventRecord.created_at.asc(),
                OutboxEventRecord.id.asc(),
            )
            .limit(limit)
        )
        return [to_domain(record) for record in self._session.scalars(statement)]
