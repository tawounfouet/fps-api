from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from uuid import UUID

import pytest

from fps_platform.modules.media.application.dto import MediaErrorCode
from fps_platform.modules.media.application.ports import InspectedObject
from fps_platform.modules.media.application.services.promotion import (
    FAILURE_ATTEMPT_BUDGET,
    FAILURE_VERSION_CONFLICT,
    MediaInspectionError,
    MediaPromotionService,
    PromotionBlockedError,
    PromotionRequest,
)
from fps_platform.modules.media.domain.entities import MediaAsset
from fps_platform.modules.media.domain.enums import MediaStatus
from fps_platform.modules.media.domain.exceptions import (
    InvalidMediaTransitionError,
    MediaStoragePermanentError,
    MediaStorageTransientError,
)
from fps_platform.modules.media.domain.value_objects import MimeType, StorageKey
from fps_platform.modules.media.infrastructure.fake_storage import InMemoryMediaStoragePort
from fps_platform.modules.media.infrastructure.image_inspection import PillowImageInspector
from fps_platform.shared.domain.clock import FakeClock
from fps_platform.shared.domain.errors import ConcurrentModificationError
from fps_platform.shared.domain.identifiers import Uuid4IdGenerator
from tests.security.media.fixtures import (
    FINAL_KEY,
    MOMENT,
    STAGING_KEY,
    CorruptingFinalStorage,
    FailingCopyStorage,
    FailingReadStorage,
    FakeDatabase,
    FakeUnitOfWork,
    claim_expires,
    corpus,
    make_asset,
)


class VersionChangingStorage(InMemoryMediaStoragePort):
    def __init__(self, clock: FakeClock, database: FakeDatabase, asset_id: UUID) -> None:
        super().__init__(clock)
        self._database = database
        self._asset_id = asset_id

    def copy_object(self, *, source_key: StorageKey, destination_key: StorageKey) -> None:
        super().copy_object(source_key=source_key, destination_key=destination_key)
        with FakeUnitOfWork(self._database, self._clock) as uow:
            asset = uow.media_assets.get(self._asset_id)
            if asset is None:
                raise AssertionError("asset disappeared during promotion")
            version = asset.version
            asset.version = version + 1
            uow.media_assets.save(asset, expected_version=version)
            uow.commit()


def setup_service(
    *,
    asset: MediaAsset | None = None,
    storage: InMemoryMediaStoragePort | None = None,
    clock: FakeClock | None = None,
    body: bytes | None = None,
    declared_type: str | None = None,
    fail_commit_at: int | None = None,
) -> tuple[FakeDatabase, InMemoryMediaStoragePort, MediaPromotionService, MediaAsset, FakeClock]:
    clock = clock or FakeClock(MOMENT)
    asset = asset or make_asset()
    database = FakeDatabase(fail_commit_at=fail_commit_at)
    database.assets[asset.id] = asset
    storage = storage or InMemoryMediaStoragePort(clock)
    if body is not None:
        storage.put_object(STAGING_KEY, body, declared_type or "image/png")
    service = MediaPromotionService(
        storage=storage,
        inspector=PillowImageInspector(clock),
        uow_factory=lambda: FakeUnitOfWork(database, clock),
        clock=clock,
        id_generator=Uuid4IdGenerator(),
    )
    return database, storage, service, asset, clock


def new_request(
    asset: MediaAsset,
    clock: FakeClock,
    *,
    version: int | None = None,
    owner: str | None = "worker-1",
) -> PromotionRequest:
    return PromotionRequest(
        asset_id=asset.id,
        destination_key=FINAL_KEY,
        expected_version=asset.version if version is None else version,
        claim_owner=owner,
        claim_expires_at=claim_expires(clock) if owner is not None else None,
    )


def valid_body() -> bytes:
    return next(item.body for item in corpus() if item.name == "jpeg")


