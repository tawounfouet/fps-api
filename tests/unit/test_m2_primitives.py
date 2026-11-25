from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from fps_platform.modules.audit.domain.audit_event import normalize_metadata
from fps_platform.modules.audit.domain.enums import AuditAction
from fps_platform.modules.outbox.domain.enums import OutboxEventType
from fps_platform.modules.outbox.domain.outbox_event import normalize_payload
from fps_platform.shared.domain.actor import ActorContext, ActorType
from fps_platform.shared.domain.clock import FakeClock
from fps_platform.shared.infrastructure.persistence.naming import CONVENTION


def test_fake_clock_is_aware_utc_and_advanceable() -> None:
    fixed = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
    clock = FakeClock(fixed)
    assert clock.now() == fixed
    clock.advance(minutes=5)
    assert clock.now() == datetime(2026, 11, 25, 12, 5, tzinfo=UTC)


def test_system_actor_context_rejects_actor_id() -> None:
    with pytest.raises(ValueError):
        ActorContext(
            actor_type=ActorType.SYSTEM,
            correlation_id="m2-unit",
            actor_id=uuid4(),
        )


def test_audit_metadata_allowlist_rejects_personal_data() -> None:
    with pytest.raises(ValueError):
        normalize_metadata(
            AuditAction.PERSISTENCE_PROBE_CREATED,
            {"email": "test@example.invalid"},
        )


def test_audit_metadata_allows_declared_keys() -> None:
    normalized = normalize_metadata(
        AuditAction.PERSISTENCE_PROBE_UPDATED,
        {"from_version": 1, "to_version": 2},
    )
    assert dict(normalized) == {"from_version": 1, "to_version": 2}


def test_outbox_payload_rejects_message_content() -> None:
    with pytest.raises(ValueError):
        normalize_payload(
            OutboxEventType.CONTACT_DELIVERY_REQUESTED,
            {"message": "private contact content"},
        )


def test_naming_convention_is_stable() -> None:
    assert CONVENTION["pk"] == "pk_%(table_name)s"
    assert CONVENTION["fk"] == "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
    assert CONVENTION["uq"] == "uq_%(table_name)s_%(column_0_name)s"
    assert CONVENTION["ck"] == "ck_%(table_name)s_%(constraint_name)s"
    assert CONVENTION["ix"] == "ix_%(table_name)s_%(column_0_name)s"
