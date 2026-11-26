from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from json import dumps
from uuid import UUID

from fps_platform.modules.audit.domain.enums import AuditAction, AuditSource
from fps_platform.modules.identity.domain.exceptions import AuthorizationError
from fps_platform.modules.identity.domain.value_objects import PermissionCode
from fps_platform.modules.media.application.dto import (
    MediaInvalidInputError,
    MediaPayloadTooLargeError,
    MediaStorageUnavailableError,
    MediaUnsupportedTypeError,
    MediaUploadIntentResult,
)
from fps_platform.modules.media.application.ports import (
    MediaStoragePort,
    UploadIntentRequest,
)
from fps_platform.modules.media.application.services.promotion import MediaUnitOfWork
from fps_platform.modules.media.domain.entities import MediaAsset
from fps_platform.modules.media.domain.enums import MediaStatus
from fps_platform.modules.media.domain.exceptions import MediaStorageError
from fps_platform.modules.media.domain.value_objects import (
    ByteSize,
    MediaMetadata,
    MimeType,
    OriginalFileName,
    StorageKey,
)
from fps_platform.shared.auth.principal import CurrentPrincipal
from fps_platform.shared.domain.clock import Clock
from fps_platform.shared.domain.identifiers import IdGenerator

MAX_INTENT_TTL_SECONDS = 300
MIN_INTENT_TTL_SECONDS = 60
MAX_IDEMPOTENCY_ENTRIES = 512
AUDIT_RESOURCE_TYPE = "MEDIA_ASSET"


@dataclass(frozen=True, slots=True)
class RequestMediaUploadCommand:
    filename_safe: str
    declared_mime: str
    declared_size_bytes: int


class MediaIntentIdempotencyStore:
    def __init__(
        self,
        clock: Clock,
        *,
        ttl_seconds: int = MAX_INTENT_TTL_SECONDS,
        max_entries: int = MAX_IDEMPOTENCY_ENTRIES,
    ) -> None:
        self._clock = clock
        self._ttl_seconds = ttl_seconds
        self._max_entries = max_entries
        self._entries: OrderedDict[str, MediaUploadIntentResult] = OrderedDict()
        self._created_at: dict[str, datetime] = {}

    def get(self, fingerprint: str) -> MediaUploadIntentResult | None:
        now = self._clock.now()
        expired = [
            key
            for key, created_at in self._created_at.items()
            if (now - created_at).total_seconds() >= self._ttl_seconds
        ]
        for key in expired:
            self._forget(key)
        result = self._entries.get(fingerprint)
        if result is not None:
            self._entries.move_to_end(fingerprint)
        return result

    def put(self, fingerprint: str, result: MediaUploadIntentResult) -> None:
        while len(self._entries) >= self._max_entries:
            oldest = next(iter(self._entries))
            self._forget(oldest)
        self._entries[fingerprint] = result
        self._created_at[fingerprint] = self._clock.now()
        self._entries.move_to_end(fingerprint)

    def _forget(self, fingerprint: str) -> None:
        self._entries.pop(fingerprint, None)
        self._created_at.pop(fingerprint, None)


def fingerprint_for(command: RequestMediaUploadCommand, *, actor_id: UUID) -> str:
    canonical = dumps(
        [
            str(actor_id),
            command.filename_safe,
            command.declared_mime.strip().lower(),
            command.declared_size_bytes,
        ],
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


class RequestMediaUploadHandler:
    def __init__(
        self,
        *,
        uow: MediaUnitOfWork,
        storage: MediaStoragePort,
        clock: Clock,
        id_generator: IdGenerator,
        idempotency: MediaIntentIdempotencyStore,
        max_bytes: int,
        ttl_seconds: int = MAX_INTENT_TTL_SECONDS,
    ) -> None:
        self._uow = uow
        self._storage = storage
        self._clock = clock
        self._id_generator = id_generator
        self._idempotency = idempotency
        self._max_bytes = max_bytes
        self._ttl_seconds = min(ttl_seconds, MAX_INTENT_TTL_SECONDS)

    def handle(
        self, command: RequestMediaUploadCommand, *, principal: CurrentPrincipal
    ) -> MediaUploadIntentResult:
        if PermissionCode.MANAGE_MEDIA not in principal.permissions:
            raise AuthorizationError("PERMISSION_DENIED")

        now = self._clock.now()
        fingerprint = fingerprint_for(command, actor_id=principal.user_id)
        replay = self._idempotency.get(fingerprint)
        if replay is not None:
            return replay

        filename = self._parse_filename(command.filename_safe)
        mime_type = self._parse_mime(command.declared_mime)
        byte_size = self._parse_size(command.declared_size_bytes)

        asset_id = self._id_generator.new_id()
        intent_id = self._id_generator.new_id()
        staging_key = _staging_key(now, asset_id=asset_id, intent_id=intent_id)
        expires_seconds = self._ttl_seconds
        expires_at = now + timedelta(seconds=expires_seconds)
        asset = MediaAsset(
            id=asset_id,
            storage_key=staging_key,
            original_filename=filename,
            mime_type=mime_type,
            byte_size=byte_size,
            status=MediaStatus.UPLOADING,
            metadata=MediaMetadata(),
            uploaded_by=principal.user_id,
            created_at=now,
            updated_at=now,
            version=1,
            intent_expires_at=expires_at,
        )
        try:
            intent = self._storage.create_upload_intent(
                UploadIntentRequest(
                    key=staging_key,
                    content_type=mime_type,
                    expires_seconds=expires_seconds,
                )
            )
        except MediaStorageError:
            raise MediaStorageUnavailableError("upload intent could not be created") from None

        self._uow.media_assets.add(asset)
        self._uow.audit_recorder.record(
            action=AuditAction.MEDIA_UPLOAD_REQUESTED,
            resource_type=AUDIT_RESOURCE_TYPE,
            resource_id=asset.id,
            metadata={
                "media_asset_status": asset.status.value,
                "declared_mime": str(mime_type),
            },
            source=AuditSource.APPLICATION,
        )
        self._uow.commit()

        result = MediaUploadIntentResult(
            media_asset_id=asset.id,
            intent_id=intent_id,
            method=intent.method,
            upload_url=intent.url,
            required_headers=dict(intent.headers),
            expires_at=intent.expires_at,
            version=asset.version,
        )
        self._idempotency.put(fingerprint, result)
        return result

    def _parse_filename(self, value: str) -> OriginalFileName:
        try:
            return OriginalFileName(value)
        except ValueError:
            raise MediaInvalidInputError("filename is not safe") from None

    def _parse_mime(self, value: str) -> MimeType:
        try:
            return MimeType(value)
        except ValueError:
            raise MediaUnsupportedTypeError("MIME type is not supported") from None

    def _parse_size(self, value: int) -> ByteSize:
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise MediaInvalidInputError("declared size must be a positive integer")
        if value > self._max_bytes:
            raise MediaPayloadTooLargeError("declared size exceeds the media budget")
        return ByteSize(value)


def _staging_key(now: datetime, *, asset_id: UUID, intent_id: UUID) -> StorageKey:
    prefix = f"{now:%Y}.{now:%m}.{asset_id.hex}"
    return StorageKey(f"staging/{prefix}/{intent_id}")
