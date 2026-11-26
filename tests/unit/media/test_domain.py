from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

import pytest

from fps_platform.modules.media.domain.entities import MediaAsset
from fps_platform.modules.media.domain.enums import ChecksumAlgorithm, MediaStatus
from fps_platform.modules.media.domain.exceptions import (
    InvalidMediaObjectError,
    InvalidMediaTransitionError,
)
from fps_platform.modules.media.domain.value_objects import (
    ByteSize,
    Checksum,
    LocalizedTextMap,
    MediaDimensions,
    MediaMetadata,
    MediaText,
    MimeType,
    OriginalFileName,
    PromotionEvidence,
    StorageKey,
)

MOMENT = datetime(2026, 6, 4, 9, 0, tzinfo=UTC)
DIGEST = "a" * 64


def make_asset() -> MediaAsset:
    return MediaAsset(
        id=uuid4(),
        storage_key=StorageKey("media/asset.jpg"),
        original_filename=OriginalFileName("photo.jpg"),
        mime_type=MimeType("image/jpeg"),
        byte_size=ByteSize(256),
        status=MediaStatus.UPLOADING,
        metadata=MediaMetadata(),
        uploaded_by=uuid4(),
        created_at=MOMENT,
        updated_at=MOMENT,
        version=1,
    )


def inspection_evidence() -> PromotionEvidence:
    return PromotionEvidence(
        proof_id=uuid4(),
        storage_key=StorageKey("media/asset.jpg"),
        detected_mime=MimeType("image/jpeg"),
        byte_size=ByteSize(256),
        dimensions=MediaDimensions(640, 480),
        checksum=Checksum(ChecksumAlgorithm.SHA256, DIGEST),
        verified_at=MOMENT,
    )


def claim(asset: MediaAsset, owner: str = "worker-1") -> None:
    asset.claim(MOMENT, owner=owner, expires_at=MOMENT + timedelta(seconds=120))


def test_media_lifecycle_and_inspection_proof() -> None:
    asset = make_asset()
    assert asset.version == 1

    claim(asset)
    asset.mark_processing(MOMENT)
    proof = inspection_evidence()
    asset.mark_ready(MOMENT, evidence=proof)

    assert asset.status is MediaStatus.READY
    assert asset.version == 4
    assert asset.ready_at == MOMENT
    assert asset.detected_mime == proof.detected_mime
    assert asset.promotion_proof_id == proof.proof_id
    assert asset.promoted_at == MOMENT
    assert asset.verified_at == proof.verified_at

    asset.archive(MOMENT)
    assert cast(MediaStatus, asset.status) is MediaStatus.ARCHIVED
    assert asset.version == 5

    restore_proof = replace(proof, proof_id=uuid4())
    asset.restore(MOMENT, evidence=restore_proof)
    assert asset.status is MediaStatus.READY
    assert asset.version == 6
    assert asset.promotion_proof_id == restore_proof.proof_id
    assert asset.archived_at is None


def test_invalid_transitions_and_failure_codes() -> None:
    asset = make_asset()

    with pytest.raises(InvalidMediaTransitionError):
        asset.mark_processing(MOMENT)
    with pytest.raises(InvalidMediaTransitionError):
        asset.archive(MOMENT)

    claim(asset)
    asset.mark_processing(MOMENT)
    with pytest.raises(InvalidMediaTransitionError):
        asset.mark_processing(MOMENT)
    with pytest.raises(InvalidMediaTransitionError):
        asset.update_metadata(MOMENT, MediaMetadata())

    asset.mark_failed(MOMENT, reason_code="MEDIA_CORRUPT")
    assert asset.status is MediaStatus.FAILED
    assert asset.failure_code == "MEDIA_CORRUPT"
    with pytest.raises(InvalidMediaTransitionError):
        asset.mark_ready(MOMENT, evidence=inspection_evidence())

    asset.retry(MOMENT, reason_code="RETRY")
    assert cast(MediaStatus, asset.status) is MediaStatus.UPLOADING
    assert asset.failure_code == "RETRY"


def test_ready_original_cannot_be_promoted_again() -> None:
    asset = make_asset()
    claim(asset)
    asset.mark_processing(MOMENT)
    asset.mark_ready(MOMENT, evidence=inspection_evidence())

    with pytest.raises(InvalidMediaTransitionError):
        asset.mark_ready(MOMENT, evidence=inspection_evidence())


def test_retry_budget_is_bounded() -> None:
    asset = make_asset()
    for _ in range(3):
        claim(asset)
        asset.release_claim(MOMENT)
    assert asset.attempt_count == 3

    with pytest.raises(InvalidMediaTransitionError):
        claim(asset)


def test_zero_byte_promotion_evidence_is_rejected() -> None:
    asset = make_asset()
    claim(asset)
    asset.mark_processing(MOMENT)
    zero_byte_evidence = replace(inspection_evidence(), byte_size=ByteSize(0))
    with pytest.raises(InvalidMediaObjectError):
        asset.mark_ready(MOMENT, evidence=zero_byte_evidence)


def test_promotion_evidence_requires_utc_and_locale_map_is_explicit() -> None:
    evidence = inspection_evidence()
    with pytest.raises(ValueError):
        replace(evidence, verified_at=datetime(2026, 6, 4, 9, 0))

    metadata = MediaMetadata(
        alt_texts=LocalizedTextMap(fr=MediaText("Description"), en=MediaText("Description"))
    )
    asset = make_asset()
    asset.update_metadata(MOMENT, metadata)
    assert asset.metadata.alt_texts.en is not None
    assert asset.metadata.alt_texts.en.value == "Description"
