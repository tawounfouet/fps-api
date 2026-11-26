from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session, sessionmaker

from fps_platform.modules.media.domain.entities import MediaAsset
from fps_platform.modules.media.domain.enums import ChecksumAlgorithm, MediaStatus
from fps_platform.modules.media.domain.value_objects import (
    ByteSize,
    Checksum,
    MediaDimensions,
    MediaMetadata,
    MimeType,
    OriginalFileName,
    PromotionEvidence,
    StorageKey,
)
from fps_platform.modules.media.infrastructure.persistence.repository import (
    SqlAlchemyMediaAssetRepository,
)
from fps_platform.shared.domain.errors import ConcurrentModificationError

pytestmark = pytest.mark.integration
MOMENT = datetime(2026, 11, 26, 9, 0, tzinfo=UTC)
DIGEST = "b" * 64


def make_asset(uploaded_by: UUID) -> MediaAsset:
    return MediaAsset(
        id=uuid4(),
        storage_key=StorageKey("media/integration/original.jpg"),
        original_filename=OriginalFileName("original.jpg"),
        mime_type=MimeType("image/jpeg"),
        byte_size=ByteSize(128),
        status=MediaStatus.UPLOADING,
        metadata=MediaMetadata(),
        uploaded_by=uploaded_by,
        created_at=MOMENT,
        updated_at=MOMENT,
        version=1,
    )


def make_evidence(asset: MediaAsset) -> PromotionEvidence:
    return PromotionEvidence(
        proof_id=uuid4(),
        storage_key=asset.storage_key,
        detected_mime=MimeType("image/jpeg"),
        byte_size=asset.byte_size,
        dimensions=MediaDimensions(320, 240),
        checksum=Checksum(ChecksumAlgorithm.SHA256, DIGEST),
        verified_at=MOMENT,
    )


def test_media_repository_persists_claim_and_promotion_proof(
    session_factory: sessionmaker[Session],
    uploader_user_id: UUID,
) -> None:
    asset = make_asset(uploader_user_id)
    with session_factory() as session:
        repository = SqlAlchemyMediaAssetRepository(session)
        repository.add(asset)
        expected_version = asset.version
        asset.claim(MOMENT, owner="worker-1", expires_at=MOMENT + timedelta(seconds=120))
        repository.save(asset, expected_version=expected_version)
        session.commit()

    with session_factory() as session:
        repository = SqlAlchemyMediaAssetRepository(session)
        loaded = repository.get(asset.id)
        assert loaded is not None
        assert loaded.attempt_count == 1
        assert loaded.claim_owner == "worker-1"
        assert loaded.intent_expires_at == MOMENT + timedelta(seconds=120)
        expected_version = loaded.version
        loaded.mark_processing(MOMENT)
        evidence = make_evidence(loaded)
        loaded.mark_ready(MOMENT, evidence=evidence)
        repository.save(loaded, expected_version=expected_version)
        session.commit()

    with session_factory() as session:
        repository = SqlAlchemyMediaAssetRepository(session)
        final = repository.get(asset.id)
        assert final is not None
        assert final.status is MediaStatus.READY
        assert final.promotion_proof_id == evidence.proof_id
        assert final.detected_mime == evidence.detected_mime
        assert final.verified_at == evidence.verified_at
        assert final.attempt_count == 1


def test_media_repository_rejects_stale_version(
    session_factory: sessionmaker[Session],
    uploader_user_id: UUID,
) -> None:
    asset = make_asset(uploader_user_id)
    with session_factory() as session:
        repository = SqlAlchemyMediaAssetRepository(session)
        repository.add(asset)
        session.commit()

    stale = make_asset(uploader_user_id)
    stale.id = asset.id
    with session_factory() as session:
        repository = SqlAlchemyMediaAssetRepository(session)
        stale.update_metadata(MOMENT, stale.metadata)
        with pytest.raises(ConcurrentModificationError):
            repository.save(stale, expected_version=2)
