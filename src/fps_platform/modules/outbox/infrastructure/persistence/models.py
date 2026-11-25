from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from fps_platform.shared.infrastructure.persistence.base import Base


class OutboxEventRecord(Base):
    __tablename__ = "outbox_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    operation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    dedup_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    payload_version: Mapped[int] = mapped_column(nullable=False)
    payload_: Mapped[dict[str, object]] = mapped_column(
        "payload", JSONB, nullable=False, default=dict
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempt_count: Mapped[int] = mapped_column(nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(nullable=False)
    lease_token: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    leased_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        CheckConstraint("payload_version > 0", name="payload_version_positive"),
        CheckConstraint("attempt_count >= 0", name="attempt_count_non_negative"),
        CheckConstraint("max_attempts > 0", name="max_attempts_positive"),
        CheckConstraint("attempt_count <= max_attempts", name="attempt_count_bounded"),
        CheckConstraint(
            "status <> 'COMPLETED' OR completed_at IS NOT NULL",
            name="completed_at_required",
        ),
        CheckConstraint(
            "status <> 'LEASED' OR (lease_token IS NOT NULL AND leased_until IS NOT NULL)",
            name="lease_fields_required",
        ),
        Index(
            "ix_outbox_events_status_available_at_created_at_id",
            "status",
            "available_at",
            "created_at",
            "id",
        ),
        Index("ix_outbox_events_leased_until", "leased_until"),
        Index("ix_outbox_events_aggregate_type_aggregate_id", "aggregate_type", "aggregate_id"),
    )
