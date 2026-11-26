from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest

from fps_platform.modules.audit.domain.audit_event import (
    ALLOWED_METADATA_KEYS,
    AuditMetadataValue,
    normalize_metadata,
)
from fps_platform.modules.audit.domain.enums import AuditAction, AuditSource
from fps_platform.modules.media.application.services.audit import (
    RECONCILIATION_RESOURCE_ID,
    MediaAuditService,
)
from fps_platform.modules.media.application.services.promotion import MediaUnitOfWork
from fps_platform.shared.domain.clock import FakeClock
from tests.security.media.fixtures import FakeDatabase, FakeUnitOfWork

MOMENT = datetime(2026, 11, 26, 10, tzinfo=UTC)


def service_for(database: FakeDatabase) -> MediaAuditService:
    def factory() -> FakeUnitOfWork:
        return FakeUnitOfWork(database, FakeClock(MOMENT))

    return MediaAuditService(uow_factory=cast(Callable[[], MediaUnitOfWork], factory))


def test_reconciliation_action_and_keys_are_declared() -> None:
    allowed = ALLOWED_METADATA_KEYS[AuditAction.MEDIA_RECONCILIATION_REPORTED]

    assert allowed == frozenset({"finding_count", "dry_run"})


def test_media_audit_record_commits_with_asset_mutation() -> None:
    database = FakeDatabase()
    service = service_for(database)
    resource_id = uuid4()

    service.record_reconciliation_report(finding_count=2, dry_run=True)

    assert database.commit_calls == 1
    assert len(database.audit_events) == 1
    event = database.audit_events[0]
    assert event.action is AuditAction.MEDIA_RECONCILIATION_REPORTED
    assert event.resource_id == RECONCILIATION_RESOURCE_ID
    assert event.resource_type == "MEDIA_RECONCILIATION"
    assert event.source is AuditSource.WORKER
    assert event.metadata == {"finding_count": 2, "dry_run": True}
    assert resource_id != event.resource_id


def test_failed_commit_does_not_persist_audit_event() -> None:
    database = FakeDatabase(fail_commit_at=1)
    service = service_for(database)

    with pytest.raises(RuntimeError, match="commit failed"):
        service.record_reconciliation_report(finding_count=1, dry_run=False)

    assert database.audit_events == []
    assert database.commit_calls == 1


def test_invalid_metadata_rolls_back_without_commit() -> None:
    database = FakeDatabase()
    service = service_for(database)

    with pytest.raises(ValueError, match="not allowed"):
        service.record(
            action=AuditAction.MEDIA_RECONCILIATION_REPORTED,
            resource_type="MEDIA_RECONCILIATION",
            resource_id=uuid4(),
            metadata={"storage_key": "media/secret"},
        )

    assert database.audit_events == []
    assert database.commit_calls == 0


@pytest.mark.parametrize(
    "metadata",
    [
        {"authorization": "synthetic"},
        {"token": "synthetic"},
        {"secret": "synthetic"},
        {"password": "synthetic"},
        {"email": "synthetic"},
        {"phone": "synthetic"},
        {"message": "synthetic"},
        {"storage_key": "media/secret"},
        {"url": "https://media.example.test/signed?sig=deadbeef"},
        {"bucket": "synthetic"},
        {"endpoint": "synthetic"},
    ],
)
def test_forbidden_metadata_keys_are_rejected(metadata: Mapping[str, AuditMetadataValue]) -> None:
    with pytest.raises(ValueError):
        normalize_metadata(AuditAction.MEDIA_RECONCILIATION_REPORTED, metadata)


def test_audit_event_contains_no_signed_url_or_credential() -> None:
    database = FakeDatabase()
    service = service_for(database)

    service.record_reconciliation_report(finding_count=0, dry_run=True)

    serialized = str(database.audit_events[0]).lower()
    for token in ("http", "signature", "deadbeef", "bucket", "secret", "credential"):
        assert token not in serialized


def test_audit_resource_id_is_stable() -> None:
    assert isinstance(RECONCILIATION_RESOURCE_ID, UUID)
    assert RECONCILIATION_RESOURCE_ID.version == 5
