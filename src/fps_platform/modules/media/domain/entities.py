from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fps_platform.modules.media.domain.enums import MediaStatus
from fps_platform.modules.media.domain.exceptions import (
    InvalidMediaObjectError,
    InvalidMediaTransitionError,
)
from fps_platform.modules.media.domain.value_objects import (
    MAX_UPLOAD_ATTEMPTS,
    ByteSize,
    Checksum,
    MediaDimensions,
    MediaMetadata,
    MimeType,
    OriginalFileName,
    PromotionEvidence,
    StorageKey,
)


def require_aware_utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must be aware UTC")
    return value.astimezone(UTC)


@dataclass(slots=True)
class MediaAsset:
    id: UUID
    storage_key: StorageKey
    original_filename: OriginalFileName
    mime_type: MimeType
    byte_size: ByteSize
    status: MediaStatus
    metadata: MediaMetadata
    uploaded_by: UUID
    created_at: datetime
    updated_at: datetime
    version: int
    dimensions: MediaDimensions | None = None
    checksum: Checksum | None = None
    ready_at: datetime | None = None
    archived_at: datetime | None = None
    intent_expires_at: datetime | None = None
    claimed_at: datetime | None = None
    claim_owner: str | None = None
    attempt_count: int = 0
    failure_code: str | None = None
    detected_mime: MimeType | None = None
    promotion_proof_id: UUID | None = None
    promoted_at: datetime | None = None
    verified_at: datetime | None = None

    def __post_init__(self) -> None:
        require_aware_utc(self.created_at, "created_at")
        require_aware_utc(self.updated_at, "updated_at")
        for field_name in (
            "ready_at",
            "archived_at",
            "intent_expires_at",
            "claimed_at",
            "promoted_at",
            "verified_at",
        ):
            value: datetime | None = getattr(self, field_name)
            if value is not None:
                require_aware_utc(value, field_name)
        if isinstance(self.attempt_count, bool) or not isinstance(self.attempt_count, int):
            raise ValueError("attempt count must be an integer")
        if not 0 <= self.attempt_count <= MAX_UPLOAD_ATTEMPTS:
            raise ValueError("attempt count is out of range")
        if self.promotion_proof_id is not None and not isinstance(self.promotion_proof_id, UUID):
            raise ValueError("promotion proof id must be a UUID")
        if self.detected_mime is not None and not isinstance(self.detected_mime, MimeType):
            raise ValueError("detected mime must be a MimeType")
        if self.version < 1:
            raise ValueError("version must be positive")
        if self.status is MediaStatus.READY and self.ready_at is None:
            raise ValueError("READY media must have ready_at")
        if self.status is MediaStatus.READY and self.byte_size.value <= 0:
            raise ValueError("READY media must have a positive measured byte size")
        if self.status is MediaStatus.READY and (self.dimensions is None or self.checksum is None):
            raise ValueError("READY images require dimensions and checksum")

    def _touch(self, now: datetime) -> datetime:
        moment = require_aware_utc(now, "now")
        self.updated_at = moment
        self.version += 1
        return moment

    def claim(self, now: datetime, *, owner: str, expires_at: datetime) -> None:
        normalized_owner = owner.strip()
        if not normalized_owner:
            raise ValueError("claim owner must not be empty")
        require_aware_utc(expires_at, "expires_at")
        if self.status not in {MediaStatus.UPLOADING, MediaStatus.PROCESSING}:
            raise InvalidMediaTransitionError("only unfinished media can be claimed")
        if self.attempt_count >= MAX_UPLOAD_ATTEMPTS:
            raise InvalidMediaTransitionError("upload attempt budget is exhausted")
        moment = require_aware_utc(now, "now")
        self.claim_owner = normalized_owner
        self.claimed_at = moment
        self.intent_expires_at = expires_at
        self.attempt_count += 1
        self._touch(now)

    def release_claim(self, now: datetime) -> None:
        if self.status not in {MediaStatus.UPLOADING, MediaStatus.PROCESSING}:
            raise InvalidMediaTransitionError("only unfinished media can release a claim")
        self.claim_owner = None
        self.claimed_at = None
        self.intent_expires_at = None
        self._touch(now)

    def mark_processing(self, now: datetime) -> None:
        if self.status is not MediaStatus.UPLOADING:
            raise InvalidMediaTransitionError("only UPLOADING media can enter PROCESSING")
        if self.claim_owner is None:
            raise InvalidMediaTransitionError("unclaimed media cannot enter PROCESSING")
        self.status = MediaStatus.PROCESSING
        self._touch(now)

    def _promote(self, now: datetime, *, evidence: PromotionEvidence) -> None:
        if self.status is MediaStatus.READY:
            raise InvalidMediaTransitionError("READY original cannot be promoted again")
        if evidence.byte_size.value <= 0:
            raise InvalidMediaObjectError("measured byte size must be positive")
        moment = self._touch(now)
        self.mime_type = evidence.detected_mime
        self.byte_size = evidence.byte_size
        self.dimensions = evidence.dimensions
        self.checksum = evidence.checksum
        self.detected_mime = evidence.detected_mime
        self.promotion_proof_id = evidence.proof_id
        self.promoted_at = moment
        self.verified_at = evidence.verified_at
        self.status = MediaStatus.READY
        self.ready_at = moment
        self.archived_at = None
        self.failure_code = None

    def mark_ready(self, now: datetime, *, evidence: PromotionEvidence) -> None:
        if self.status is not MediaStatus.PROCESSING:
            raise InvalidMediaTransitionError("only PROCESSING media can become READY")
        self._promote(now, evidence=evidence)

    def mark_failed(self, now: datetime, *, reason_code: str) -> None:
        normalized_reason = reason_code.strip()
        if not normalized_reason:
            raise ValueError("failure reason code must not be empty")
        if self.status not in {MediaStatus.UPLOADING, MediaStatus.PROCESSING}:
            raise InvalidMediaTransitionError("only unfinished media can fail")
        self.status = MediaStatus.FAILED
        self.failure_code = normalized_reason
        self.claim_owner = None
        self.claimed_at = None
        self.intent_expires_at = None
        self._touch(now)

    def retry(self, now: datetime, *, reason_code: str | None = None) -> None:
        if self.status is not MediaStatus.FAILED:
            raise InvalidMediaTransitionError("only FAILED media can retry")
        if self.attempt_count >= MAX_UPLOAD_ATTEMPTS:
            raise InvalidMediaTransitionError("upload attempt budget is exhausted")
        self.status = MediaStatus.UPLOADING
        self.failure_code = reason_code.strip() if reason_code is not None else None
        self._touch(now)

    def archive(self, now: datetime) -> None:
        if self.status is not MediaStatus.READY:
            raise InvalidMediaTransitionError("only READY media can be archived")
        moment = self._touch(now)
        self.status = MediaStatus.ARCHIVED
        self.archived_at = moment

    def restore(self, now: datetime, *, evidence: PromotionEvidence) -> None:
        if self.status is not MediaStatus.ARCHIVED:
            raise InvalidMediaTransitionError("only ARCHIVED media can be restored")
        self._promote(now, evidence=evidence)

    def update_metadata(self, now: datetime, metadata: MediaMetadata) -> None:
        if self.status in {MediaStatus.PROCESSING, MediaStatus.FAILED}:
            raise InvalidMediaTransitionError("media metadata is read only in this status")
        self.metadata = metadata
        self._touch(now)
