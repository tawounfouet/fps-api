from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from fps_platform.modules.media.domain.entities import MediaAsset
from fps_platform.modules.media.domain.enums import MediaCoverageStatus, MediaStatus
from fps_platform.modules.media.domain.value_objects import (
    ByteSize,
    Checksum,
    MediaDimensions,
    MimeType,
    PromotionEvidence,
    StorageKey,
)

__all__ = [
    "DeletionAuthorizationId",
    "InspectionEvidence",
    "MediaConfirmResult",
    "MediaConflictError",
    "MediaErrorCode",
    "MediaInvalidInputError",
    "MediaListResult",
    "MediaNotFoundError",
    "MediaPayloadTooLargeError",
    "MediaReadModel",
    "MediaSourceCoverage",
    "MediaStillInUseError",
    "MediaStorageUnavailableError",
    "MediaUnsupportedTypeError",
    "MediaUploadIntentResult",
    "MediaUsageResult",
    "MediaUsageSourceResult",
    "PromotionEvidence",
    "PublicMediaUrlResult",
    "PublicUsageContract",
    "ReconciliationFinding",
    "ReconciliationFindingCode",
    "ReconciliationReport",
    "UploadIntentLease",
    "project_media",
]


class MediaErrorCode(StrEnum):
    MEDIA_TOO_LARGE = "MEDIA_TOO_LARGE"
    UNSUPPORTED_MEDIA_TYPE = "UNSUPPORTED_MEDIA_TYPE"
    MEDIA_CORRUPT = "MEDIA_CORRUPT"
    STORAGE_TEMPORARY_FAILURE = "STORAGE_TEMPORARY_FAILURE"
    MEDIA_STILL_IN_USE = "MEDIA_STILL_IN_USE"


@dataclass(frozen=True, slots=True)
class DeletionAuthorizationId:
    value: UUID


@dataclass(frozen=True, slots=True)
class InspectionEvidence:
    detected_mime: MimeType
    byte_size: ByteSize
    dimensions: MediaDimensions
    checksum: Checksum
    inspected_at: datetime


@dataclass(frozen=True, slots=True)
class UploadIntentLease:
    key: StorageKey
    content_type: MimeType
    expires_at: datetime
    max_bytes: int
    attempt_count: int = 0


@dataclass(frozen=True, slots=True)
class MediaSourceCoverage:
    source: str
    status: MediaCoverageStatus = MediaCoverageStatus.PARTIAL


class MediaNotFoundError(Exception):
    pass


class MediaConflictError(Exception):
    pass


class MediaStillInUseError(MediaConflictError):
    def __init__(self, message: str = "media is still in use") -> None:
        self.code = str(MediaErrorCode.MEDIA_STILL_IN_USE)
        super().__init__(message)


class MediaInvalidInputError(ValueError):
    pass


class MediaUnsupportedTypeError(ValueError):
    pass


class MediaPayloadTooLargeError(ValueError):
    pass


class MediaStorageUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MediaUploadIntentResult:
    media_asset_id: UUID
    intent_id: UUID
    method: str
    upload_url: str
    required_headers: dict[str, str]
    expires_at: datetime
    version: int


@dataclass(frozen=True, slots=True)
class MediaConfirmResult:
    media_asset_id: UUID
    status: MediaStatus
    version: int
    checksum_sha256: str | None = None
    failure_code: str | None = None


@dataclass(frozen=True, slots=True)
class MediaReadModel:
    id: UUID
    status: MediaStatus
    version: int
    original_filename: str
    mime_type: str
    byte_size: int
    width: int | None
    height: int | None
    checksum_sha256: str | None
    failure_code: str | None
    created_at: datetime
    updated_at: datetime
    ready_at: datetime | None


@dataclass(frozen=True, slots=True)
class MediaListResult:
    items: tuple[MediaReadModel, ...]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class MediaUsageSourceResult:
    source: str
    coverage_status: MediaCoverageStatus
    found: bool
    reference_count: int


@dataclass(frozen=True, slots=True)
class MediaUsageResult:
    media_id: UUID
    coverage_status: MediaCoverageStatus
    found: bool
    sources: tuple[MediaUsageSourceResult, ...]


@dataclass(frozen=True, slots=True)
class PublicMediaUrlResult:
    media_id: UUID
    url: str
    cache_control: str = "public, max-age=60"


@dataclass(frozen=True, slots=True)
class PublicUsageContract:
    media_id: UUID
    locale: str
    decorative: bool
    alt_text: str | None
    title: str | None


class ReconciliationFindingCode(StrEnum):
    UPLOADING_EXPIRED = "UPLOADING_EXPIRED"
    ATTEMPT_BUDGET_EXHAUSTED = "ATTEMPT_BUDGET_EXHAUSTED"
    PROCESSING_STALLED = "PROCESSING_STALLED"
    MISSING_OBJECT = "MISSING_OBJECT"
    ORPHAN_OBJECT = "ORPHAN_OBJECT"
    SIZE_MISMATCH = "SIZE_MISMATCH"
    STORAGE_UNAVAILABLE = "STORAGE_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class ReconciliationFinding:
    code: ReconciliationFindingCode
    media_id: UUID | None = None
    observed: int | None = None
    recommended_status: MediaStatus | None = None


@dataclass(frozen=True, slots=True)
class ReconciliationReport:
    dry_run: bool
    scanned_assets: int
    scanned_objects: int
    findings: tuple[ReconciliationFinding, ...]


def project_media(asset: MediaAsset) -> MediaReadModel:
    return MediaReadModel(
        id=asset.id,
        status=asset.status,
        version=asset.version,
        original_filename=str(asset.original_filename),
        mime_type=str(asset.mime_type),
        byte_size=asset.byte_size.value,
        width=asset.dimensions.width if asset.dimensions is not None else None,
        height=asset.dimensions.height if asset.dimensions is not None else None,
        checksum_sha256=asset.checksum.digest if asset.checksum is not None else None,
        failure_code=asset.failure_code,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        ready_at=asset.ready_at,
    )
