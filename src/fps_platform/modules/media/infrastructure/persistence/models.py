from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from fps_platform.shared.infrastructure.persistence.base import Base


class MediaAssetRecord(Base):
    __tablename__ = "media_assets"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger(), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    height: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    checksum_algorithm: Mapped[str | None] = mapped_column(String(16), nullable=True)
    checksum_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    alt_texts: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    captions: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    attribution: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    uploaded_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer(), nullable=False)
    intent_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claim_owner: Mapped[str | None] = mapped_column(String(128), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detected_mime: Mapped[str | None] = mapped_column(String(64), nullable=True)
    promotion_proof_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    promoted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("storage_key", name="uq_media_assets_storage_key"),
        CheckConstraint("length(storage_key) > 0", name="media_assets_storage_key_non_empty"),
        CheckConstraint("length(original_filename) > 0", name="media_assets_filename_non_empty"),
        CheckConstraint("length(mime_type) > 0", name="media_assets_mime_type_non_empty"),
        CheckConstraint("byte_size >= 0", name="media_assets_byte_size_non_negative"),
        CheckConstraint(
            "attempt_count >= 0 AND attempt_count <= 3",
            name="media_assets_attempt_count_bounded",
        ),
        CheckConstraint("width IS NULL OR width > 0", name="media_assets_width_positive"),
        CheckConstraint("height IS NULL OR height > 0", name="media_assets_height_positive"),
        CheckConstraint("version > 0", name="media_assets_version_positive"),
        CheckConstraint(
            "status IN ('UPLOADING', 'PROCESSING', 'READY', 'FAILED', 'ARCHIVED')",
            name="media_assets_status_valid",
        ),
        CheckConstraint(
            "status <> 'READY' OR ("
            "byte_size > 0 AND width IS NOT NULL AND height IS NOT NULL "
            "AND checksum_algorithm IS NOT NULL AND checksum_digest IS NOT NULL "
            "AND ready_at IS NOT NULL)",
            name="media_assets_ready_requirements",
        ),
        Index("ix_media_assets_status_created_at_id", "status", "created_at", "id"),
        Index("ix_media_assets_checksum_digest", "checksum_digest"),
    )
