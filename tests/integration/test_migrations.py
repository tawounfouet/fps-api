from __future__ import annotations

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from alembic import command
from tests.fixtures.persistence_probe import ProbeBase

EXPECTED_HEAD = "af1fb0f824bc"
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
    assert "ck_audit_events_actor_type_non_empty" in audit_checks
    assert "ck_audit_events_correlation_id_non_empty" in audit_checks
    assert "ck_outbox_events_attempt_count_bounded" in outbox_checks
    assert "ck_outbox_events_lease_fields_required" in outbox_checks
    assert "uq_outbox_events_dedup_key" in outbox_unique


def test_alembic_check_has_no_drift(alembic_config: Config, engine: Engine) -> None:
    ProbeBase.metadata.drop_all(engine)
    try:
        command.check(alembic_config)
    finally:
        ProbeBase.metadata.create_all(engine)
