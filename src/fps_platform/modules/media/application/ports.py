from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from fps_platform.modules.media.application.dto import DeletionAuthorizationId, InspectionEvidence
from fps_platform.modules.media.domain.entities import MediaAsset
from fps_platform.modules.media.domain.enums import MediaStatus
from fps_platform.modules.media.domain.value_objects import MimeType, StorageKey


class MediaAssetRepository(Protocol):
    def add(self, asset: MediaAsset) -> None: ...

    def get(self, asset_id: UUID) -> MediaAsset | None: ...

    def get_by_storage_key(self, storage_key: str) -> MediaAsset | None: ...

    def list(
        self,
        *,
        limit: int,
        offset: int,
        status: MediaStatus | None = None,
    ) -> Sequence[MediaAsset]: ...

    def count(self, *, status: MediaStatus | None = None) -> int: ...

    def save(self, asset: MediaAsset, *, expected_version: int | None = None) -> None: ...


@dataclass(frozen=True, slots=True)
class UploadIntentRequest:
    key: StorageKey
    content_type: MimeType
    expires_seconds: int


@dataclass(frozen=True, slots=True)
class SignedUploadIntent:
    method: str
    url: str
    expires_at: datetime
    headers: dict[str, str]
    fields: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class ObjectHead:
    exists: bool
    byte_size: int | None = None
    content_type: str | None = None
    etag: str | None = None


@dataclass(frozen=True, slots=True)
class InspectedObject:
    body: bytes
    byte_size: int
    content_type: str | None
    etag: str | None
    truncated: bool
    detected_mime: str | None = None
    width: int | None = None
    height: int | None = None
    checksum: str | None = None


@dataclass(frozen=True, slots=True)
class DeleteObjectRequest:
    key: StorageKey
    authorized_deletion_id: DeletionAuthorizationId


@dataclass(frozen=True, slots=True)
class ResolvePublicUrlRequest:
    key: StorageKey
    readiness_proof_id: UUID


class MediaStoragePort(Protocol):
    def create_upload_intent(self, request: UploadIntentRequest) -> SignedUploadIntent: ...

    def head_object(self, key: StorageKey) -> ObjectHead: ...

    def read_or_inspect_object(self, key: StorageKey, *, max_bytes: int) -> InspectedObject: ...

    def copy_object(self, *, source_key: StorageKey, destination_key: StorageKey) -> None: ...

    def delete_object(self, request: DeleteObjectRequest) -> None: ...

    def resolve_public_url(self, request: ResolvePublicUrlRequest) -> str: ...

    def close(self) -> None: ...


class ImageInspectionPort(Protocol):
    def inspect(self, body: bytes, *, content_type: str | None) -> InspectionEvidence: ...