def test_promotion_reaches_ready_with_verified_evidence_and_audit() -> None:
    body = valid_body()
    database, storage, service, asset, clock = setup_service(body=body, declared_type="image/jpeg")

    evidence = service.promote(new_request(asset, clock))

    promoted = database.assets[asset.id]
    assert promoted.status is MediaStatus.READY
    assert promoted.detected_mime == MimeType("image/jpeg")
    assert promoted.checksum is not None
    assert promoted.checksum.digest == sha256(body).hexdigest()
    assert promoted.promotion_proof_id == evidence.proof_id
    assert evidence.storage_key == FINAL_KEY
    assert storage.head_object(FINAL_KEY).exists
    assert storage.head_object(STAGING_KEY).exists
    assert len(database.audit_events) == 1
    assert database.audit_events[0].resource_id == asset.id


def test_claimed_processing_asset_is_promoted_by_version() -> None:
    body = valid_body()
    asset = make_asset(status=MediaStatus.PROCESSING, version=3, claim_owner="worker-1")
    database, _storage, service, _asset, clock = setup_service(
        asset=asset, body=body, declared_type="image/jpeg"
    )

    service.promote(new_request(asset, clock, version=3))

    assert database.assets[asset.id].status is MediaStatus.READY
    assert database.assets[asset.id].attempt_count == 0


INVALID_EXPECTATIONS = {
    "avif": (MediaInspectionError, MediaErrorCode.UNSUPPORTED_MEDIA_TYPE),
    "avif_truncated": (MediaInspectionError, MediaErrorCode.UNSUPPORTED_MEDIA_TYPE),
    "fake_mime_html": (MediaInspectionError, MediaErrorCode.UNSUPPORTED_MEDIA_TYPE),
    "fake_mime_png": (MediaInspectionError, MediaErrorCode.UNSUPPORTED_MEDIA_TYPE),
    "svg": (MediaInspectionError, MediaErrorCode.UNSUPPORTED_MEDIA_TYPE),
    "html": (MediaInspectionError, MediaErrorCode.UNSUPPORTED_MEDIA_TYPE),
    "exif_gps": (MediaInspectionError, MediaErrorCode.UNSUPPORTED_MEDIA_TYPE),
    "pixel_bomb": (MediaInspectionError, MediaErrorCode.MEDIA_TOO_LARGE),
    "empty": (PromotionBlockedError, MediaErrorCode.MEDIA_CORRUPT),
    "truncated_jpeg": (MediaInspectionError, MediaErrorCode.MEDIA_CORRUPT),
    "corrupted_png": (MediaInspectionError, MediaErrorCode.MEDIA_CORRUPT),
}


@pytest.mark.parametrize("name", sorted(INVALID_EXPECTATIONS))
def test_invalid_image_never_reaches_ready(name: str) -> None:
    fixture = next(item for item in corpus() if item.name == name)
    database, storage, service, asset, clock = setup_service(
        body=fixture.body, declared_type=fixture.declared_type
    )
    expected_error, expected_code = INVALID_EXPECTATIONS[name]

    with pytest.raises(expected_error):
        service.promote(new_request(asset, clock))

    promoted = database.assets[asset.id]
    assert promoted.status is MediaStatus.FAILED
    assert promoted.failure_code == str(expected_code)
    assert promoted.checksum is None
    assert not storage.head_object(FINAL_KEY).exists
    assert database.audit_events == []


def test_head_without_usable_read_never_reaches_ready() -> None:
    clock = FakeClock(MOMENT)
    storage = FailingReadStorage(clock)
    database, _storage, service, asset, clock = setup_service(
        storage=storage, clock=clock, body=valid_body(), declared_type="image/jpeg"
    )

    with pytest.raises(MediaStorageTransientError):
        service.promote(new_request(asset, clock))

    assert database.assets[asset.id].failure_code == str(MediaErrorCode.STORAGE_TEMPORARY_FAILURE)
    assert database.assets[asset.id].status is MediaStatus.FAILED
    assert not storage.head_object(FINAL_KEY).exists


def test_final_checksum_mismatch_never_reaches_ready() -> None:
    clock = FakeClock(MOMENT)
    storage = CorruptingFinalStorage(clock)
    database, _storage, service, asset, clock = setup_service(
        storage=storage, clock=clock, body=valid_body(), declared_type="image/jpeg"
    )

    with pytest.raises(PromotionBlockedError):
        service.promote(new_request(asset, clock))

    assert database.assets[asset.id].status is MediaStatus.FAILED
    assert database.assets[asset.id].failure_code == str(MediaErrorCode.MEDIA_CORRUPT)


