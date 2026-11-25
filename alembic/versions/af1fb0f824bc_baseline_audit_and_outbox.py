"""baseline audit and outbox

Revision ID: af1fb0f824bc
Revises:
Create Date: 2026-11-25 08:04:55.270747
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "af1fb0f824bc"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.CheckConstraint("length(action) > 0", name=op.f("ck_audit_events_action_non_empty")),
        sa.CheckConstraint(
            "length(actor_type) > 0", name=op.f("ck_audit_events_actor_type_non_empty")
        ),
        sa.CheckConstraint(
            "length(correlation_id) > 0", name=op.f("ck_audit_events_correlation_id_non_empty")
        ),
        sa.CheckConstraint(
            "length(resource_type) > 0", name=op.f("ck_audit_events_resource_type_non_empty")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index(
        "ix_audit_events_actor_type_actor_id_occurred_at",
        "audit_events",
        ["actor_type", "actor_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_correlation_id", "audit_events", ["correlation_id"], unique=False
    )
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"], unique=False)
    op.create_index(
        "ix_audit_events_resource_type_resource_id_occurred_at",
        "audit_events",
        ["resource_type", "resource_id", "occurred_at"],
        unique=False,
    )
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("operation_id", sa.String(length=128), nullable=False),
        sa.Column("dedup_key", sa.String(length=128), nullable=False),
        sa.Column("payload_version", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("lease_token", sa.Uuid(), nullable=True),
        sa.Column("leased_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.String(length=128), nullable=True),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "status <> 'COMPLETED' OR completed_at IS NOT NULL",
            name=op.f("ck_outbox_events_completed_at_required"),
        ),
        sa.CheckConstraint(
            "status <> 'LEASED' OR (lease_token IS NOT NULL AND leased_until IS NOT NULL)",
            name=op.f("ck_outbox_events_lease_fields_required"),
        ),
        sa.CheckConstraint(
            "attempt_count <= max_attempts", name=op.f("ck_outbox_events_attempt_count_bounded")
        ),
        sa.CheckConstraint(
            "attempt_count >= 0", name=op.f("ck_outbox_events_attempt_count_non_negative")
        ),
        sa.CheckConstraint("max_attempts > 0", name=op.f("ck_outbox_events_max_attempts_positive")),
        sa.CheckConstraint(
            "payload_version > 0", name=op.f("ck_outbox_events_payload_version_positive")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_outbox_events")),
        sa.UniqueConstraint("dedup_key", name=op.f("uq_outbox_events_dedup_key")),
    )
    op.create_index(
        "ix_outbox_events_aggregate_type_aggregate_id",
        "outbox_events",
        ["aggregate_type", "aggregate_id"],
        unique=False,
    )
    op.create_index(
        "ix_outbox_events_leased_until", "outbox_events", ["leased_until"], unique=False
    )
    op.create_index(
        "ix_outbox_events_status_available_at_created_at_id",
        "outbox_events",
        ["status", "available_at", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_events_status_available_at_created_at_id", table_name="outbox_events")
    op.drop_index("ix_outbox_events_leased_until", table_name="outbox_events")
    op.drop_index("ix_outbox_events_aggregate_type_aggregate_id", table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_index(
        "ix_audit_events_resource_type_resource_id_occurred_at", table_name="audit_events"
    )
    op.drop_index("ix_audit_events_occurred_at", table_name="audit_events")
    op.drop_index("ix_audit_events_correlation_id", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_type_actor_id_occurred_at", table_name="audit_events")
    op.drop_table("audit_events")
