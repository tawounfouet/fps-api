from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Protocol
from uuid import UUID

from fps_platform.modules.audit.application.recorder import AuditRecorder
from fps_platform.modules.audit.domain.enums import AuditAction, AuditSource
from fps_platform.modules.media.application.dto import InspectionEvidence, MediaErrorCode
from fps_platform.modules.media.application.ports import (
    ImageInspectionPort,
    MediaAssetRepository,
    MediaStoragePort,
)
from fps_platform.modules.media.domain.enums import MediaStatus
from fps_platform.modules.media.domain.exceptions import MediaStorageError
from fps_platform.modules.media.domain.value_objects import (
    MAX_UPLOAD_ATTEMPTS,
    PromotionEvidence,
    StorageKey,
)
from fps_platform.shared.application.uow import UnitOfWork
from fps_platform.shared.domain.clock import Clock
from fps_platform.shared.domain.errors import ConcurrentModificationError
from fps_platform.shared.domain.identifiers import IdGenerator

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
MAX_IMAGE_DIMENSION = 10_000
BLOCKED_CLIENT_MIME_TYPES = frozenset(
    {
        "image/avif",
        "image/avif-sequence",
        "image/heif",
        "image/heic",
        "image/svg+xml",
        "text/html",
        "application/xhtml+xml",
    }
)
FAILURE_VERSION_CONFLICT = "PROMOTION_VERSION_CONFLICT"
FAILURE_ATTEMPT_BUDGET = "ATTEMPT_BUDGET_EXHAUSTED"
FAILURE_INTERNAL = "PROMOTION_INTERNAL_ERROR"
AUDIT_RESOURCE_TYPE = "MEDIA_ASSET"
AUDIT_READINESS_TYPE = "MEDIA_PROMOTION_VERIFIED"
AUDIT_LOCALE = "fr"


class MediaUnitOfWork(UnitOfWork, Protocol):
    @property
    def media_assets(self) -> MediaAssetRepository: ...

    @property
    def audit_recorder(self) -> AuditRecorder: ...


class MediaInspectionError(ValueError):
    def __init__(self, code: MediaErrorCode | str) -> None:
        self.code = str(code)
        super().__init__(self.code)


class PromotionBlockedError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"promotion blocked: {code}")


class _PromotionFailure(Exception):
    def __init__(self, code: str, cause: Exception | None = None) -> None:
        self.code = code
        self.cause = cause
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class ImageInspectionPolicy:
    max_bytes: int = MAX_IMAGE_BYTES
    max_pixels: int = MAX_IMAGE_PIXELS
    max_dimension: int = MAX_IMAGE_DIMENSION
    blocked_client_mime_types: frozenset[str] = BLOCKED_CLIENT_MIME_TYPES


@dataclass(frozen=True, slots=True)
class PromotionRequest:
    asset_id: UUID
    destination_key: StorageKey
    expected_version: int
    claim_owner: str | None = None
    claim_expires_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class _PreparedPromotion:
    source_key: StorageKey
    version: int