def test_copy_failure_and_overwrite_attempt_are_diagnosable() -> None:
    clock = FakeClock(MOMENT)
    failing_storage = FailingCopyStorage(clock)
    database, _storage, service, asset, clock = setup_service(
        storage=failing_storage, clock=clock, body=valid_body(), declared_type="image/jpeg"
    )

    with pytest.raises(MediaStoragePermanentError):
        service.promote(new_request(asset, clock))

    assert database.assets[asset.id].failure_code == str(MediaErrorCode.MEDIA_STILL_IN_USE)
    assert database.assets[asset.id].status is MediaStatus.FAILED

    database, storage, service, asset, clock = setup_service(
        body=valid_body(), declared_type="image/jpeg"
    )
    storage.put_object(FINAL_KEY, b"original", "image/jpeg")
    with pytest.raises(MediaStoragePermanentError):
        service.promote(new_request(asset, clock))
    assert storage.head_object(FINAL_KEY).byte_size == len(b"original")
    assert database.assets[asset.id].status is MediaStatus.FAILED


def test_copy_succeeded_but_commit_failure_leaves_no_ready() -> None:
    database, storage, service, asset, clock = setup_service(
        body=valid_body(), declared_type="image/jpeg", fail_commit_at=2
    )

    with pytest.raises(RuntimeError, match="database commit failed"):
        service.promote(new_request(asset, clock))

    assert database.assets[asset.id].status is MediaStatus.FAILED
    assert not database.assets[asset.id].ready_at
    assert database.assets[asset.id].checksum is None
    assert database.audit_events == []
    assert storage.head_object(FINAL_KEY).exists


def test_processing_version_conflict_is_reported_without_ready() -> None:
    clock = FakeClock(MOMENT)
    database = FakeDatabase()
    asset = make_asset()
    database.assets[asset.id] = asset
    storage = VersionChangingStorage(clock, database, asset.id)
    storage.put_object(STAGING_KEY, valid_body(), "image/jpeg")
    service = MediaPromotionService(
        storage=storage,
        inspector=PillowImageInspector(clock),
        uow_factory=lambda: FakeUnitOfWork(database, clock),
        clock=clock,
        id_generator=Uuid4IdGenerator(),
    )

    with pytest.raises(PromotionBlockedError) as raised:
        service.promote(new_request(asset, clock))

    assert raised.value.code == FAILURE_VERSION_CONFLICT
    assert database.assets[asset.id].status != MediaStatus.READY


def test_three_attempt_budget_is_enforced() -> None:
    asset = make_asset(attempt_count=3)
    database, _storage, service, _asset, clock = setup_service(
        asset=asset, body=valid_body(), declared_type="image/jpeg"
    )

    with pytest.raises(PromotionBlockedError) as raised:
        service.promote(new_request(asset, clock))

    assert raised.value.code == FAILURE_ATTEMPT_BUDGET
    assert database.assets[asset.id].status is MediaStatus.FAILED
    assert database.assets[asset.id].failure_code == FAILURE_ATTEMPT_BUDGET
    with pytest.raises(InvalidMediaTransitionError):
        database.assets[asset.id].retry(MOMENT)


def test_stale_version_is_rejected_before_any_storage_call() -> None:
    asset = make_asset()
    database, storage, service, _asset, clock = setup_service(asset=asset, body=valid_body())

    with pytest.raises(ConcurrentModificationError):
        service.promote(new_request(asset, clock, version=99))

    assert database.assets[asset.id].status is MediaStatus.UPLOADING
    assert not storage.head_object(FINAL_KEY).exists


def test_inspected_object_shape_is_not_reimplemented_by_service() -> None:
    source = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "fps_platform"
        / "modules"
        / "media"
        / "application"
        / "services"
        / "promotion.py"
    ).read_text(encoding="utf-8")
    assert "read_or_inspect_object" in source
    assert InspectedObject.__name__ not in source
    assert "MimeType(" not in source
