"""identity users roles and external identities

Revision ID: 9c4f6a1d8b72
Revises: af1fb0f824bc
Create Date: 2026-11-25 12:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9c4f6a1d8b72"
down_revision: str | None = "af1fb0f824bc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_issuer", sa.String(length=512), nullable=False),
        sa.Column("external_subject", sa.String(length=256), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(display_name) > 0", name=op.f("ck_users_display_name_non_empty")
        ),
        sa.CheckConstraint("length(email) > 0", name=op.f("ck_users_email_non_empty")),
        sa.CheckConstraint(
            "length(external_issuer) > 0", name=op.f("ck_users_external_issuer_non_empty")
        ),
        sa.CheckConstraint(
            "length(external_subject) > 0", name=op.f("ck_users_external_subject_non_empty")
        ),
        sa.CheckConstraint("version > 0", name=op.f("ck_users_version_positive")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint(
            "external_issuer",
            "external_subject",
            name=op.f("uq_users_external_identity"),
        ),
    )
    op.create_index("ix_users_status", "users", ["status"], unique=False)
    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(code) > 0", name=op.f("ck_roles_code_non_empty")),
        sa.CheckConstraint("length(name) > 0", name=op.f("ck_roles_name_non_empty")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
        sa.UniqueConstraint("code", name=op.f("uq_roles_code")),
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assigned_by_user_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["assigned_by_user_id"],
            ["users.id"],
            name=op.f("fk_user_roles_assigned_by_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name=op.f("fk_user_roles_role_id_roles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_roles_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "role_id", name=op.f("pk_user_roles")),
    )
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_roles_role_id", table_name="user_roles")
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_index("ix_users_status", table_name="users")
    op.drop_table("users")
