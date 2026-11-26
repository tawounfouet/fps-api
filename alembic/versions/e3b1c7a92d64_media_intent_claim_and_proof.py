"""media intent claim and promotion proof

Revision ID: e3b1c7a92d64
Revises: d4e7a92b6f31
Create Date: 2026-11-26 09:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e3b1c7a92d64"
down_revision: str | None = "d4e7a92b6f31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "media_assets",
        sa.Column("intent_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column("claim_owner", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "media_assets",
        sa.Column("failure_code", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column("detected_mime", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column("promotion_proof_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "media_assets",
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        op.f("ck_media_assets_media_assets_attempt_count_bounded"),
        "media_assets",
        "attempt_count >= 0 AND attempt_count <= 3",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_media_assets_media_assets_attempt_count_bounded"),
        "media_assets",
        type_="check",
    )
    op.drop_column("media_assets", "verified_at")
    op.drop_column("media_assets", "promoted_at")
    op.drop_column("media_assets", "promotion_proof_id")
    op.drop_column("media_assets", "detected_mime")
    op.drop_column("media_assets", "failure_code")
    op.drop_column("media_assets", "attempt_count")
    op.drop_column("media_assets", "claim_owner")
    op.drop_column("media_assets", "claimed_at")
    op.drop_column("media_assets", "intent_expires_at")
