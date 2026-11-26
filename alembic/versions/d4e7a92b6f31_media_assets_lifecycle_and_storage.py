"""media assets lifecycle and storage identity

Revision ID: d4e7a92b6f31
Revises: c8cfc1256c53
Create Date: 2026-11-25 18:45:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d4e7a92b6f31"
down_revision: str | None = "c8cfc1256c53"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("checksum_algorithm", sa.String(length=16), nullable=True),
        sa.Column("checksum_digest", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column(
            "alt_texts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "captions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "attribution",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("uploaded_by_user_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "byte_size >= 0",
            name=op.f("ck_media_assets_media_assets_byte_size_non_negative"),
        ),
        sa.CheckConstraint(
            "height IS NULL OR height > 0",
            name=op.f("ck_media_assets_media_assets_height_positive"),
        ),
        sa.CheckConstraint(
            "length(mime_type) > 0",
            name=op.f("ck_media_assets_media_assets_mime_type_non_empty"),
        ),
        sa.CheckConstraint(
            "length(original_filename) > 0",
            name=op.f("ck_media_assets_media_assets_filename_non_empty"),
        ),
        sa.CheckConstraint(
            "length(storage_key) > 0",
            name=op.f("ck_media_assets_media_assets_storage_key_non_empty"),
        ),
        sa.CheckConstraint(
            "status <> 'READY' OR ("
            "byte_size > 0 AND width IS NOT NULL AND height IS NOT NULL "
            "AND checksum_algorithm IS NOT NULL AND checksum_digest IS NOT NULL "
            "AND ready_at IS NOT NULL)",
            name=op.f("ck_media_assets_media_assets_ready_requirements"),
        ),
        sa.CheckConstraint(
            "status IN ('UPLOADING', 'PROCESSING', 'READY', 'FAILED', 'ARCHIVED')",
            name=op.f("ck_media_assets_media_assets_status_valid"),
        ),
        sa.CheckConstraint(
            "version > 0",
            name=op.f("ck_media_assets_media_assets_version_positive"),
        ),
        sa.CheckConstraint(
            "width IS NULL OR width > 0",
            name=op.f("ck_media_assets_media_assets_width_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name=op.f("fk_media_assets_uploaded_by_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_media_assets")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_media_assets_storage_key")),
    )
    op.create_index(
        "ix_media_assets_checksum_digest",
        "media_assets",
        ["checksum_digest"],
        unique=False,
    )
    op.create_index(
        "ix_media_assets_status_created_at_id",
        "media_assets",
        ["status", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_media_assets_status_created_at_id", table_name="media_assets")
    op.drop_index("ix_media_assets_checksum_digest", table_name="media_assets")
    op.drop_table("media_assets")
