from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fps_platform.modules.contact.domain.entities import ContactDelivery, ContactSubmission
from fps_platform.modules.contact.domain.enums import ContactWorkflowStatus
from fps_platform.modules.contact.domain.exceptions import IdempotencyConflictError
from fps_platform.modules.contact.infrastructure.persistence.mapper import (
    to_delivery,
    to_delivery_record,
    to_submission,
    to_submission_record,
)
from fps_platform.modules.contact.infrastructure.persistence.models import (
    ContactDeliveryRecord,
    ContactIdempotencyKeyRecord,
    ContactSubmissionRecord,
)
from fps_platform.shared.domain.clock import Clock
from fps_platform.shared.domain.errors import ConcurrentModificationError, ConflictError


class SqlAlchemyContactSubmissionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, submission: ContactSubmission) -> None:
        self._session.add(to_submission_record(submission))
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise ConflictError("contact submission could not be added") from exc

    def get(self, submission_id: UUID) -> ContactSubmission | None:
        record = self._session.get(ContactSubmissionRecord, submission_id)
        return None if record is None else to_submission(record)

    def list(
        self,
        *,
        limit: int,
        offset: int,
        workflow_status: ContactWorkflowStatus | None = None,
    ) -> Sequence[ContactSubmission]:
        statement = select(ContactSubmissionRecord)
        if workflow_status is not None:
            statement = statement.where(
                ContactSubmissionRecord.workflow_status == workflow_status.value
            )
        statement = (
            statement.order_by(
                ContactSubmissionRecord.received_at.desc(), ContactSubmissionRecord.id.desc()
            )
            .limit(limit)
            .offset(offset)
        )
        return [to_submission(record) for record in self._session.scalars(statement)]

    def count(self, *, workflow_status: ContactWorkflowStatus | None = None) -> int:
        statement = select(func.count()).select_from(ContactSubmissionRecord)
        if workflow_status is not None:
            statement = statement.where(
                ContactSubmissionRecord.workflow_status == workflow_status.value
            )
        return int(self._session.scalar(statement) or 0)

    def save(self, submission: ContactSubmission, *, expected_version: int | None = None) -> None:
        version = expected_version if expected_version is not None else submission.version - 1
        statement = (
            update(ContactSubmissionRecord)
            .where(
                ContactSubmissionRecord.id == submission.id,
                ContactSubmissionRecord.version == version,
            )
            .values(
                workflow_status=submission.workflow_status.value,
                contacted_at=submission.contacted_at,
                closed_at=submission.closed_at,
                archived_at=submission.archived_at,
                close_reason_code=submission.close_reason.value
                if submission.close_reason is not None
                else None,
                updated_at=submission.updated_at,
                version=submission.version,
            )
        )
        result = cast(CursorResult[Any], self._session.execute(statement))
        if result.rowcount != 1:
            raise ConcurrentModificationError("contact version changed")


class SqlAlchemyContactDeliveryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, delivery: ContactDelivery) -> None:
        self._session.add(to_delivery_record(delivery))
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise ConflictError("contact delivery could not be added") from exc

    def get(self, delivery_id: UUID) -> ContactDelivery | None:
        record = self._session.get(ContactDeliveryRecord, delivery_id)
        return None if record is None else to_delivery(record)

    def list_by_submission(self, submission_id: UUID) -> Sequence[ContactDelivery]:
        statement = (
            select(ContactDeliveryRecord)
            .where(ContactDeliveryRecord.submission_id == submission_id)
            .order_by(ContactDeliveryRecord.attempt_number.asc())
        )
        return [to_delivery(record) for record in self._session.scalars(statement)]

    def latest(self, submission_id: UUID) -> ContactDelivery | None:
        statement = (
            select(ContactDeliveryRecord)
            .where(ContactDeliveryRecord.submission_id == submission_id)
            .order_by(ContactDeliveryRecord.attempt_number.desc())
            .limit(1)
        )
        record = self._session.scalars(statement).first()
        return None if record is None else to_delivery(record)

    def next_attempt_number(self, submission_id: UUID) -> int:
        statement = select(func.coalesce(func.max(ContactDeliveryRecord.attempt_number), 0)).where(
            ContactDeliveryRecord.submission_id == submission_id
        )
        return int(self._session.scalar(statement) or 0) + 1

    def save(self, delivery: ContactDelivery) -> None:
        statement = (
            update(ContactDeliveryRecord)
            .where(ContactDeliveryRecord.id == delivery.id)
            .values(
                status=delivery.status.value,
                attempted_at=delivery.attempted_at,
                completed_at=delivery.completed_at,
                provider_reference=delivery.provider_reference,
                failure_code=delivery.failure_code,
            )
        )
        cast(CursorResult[Any], self._session.execute(statement))


class SqlAlchemyContactIdempotencyRepository:
    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def claim(self, *, key_hash: str, fingerprint: str, submission_id: UUID) -> UUID | None:
        insert_statement = postgresql.insert(ContactIdempotencyKeyRecord).values(
            key_hash=key_hash,
            fingerprint=fingerprint,
            submission_id=submission_id,
            created_at=self._clock.now(),
        )
        statement = insert_statement.on_conflict_do_nothing(index_elements=["key_hash"]).returning(
            ContactIdempotencyKeyRecord.key_hash
        )
        inserted = self._session.execute(statement).scalar_one_or_none()
        if inserted is not None:
            return None
        existing = self.get(key_hash=key_hash)
        if existing is None:
            raise ConflictError("contact idempotency key could not be claimed")
        stored_fingerprint, stored_submission_id = existing
        if stored_fingerprint != fingerprint:
            raise IdempotencyConflictError("idempotency key was reused with a different payload")
        return stored_submission_id

    def get(self, *, key_hash: str) -> tuple[str, UUID] | None:
        record = self._session.get(ContactIdempotencyKeyRecord, key_hash)
        if record is None:
            return None
        return record.fingerprint, record.submission_id
