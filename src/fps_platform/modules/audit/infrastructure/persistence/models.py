from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from fps_platform.shared.infrastructure.persistence.base import Base


class AuditEventRecord(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    source: Mapped[str] = mapped_column(String(32), nullable=False)

    __table_args__ = (
        CheckConstraint("length(actor_type) > 0", name="actor_type_non_empty"),
        CheckConstraint("length(action) > 0", name="action_non_empty"),
        CheckConstraint("length(resource_type) > 0", name="resource_type_non_empty"),
        CheckConstraint("length(correlation_id) > 0", name="correlation_id_non_empty"),
        Index("ix_audit_events_occurred_at", "occurred_at"),
        Index(
            "ix_audit_events_resource_type_resource_id_occurred_at",
            "resource_type",
            "resource_id",
            "occurred_at",
        ),
        Index(
            "ix_audit_events_actor_type_actor_id_occurred_at",
            "actor_type",
            "actor_id",
            "occurred_at",
        ),
        Index("ix_audit_events_correlation_id", "correlation_id"),
    )
