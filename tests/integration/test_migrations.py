from __future__ import annotations

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from alembic import command
from tests.fixtures.persistence_probe import ProbeBase

EXPECTED_HEAD = "e3b1c7a92d64"
pytestmark = pytest.mark.integration


def test_alembic_head_is_applied(engine: Engine) -> None:
    with engine.connect() as connection:
        version: str = connection.execute(
            text("select version_num from alembic_version")
        ).scalar_one()
    assert version == EXPECTED_HEAD


def test_constraint_names_are_stable(engine: Engine) -> None:
    inspector = inspect(engine)
    audit_checks = {item["name"] for item in inspector.get_check_constraints("audit_events")}
    outbox_checks = {item["name"] for item in inspector.get_check_constraints("outbox_events")}
    outbox_unique = {item["name"] for item in inspector.get_unique_constraints("outbox_events")}
    user_checks = {item["name"] for item in inspector.get_check_constraints("users")}
    user_unique = {item["name"] for item in inspector.get_unique_constraints("users")}
    media_checks = {item["name"] for item in inspector.get_check_constraints("media_assets")}
    media_unique = {item["name"] for item in inspector.get_unique_constraints("media_assets")}
    assert "ck_users_version_positive" in user_checks
    assert "uq_users_external_identity" in user_unique
    assert "ck_audit_events_actor_type_non_empty" in audit_checks
    assert "ck_audit_events_correlation_id_non_empty" in audit_checks
    assert "ck_outbox_events_attempt_count_bounded" in outbox_checks
    assert "ck_outbox_events_lease_fields_required" in outbox_checks
    assert "uq_outbox_events_dedup_key" in outbox_unique
    assert "ck_media_assets_media_assets_status_valid" in media_checks
    assert "ck_media_assets_media_assets_ready_requirements" in media_checks
    assert "ck_media_assets_media_assets_attempt_count_bounded" in media_checks
    assert "uq_media_assets_storage_key" in media_unique
    columns = {item["name"] for item in inspector.get_columns("media_assets")}
    assert {
        "intent_expires_at",
        "claimed_at",
        "claim_owner",
        "attempt_count",
        "failure_code",
        "detected_mime",
        "promotion_proof_id",
        "promoted_at",
        "verified_at",
    } <= columns


def test_alembic_check_has_no_drift(alembic_config: Config, engine: Engine) -> None:
    ProbeBase.metadata.drop_all(engine)
    try:
        command.check(alembic_config)
    finally:
        ProbeBase.metadata.create_all(engine)
