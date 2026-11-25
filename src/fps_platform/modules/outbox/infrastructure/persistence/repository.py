from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.engine import CursorResult
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
        self._validate_limit(limit)
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

    def list_due(self, *, now: datetime, limit: int = 20) -> list[OutboxEvent]:
        self._validate_limit(limit)
        statement = (
            select(OutboxEventRecord)
            .where(
                OutboxEventRecord.status.in_(
                    [OutboxStatus.PENDING.value, OutboxStatus.RETRY_WAIT.value]
                ),
                OutboxEventRecord.available_at <= now,
            )
            .order_by(
                OutboxEventRecord.available_at.asc(),
                OutboxEventRecord.created_at.asc(),
                OutboxEventRecord.id.asc(),
            )
            .limit(limit)
        )
        return [to_domain(record) for record in self._session.scalars(statement)]

    def claim(
        self,
        *,
        event_id: UUID,
        lease_token: UUID,
        leased_until: datetime,
        locked_by: str,
        now: datetime,
    ) -> bool:
        statement = (
            update(OutboxEventRecord)
            .where(
                OutboxEventRecord.id == event_id,
                OutboxEventRecord.status.in_(
                    [OutboxStatus.PENDING.value, OutboxStatus.RETRY_WAIT.value]
                ),
                OutboxEventRecord.available_at <= now,
                OutboxEventRecord.attempt_count < OutboxEventRecord.max_attempts,
            )
            .values(
                status=OutboxStatus.LEASED.value,
                attempt_count=OutboxEventRecord.attempt_count + 1,
                lease_token=lease_token,
                leased_until=leased_until,
                locked_by=locked_by,
            )
        )
        result = cast(CursorResult[Any], self._session.execute(statement))
        return result.rowcount == 1

    def complete(self, *, event_id: UUID, completed_at: datetime) -> None:
        statement = (
            update(OutboxEventRecord)
            .where(
                OutboxEventRecord.id == event_id,
                OutboxEventRecord.status == OutboxStatus.LEASED.value,
            )
            .values(
                status=OutboxStatus.COMPLETED.value,
                completed_at=completed_at,
                lease_token=None,
                leased_until=None,
                locked_by=None,
            )
        )
        cast(CursorResult[Any], self._session.execute(statement))

    def mark_retry_wait(
        self,
        *,
        event_id: UUID,
        available_at: datetime,
        last_error_code: str,
    ) -> None:
        statement = (
            update(OutboxEventRecord)
            .where(
                OutboxEventRecord.id == event_id,
                OutboxEventRecord.status == OutboxStatus.LEASED.value,
            )
            .values(
                status=OutboxStatus.RETRY_WAIT.value,
                available_at=available_at,
                last_error_code=last_error_code,
                lease_token=None,
                leased_until=None,
                locked_by=None,
            )
        )
        cast(CursorResult[Any], self._session.execute(statement))

    def mark_dead(self, *, event_id: UUID, last_error_code: str) -> None:
        statement = (
            update(OutboxEventRecord)
            .where(
                OutboxEventRecord.id == event_id,
                OutboxEventRecord.status == OutboxStatus.LEASED.value,
            )
            .values(
                status=OutboxStatus.DEAD.value,
                last_error_code=last_error_code,
                lease_token=None,
                leased_until=None,
                locked_by=None,
            )
        )
        cast(CursorResult[Any], self._session.execute(statement))

    def release_expired(self, *, now: datetime, limit: int = 20) -> int:
        self._validate_limit(limit)
        statement = (
            update(OutboxEventRecord)
            .where(
                and_(
                    OutboxEventRecord.status == OutboxStatus.LEASED.value,
                    OutboxEventRecord.leased_until < now,
                )
            )
            .values(
                status=OutboxStatus.PENDING.value,
                available_at=now,
                lease_token=None,
                leased_until=None,
                locked_by=None,
            )
        )
        result = cast(CursorResult[Any], self._session.execute(statement))
        return int(result.rowcount or 0)

    def _validate_limit(self, limit: int) -> None:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
