from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from fps_platform.shared.infrastructure.persistence.base import Base


class ContactSubmissionRecord(Base):
    __tablename__ = "contact_submissions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    organisation: Mapped[str | None] = mapped_column(String(128), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(128), nullable=True)
    subject: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text(), nullable=False)
    locale: Mapped[str] = mapped_column(String(8), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    workflow_status: Mapped[str] = mapped_column(String(32), nullable=False)
    rgpd_consent: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    close_reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("length(first_name) > 0", name="contact_submissions_first_name_non_empty"),
        CheckConstraint("length(last_name) > 0", name="contact_submissions_last_name_non_empty"),
        CheckConstraint("length(email) > 0", name="contact_submissions_email_non_empty"),
        CheckConstraint("length(subject) > 0", name="contact_submissions_subject_non_empty"),
        CheckConstraint("length(message) > 0", name="contact_submissions_message_non_empty"),
        CheckConstraint("version > 0", name="contact_submissions_version_positive"),
        CheckConstraint(
            "workflow_status IN ('RECEIVED', 'CONTACTED', 'CLOSED', 'ARCHIVED')",
            name="contact_submissions_workflow_status_valid",
        ),
        Index(
            "ix_contact_submissions_workflow_status_received_at_id",
            "workflow_status",
            "received_at",
            "id",
        ),
    )


class ContactDeliveryRecord(Base):
    __tablename__ = "contact_deliveries"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    submission_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("contact_submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(String(16), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        CheckConstraint("attempt_number > 0", name="contact_deliveries_attempt_positive"),
        CheckConstraint("length(provider) > 0", name="contact_deliveries_provider_non_empty"),
        CheckConstraint(
            "status IN ('PENDING', 'IN_PROGRESS', 'SUCCEEDED', 'FAILED')",
            name="contact_deliveries_status_valid",
        ),
        Index(
            "uq_contact_deliveries_submission_channel_attempt",
            "submission_id",
            "channel",
            "attempt_number",
            unique=True,
        ),
        Index("ix_contact_deliveries_status_requested_at", "status", "requested_at"),
    )


class ContactIdempotencyKeyRecord(Base):
    __tablename__ = "contact_idempotency_keys"

    key_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    submission_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint("length(key_hash) = 64", name="contact_idempotency_keys_hash_length"),
        CheckConstraint(
            "length(fingerprint) = 64", name="contact_idempotency_keys_fingerprint_length"
        ),
    )
