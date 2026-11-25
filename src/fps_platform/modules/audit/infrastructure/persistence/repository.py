from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fps_platform.modules.audit.domain.audit_event import AuditEvent
from fps_platform.modules.audit.domain.ports import AuditEventRepository
from fps_platform.modules.audit.infrastructure.persistence.mapper import to_domain, to_record
from fps_platform.modules.audit.infrastructure.persistence.models import AuditEventRecord
from fps_platform.shared.domain.errors import ConflictError


class SqlAlchemyAuditEventRepository(AuditEventRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def append(self, event: AuditEvent) -> None:
        self._session.add(to_record(event))
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise ConflictError("Audit event could not be appended") from exc

    def get(self, event_id: UUID) -> AuditEvent | None:
        record = self._session.get(AuditEventRecord, event_id)
        return None if record is None else to_domain(record)

    def list_by_resource(
        self, *, resource_type: str, resource_id: UUID, limit: int = 100
    ) -> list[AuditEvent]:
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")
        statement = (
            select(AuditEventRecord)
            .where(
                AuditEventRecord.resource_type == resource_type,
                AuditEventRecord.resource_id == resource_id,
            )
            .order_by(AuditEventRecord.occurred_at.desc(), AuditEventRecord.id.desc())
            .limit(limit)
        )
        return [to_domain(record) for record in self._session.scalars(statement)]
