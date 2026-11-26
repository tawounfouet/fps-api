from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from fps_platform.modules.media.application.dto import ReconciliationFindingCode
from fps_platform.modules.media.application.services.reconciliation import (
    FakeStorageObjectCatalog,
    ReconciliationService,
)
from fps_platform.modules.media.domain.entities import MediaAsset
from fps_platform.modules.media.domain.enums import ChecksumAlgorithm, MediaStatus
from fps_platform.modules.media.domain.value_objects import (
    ByteSize,
    Checksum,
    MediaDimensions,
    MediaMetadata,
    MimeType,
    OriginalFileName,
    StorageKey,
)
from fps_platform.modules.media.infrastructure.fake_storage import InMemoryMediaStoragePort
from fps_platform.shared.domain.clock import FakeClock
from tests.integration.conftest import MakeUow

pytestmark = pytest.mark.integration
MOMENT = datetime(2026, 11, 26, 12, tzinfo=UTC)
FINAL_KEY = StorageKey("media/integration/original.jpg")
ORPHAN_KEY = StorageKey("staging/worker-1/6a3c1e44-19c9-4e0e-9c0a-6d1f2a5b8c11")


def make_ready_asset() -> MediaAsset:
    return MediaAsset(
        id=uuid4(),
        storage_key=FINAL_KEY,
        original_filename=OriginalFileName("original.jpg"),
        mime_type=MimeType("image/jpeg"),
        byte_size=ByteSize(128),
        status=MediaStatus.READY,
        metadata=MediaMetadata(),
        uploaded_by=uuid4(),
        created_at=MOMENT - timedelta(minutes=5),
        updated_at=MOMENT - timedelta(minutes=5),
        version=2,
        dimensions=MediaDimensions(12, 8),
        checksum=Checksum(ChecksumAlgorithm.SHA256, "a" * 64),
        ready_at=MOMENT - timedelta(minutes=5),
        promotion_proof_id=uuid4(),
        detected_mime=MimeType("image/jpeg"),
        verified_at=MOMENT - timedelta(minutes=5),
    )


def test_missing_object_is_reported_without_deletion(make_uow: MakeUow) -> None:
    clock = FakeClock(MOMENT)
    storage = InMemoryMediaStoragePort(clock)
    asset = make_ready_asset()

    with make_uow(clock=clock) as uow:
        uow.media_assets.add(asset)
        uow.commit()

    with make_uow(clock=clock) as uow:
        service = ReconciliationService(
            assets=uow.media_assets,
            storage=storage,
            catalog=FakeStorageObjectCatalog(storage),
            clock=clock,
        )
        report = service.run()

        assert report.dry_run is True
        assert report.scanned_assets == 1
        assert [item.code for item in report.findings] == [ReconciliationFindingCode.MISSING_OBJECT]
        assert report.findings[0].media_id == asset.id
        assert uow.media_assets.get(asset.id) is not None
        assert (
            uow.audit_events.list_by_resource(
                resource_type="MEDIA_RECONCILIATION", resource_id=asset.id
            )
            == []
        )

    assert storage.head_object(FINAL_KEY).exists is False


def test_orphan_staging_object_is_reported_and_kept(make_uow: MakeUow) -> None:
    clock = FakeClock(MOMENT)
    storage = InMemoryMediaStoragePort(clock)
    storage.put_object(ORPHAN_KEY, b"synthetic-bytes", "image/jpeg")

    with make_uow(clock=clock) as uow:
        service = ReconciliationService(
            assets=uow.media_assets,
            storage=storage,
            catalog=FakeStorageObjectCatalog(storage),
            clock=clock,
        )
        report = service.run()

        assert report.dry_run is True
        assert report.scanned_assets == 0
        assert report.scanned_objects == 1
        assert [item.code for item in report.findings] == [ReconciliationFindingCode.ORPHAN_OBJECT]
        assert report.findings[0].media_id is None
        assert uow.media_assets.get_by_storage_key(str(ORPHAN_KEY)) is None

    assert storage.head_object(ORPHAN_KEY).exists is True


def test_size_mismatch_is_reported_without_mutation(make_uow: MakeUow) -> None:
    clock = FakeClock(MOMENT)
    storage = InMemoryMediaStoragePort(clock)
    storage.put_object(FINAL_KEY, b"x" * 64, "image/jpeg")
    asset = make_ready_asset()

    with make_uow(clock=clock) as uow:
        uow.media_assets.add(asset)
        uow.commit()

    with make_uow(clock=clock) as uow:
        service = ReconciliationService(
            assets=uow.media_assets,
            storage=storage,
            catalog=FakeStorageObjectCatalog(storage),
            clock=clock,
        )
        report = service.run()

        assert [item.code for item in report.findings] == [ReconciliationFindingCode.SIZE_MISMATCH]
        assert report.findings[0].observed == 64
        stored = uow.media_assets.get(asset.id)
        assert stored is not None
        assert stored.version == 2
