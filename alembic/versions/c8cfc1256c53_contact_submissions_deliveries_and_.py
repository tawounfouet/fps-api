"""contact submissions deliveries and idempotency

Revision ID: c8cfc1256c53
Revises: 9c4f6a1d8b72
Create Date: 2026-11-25 12:17:07.357322
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c8cfc1256c53"
down_revision: str | None = "9c4f6a1d8b72"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contact_idempotency_keys",
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("submission_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(fingerprint) = 64",
            name=op.f("ck_contact_idempotency_keys_contact_idempotency_keys_fingerprint_length"),
        ),
        sa.CheckConstraint(
            "length(key_hash) = 64",
            name=op.f("ck_contact_idempotency_keys_contact_idempotency_keys_hash_length"),
        ),
        sa.PrimaryKeyConstraint("key_hash", name=op.f("pk_contact_idempotency_keys")),
    )
    op.create_table(
        "contact_submissions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("first_name", sa.String(length=128), nullable=False),
        sa.Column("last_name", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("organisation", sa.String(length=128), nullable=True),
        sa.Column("job_title", sa.String(length=128), nullable=True),
        sa.Column("subject", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("workflow_status", sa.String(length=32), nullable=False),
        sa.Column("rgpd_consent", sa.Boolean(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("contacted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("close_reason_code", sa.String(length=64), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "workflow_status IN ('RECEIVED', 'CONTACTED', 'CLOSED', 'ARCHIVED')",
            name=op.f("ck_contact_submissions_contact_submissions_workflow_status_valid"),
        ),
        sa.CheckConstraint(
            "length(email) > 0",
            name=op.f("ck_contact_submissions_contact_submissions_email_non_empty"),
        ),
        sa.CheckConstraint(
            "length(first_name) > 0",
            name=op.f("ck_contact_submissions_contact_submissions_first_name_non_empty"),
        ),
        sa.CheckConstraint(
            "length(last_name) > 0",
            name=op.f("ck_contact_submissions_contact_submissions_last_name_non_empty"),
        ),
        sa.CheckConstraint(
            "length(message) > 0",
            name=op.f("ck_contact_submissions_contact_submissions_message_non_empty"),
        ),
        sa.CheckConstraint(
            "length(subject) > 0",
            name=op.f("ck_contact_submissions_contact_submissions_subject_non_empty"),
        ),
        sa.CheckConstraint(
            "version > 0", name=op.f("ck_contact_submissions_contact_submissions_version_positive")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contact_submissions")),
    )
    op.create_index(
        "ix_contact_submissions_workflow_status_received_at_id",
        "contact_submissions",
        ["workflow_status", "received_at", "id"],
        unique=False,
    )
    op.create_table(
        "contact_deliveries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("submission_id", sa.UUID(), nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_reference", sa.String(length=128), nullable=True),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "status IN ('PENDING', 'IN_PROGRESS', 'SUCCEEDED', 'FAILED')",
            name=op.f("ck_contact_deliveries_contact_deliveries_status_valid"),
        ),
        sa.CheckConstraint(
            "attempt_number > 0",
            name=op.f("ck_contact_deliveries_contact_deliveries_attempt_positive"),
        ),
        sa.CheckConstraint(
            "length(provider) > 0",
            name=op.f("ck_contact_deliveries_contact_deliveries_provider_non_empty"),
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"],
            ["contact_submissions.id"],
            name=op.f("fk_contact_deliveries_submission_id_contact_submissions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_contact_deliveries")),
    )
    op.create_index(
        "ix_contact_deliveries_status_requested_at",
        "contact_deliveries",
        ["status", "requested_at"],
        unique=False,
    )
    op.create_index(
        "uq_contact_deliveries_submission_channel_attempt",
        "contact_deliveries",
        ["submission_id", "channel", "attempt_number"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_contact_deliveries_submission_channel_attempt", table_name="contact_deliveries"
    )
    op.drop_index("ix_contact_deliveries_status_requested_at", table_name="contact_deliveries")
    op.drop_table("contact_deliveries")
    op.drop_index(
        "ix_contact_submissions_workflow_status_received_at_id", table_name="contact_submissions"
    )
    op.drop_table("contact_submissions")
    op.drop_table("contact_idempotency_keys")
