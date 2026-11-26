from __future__ import annotations

from collections.abc import Mapping

from fps_platform.modules.media.domain.entities import MediaAsset
from fps_platform.modules.media.domain.enums import ChecksumAlgorithm, MediaStatus
from fps_platform.modules.media.domain.value_objects import (
    ByteSize,
    Checksum,
    LocalizedTextMap,
    MediaAttribution,
    MediaDimensions,
    MediaMetadata,
    MediaText,
    MimeType,
    OriginalFileName,
    StorageKey,
    to_localized_text_map,
)
from fps_platform.modules.media.infrastructure.persistence.models import MediaAssetRecord


def to_localized_map(value: Mapping[str, object]) -> LocalizedTextMap:
    normalized: dict[str, str] = {}
    for locale in ("fr", "en"):
        text = value.get(locale)
        if isinstance(text, str) and text:
            normalized[locale] = text
    return to_localized_text_map(normalized)


def to_media_asset_record(asset: MediaAsset) -> MediaAssetRecord:
    metadata = asset.metadata.as_mapping()
    attribution = metadata["attribution"]
    return MediaAssetRecord(
        id=asset.id,
        storage_key=str(asset.storage_key),
        original_filename=str(asset.original_filename),
        mime_type=str(asset.mime_type),
        byte_size=asset.byte_size.value,
        width=asset.dimensions.width if asset.dimensions is not None else None,
        height=asset.dimensions.height if asset.dimensions is not None else None,
        checksum_algorithm=asset.checksum.algorithm.value if asset.checksum is not None else None,
        checksum_digest=asset.checksum.digest if asset.checksum is not None else None,
        status=asset.status.value,
        title=str(asset.metadata.title) if asset.metadata.title is not None else None,
        alt_texts=dict(metadata["alt_texts"]) if isinstance(metadata["alt_texts"], dict) else {},
        captions=dict(metadata["captions"]) if isinstance(metadata["captions"], dict) else {},
        attribution=dict(attribution) if isinstance(attribution, dict) else None,
        uploaded_by_user_id=asset.uploaded_by,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        ready_at=asset.ready_at,
        archived_at=asset.archived_at,
        version=asset.version,
        intent_expires_at=asset.intent_expires_at,
        claimed_at=asset.claimed_at,
        claim_owner=asset.claim_owner,
        attempt_count=asset.attempt_count,
        failure_code=asset.failure_code,
        detected_mime=str(asset.detected_mime) if asset.detected_mime is not None else None,
        promotion_proof_id=asset.promotion_proof_id,
        promoted_at=asset.promoted_at,
        verified_at=asset.verified_at,
    )


def to_media_asset(record: MediaAssetRecord) -> MediaAsset:
    dimensions = (
        MediaDimensions(int(record.width), int(record.height))
        if record.width is not None and record.height is not None
        else None
    )
    checksum = (
        Checksum(ChecksumAlgorithm(record.checksum_algorithm), record.checksum_digest)
        if record.checksum_algorithm is not None and record.checksum_digest is not None
        else None
    )
    attribution_value: dict[str, str] = {}
    if isinstance(record.attribution, dict):
        attribution_value = {
            key: value
            for key, value in record.attribution.items()
            if key in {"source", "license"} and isinstance(value, str)
        }
    attribution = MediaAttribution(
        source=MediaText(attribution_value["source"]) if "source" in attribution_value else None,
        license=MediaText(attribution_value["license"]) if "license" in attribution_value else None,
    )
    metadata = MediaMetadata(
        title=MediaText(record.title) if record.title is not None else None,
        alt_texts=to_localized_map(record.alt_texts),
        captions=to_localized_map(record.captions),
        attribution=attribution if attribution_value else None,
    )
    return MediaAsset(
        id=record.id,
        storage_key=StorageKey(record.storage_key),
        original_filename=OriginalFileName(record.original_filename),
        mime_type=MimeType(record.mime_type),
        byte_size=ByteSize(record.byte_size),
        status=MediaStatus(record.status),
        metadata=metadata,
        uploaded_by=record.uploaded_by_user_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
        version=record.version,
        dimensions=dimensions,
        checksum=checksum,
        ready_at=record.ready_at,
        archived_at=record.archived_at,
        intent_expires_at=record.intent_expires_at,
        claimed_at=record.claimed_at,
        claim_owner=record.claim_owner,
        attempt_count=record.attempt_count,
        failure_code=record.failure_code,
        detected_mime=MimeType(record.detected_mime) if record.detected_mime is not None else None,
        promotion_proof_id=record.promotion_proof_id,
        promoted_at=record.promoted_at,
        verified_at=record.verified_at,
    )