class MediaPromotionService:
    def __init__(
        self,
        *,
        storage: MediaStoragePort,
        inspector: ImageInspectionPort,
        uow_factory: Callable[[], MediaUnitOfWork],
        clock: Clock,
        id_generator: IdGenerator,
        max_bytes: int = MAX_IMAGE_BYTES,
    ) -> None:
        self._storage = storage
        self._inspector = inspector
        self._uow_factory = uow_factory
        self._clock = clock
        self._id_generator = id_generator
        self._max_bytes = max_bytes

    def promote(self, request: PromotionRequest) -> PromotionEvidence:
        try:
            prepared = self._prepare(request)
        except _PromotionFailure as failure:
            self._record_failure(request.asset_id, request.expected_version, failure.code)
            raise PromotionBlockedError(failure.code) from None
        try:
            evidence = self._promote_object(request.destination_key, prepared.source_key)
            return self._finalize(request.asset_id, prepared.version, evidence)
        except _PromotionFailure as failure:
            self._record_failure(request.asset_id, prepared.version, failure.code)
            if failure.cause is not None:
                raise failure.cause from None
            raise PromotionBlockedError(failure.code) from None

    def _prepare(self, request: PromotionRequest) -> _PreparedPromotion:
        with self._uow_factory() as uow:
            asset = uow.media_assets.get(request.asset_id)
            if asset is None:
                raise ConcurrentModificationError("media asset does not exist")
            if asset.version != request.expected_version:
                raise ConcurrentModificationError("media version changed")
            source_key = asset.storage_key
            if asset.status is MediaStatus.UPLOADING:
                if asset.attempt_count >= MAX_UPLOAD_ATTEMPTS:
                    raise _PromotionFailure(FAILURE_ATTEMPT_BUDGET)
                if request.claim_owner is None or request.claim_expires_at is None:
                    raise PromotionBlockedError("PROMOTION_UNCLAIMED")
                asset.claim(
                    self._clock.now(),
                    owner=request.claim_owner,
                    expires_at=request.claim_expires_at,
                )
                asset.mark_processing(self._clock.now())
            elif asset.status is MediaStatus.PROCESSING:
                if request.claim_owner is not None and request.claim_owner != asset.claim_owner:
                    raise ConcurrentModificationError("claim owner does not match")
            else:
                raise ConcurrentModificationError("media is not promotable")
            uow.media_assets.save(asset, expected_version=request.expected_version)
            uow.commit()
            return _PreparedPromotion(source_key=source_key, version=asset.version)

    def _promote_object(
        self, destination_key: StorageKey, source_key: StorageKey
    ) -> PromotionEvidence:
        try:
            head = self._storage.head_object(source_key)
            if not head.exists or head.byte_size is None or head.byte_size <= 0:
                raise _PromotionFailure(MediaErrorCode.MEDIA_CORRUPT.value)
            if head.byte_size > self._max_bytes:
                raise _PromotionFailure(MediaErrorCode.MEDIA_TOO_LARGE.value)
            inspected = self._storage.read_or_inspect_object(source_key, max_bytes=self._max_bytes)
            if inspected.truncated:
                raise _PromotionFailure(MediaErrorCode.MEDIA_TOO_LARGE.value)
            if (
                inspected.byte_size != head.byte_size
                or len(inspected.body) != inspected.byte_size
                or not inspected.body
            ):
                raise _PromotionFailure(MediaErrorCode.MEDIA_CORRUPT.value)
            inspection = self._inspect(inspected.body, inspected.content_type)
            if inspection.byte_size.value != inspected.byte_size:
                raise _PromotionFailure(MediaErrorCode.MEDIA_CORRUPT.value)
            self._storage.copy_object(source_key=source_key, destination_key=destination_key)
            final_head = self._storage.head_object(destination_key)
            if (
                not final_head.exists
                or final_head.byte_size != inspection.byte_size.value
                or final_head.byte_size > self._max_bytes
            ):
                raise _PromotionFailure(MediaErrorCode.MEDIA_CORRUPT.value)
            final = self._storage.read_or_inspect_object(destination_key, max_bytes=self._max_bytes)
            if (
                final.truncated
                or final.byte_size != final_head.byte_size
                or len(final.body) != final.byte_size
                or sha256(final.body).hexdigest() != inspection.checksum.digest
            ):
                raise _PromotionFailure(MediaErrorCode.MEDIA_CORRUPT.value)
            return PromotionEvidence(
                proof_id=self._id_generator.new_id(),
                storage_key=destination_key,
                detected_mime=inspection.detected_mime,
                byte_size=inspection.byte_size,
                dimensions=inspection.dimensions,
                checksum=inspection.checksum,
                verified_at=self._clock.now(),
            )
        except MediaStorageError as exc:
            code = (
                MediaErrorCode.STORAGE_TEMPORARY_FAILURE.value
                if exc.retryable
                else MediaErrorCode.MEDIA_STILL_IN_USE.value
                if "already exists" in str(exc).lower()
                else FAILURE_INTERNAL
            )
            raise _PromotionFailure(code, exc) from None

    def _inspect(self, body: bytes, content_type: str | None) -> InspectionEvidence:
        try:
            return self._inspector.inspect(body, content_type=content_type)
        except MediaInspectionError as exc:
            raise _PromotionFailure(exc.code, exc) from None
        except Exception as exc:
            raise _PromotionFailure(FAILURE_INTERNAL, exc) from None

    def _finalize(
        self, asset_id: UUID, version: int, evidence: PromotionEvidence
    ) -> PromotionEvidence:
        try:
            with self._uow_factory() as uow:
                asset = uow.media_assets.get(asset_id)
                if asset is None or asset.version != version:
                    raise _PromotionFailure(FAILURE_VERSION_CONFLICT)
                if asset.status is not MediaStatus.PROCESSING:
                    raise _PromotionFailure(FAILURE_VERSION_CONFLICT)
                asset.mark_ready(self._clock.now(), evidence=evidence)
                uow.media_assets.save(asset, expected_version=version)
                uow.audit_recorder.record(
                    action=AuditAction.CONTENT_REVALIDATION_REQUESTED,
                    resource_type=AUDIT_RESOURCE_TYPE,
                    resource_id=asset.id,
                    metadata={"resource_type": AUDIT_READINESS_TYPE, "locale": AUDIT_LOCALE},
                    source=AuditSource.WORKER,
                )
                uow.commit()
            return evidence
        except _PromotionFailure:
            raise
        except Exception as exc:
            raise _PromotionFailure(FAILURE_INTERNAL, exc) from None

    def _record_failure(self, asset_id: UUID, version: int, code: str) -> None:
        try:
            with self._uow_factory() as uow:
                asset = uow.media_assets.get(asset_id)
                if asset is None or asset.version != version:
                    return
                if asset.status not in {MediaStatus.UPLOADING, MediaStatus.PROCESSING}:
                    return
                asset.mark_failed(self._clock.now(), reason_code=code)
                uow.media_assets.save(asset, expected_version=version)
                uow.commit()
        except Exception as exc:
            raise PromotionBlockedError(code) from exc
