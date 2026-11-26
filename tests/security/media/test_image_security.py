from __future__ import annotations

from hashlib import sha256

import pytest

from fps_platform.modules.media.application.dto import MediaErrorCode
from fps_platform.modules.media.application.services.promotion import (
    MAX_IMAGE_BYTES,
    MediaInspectionError,
    MediaPromotionService,
    PromotionBlockedError,
    PromotionRequest,
)
from fps_platform.modules.media.domain.enums import MediaStatus
from fps_platform.modules.media.infrastructure.fake_storage import InMemoryMediaStoragePort
from fps_platform.modules.media.infrastructure.image_inspection import PillowImageInspector
from fps_platform.shared.domain.clock import FakeClock
from fps_platform.shared.domain.identifiers import Uuid4IdGenerator
from tests.security.media.fixtures import (
    FINAL_KEY,
    MOMENT,
    STAGING_KEY,
    FakeDatabase,
    FakeUnitOfWork,
    ImageFixture,
    claim_expires,
    corpus,
    make_asset,
)

INVALID = tuple(item for item in corpus() if not item.valid)
VALID = tuple(item for item in corpus() if item.valid)


def build(
    fixture: ImageFixture, *, max_bytes: int | None = None
) -> tuple[
    FakeDatabase, InMemoryMediaStoragePort, MediaPromotionService, PromotionRequest, FakeClock
]:
    clock = FakeClock(MOMENT)
    database = FakeDatabase()
    asset = make_asset()
    database.assets[asset.id] = asset
    storage = InMemoryMediaStoragePort(clock)
    storage.put_object(STAGING_KEY, fixture.body, fixture.declared_type or "image/jpeg")
    service = MediaPromotionService(
        storage=storage,
        inspector=PillowImageInspector(clock),
        uow_factory=lambda: FakeUnitOfWork(database, clock),
        clock=clock,
        id_generator=Uuid4IdGenerator(),
        max_bytes=MAX_IMAGE_BYTES if max_bytes is None else max_bytes,
    )
    request = PromotionRequest(
        asset_id=asset.id,
        destination_key=FINAL_KEY,
        expected_version=1,
        claim_owner="worker-1",
        claim_expires_at=claim_expires(clock),
    )
    return database, storage, service, request, clock


@pytest.mark.parametrize("fixture", INVALID, ids=[item.name for item in INVALID])
def test_no_invalid_fixture_reaches_ready(fixture: ImageFixture) -> None:
    database, storage, service, request, _clock = build(fixture)

    with pytest.raises((MediaInspectionError, PromotionBlockedError)):
        service.promote(request)

    promoted = database.assets[request.asset_id]
    assert promoted.status is not MediaStatus.READY
    assert promoted.ready_at is None
    assert promoted.checksum is None
    assert promoted.promotion_proof_id is None
    assert promoted.failure_code is not None
    assert not storage.head_object(FINAL_KEY).exists
    assert database.audit_events == []


@pytest.mark.parametrize("fixture", VALID, ids=[item.name for item in VALID])
def test_valid_fixtures_reach_ready_with_server_checksum(fixture: ImageFixture) -> None:
    database, _storage, service, request, _clock = build(fixture)

    evidence = service.promote(request)

    promoted = database.assets[request.asset_id]
    assert promoted.status is MediaStatus.READY
    assert promoted.checksum is not None
    assert promoted.checksum.digest == sha256(fixture.body).hexdigest()
    assert promoted.dimensions is not None
    assert promoted.dimensions.width > 0 and promoted.dimensions.height > 0
    assert promoted.promotion_proof_id == evidence.proof_id
    assert len(database.audit_events) == 1


def test_byte_budget_rejection_never_reaches_ready() -> None:
    fixture = VALID[0]
    database, storage, service, request, _clock = build(fixture, max_bytes=16)

    with pytest.raises(PromotionBlockedError) as raised:
        service.promote(request)

    assert raised.value.code == str(MediaErrorCode.MEDIA_TOO_LARGE)
    assert database.assets[request.asset_id].status is MediaStatus.FAILED
    assert not storage.head_object(FINAL_KEY).exists


def test_security_corpus_is_synthetic_and_bounded() -> None:
    assert all(len(item.body) < 1024 for item in corpus())
    assert all(item.name for item in corpus())
    assert len(INVALID) >= 11
    assert len(VALID) == 3
