from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from re import Pattern, compile
from urllib.parse import quote, urlsplit
from uuid import UUID

from fps_platform.modules.media.application.dto import DeletionAuthorizationId
from fps_platform.modules.media.application.ports import (
    DeleteObjectRequest,
    InspectedObject,
    ObjectHead,
    ResolvePublicUrlRequest,
    SignedUploadIntent,
    UploadIntentRequest,
)
from fps_platform.modules.media.domain.enums import MediaMimeType
from fps_platform.modules.media.domain.exceptions import MediaStoragePermanentError
from fps_platform.modules.media.domain.value_objects import StorageKey
from fps_platform.shared.domain.clock import Clock

STAGING_KEY_PATTERN: Pattern[str] = compile(
    r"^staging/[A-Za-z0-9][A-Za-z0-9._-]{0,127}/"
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
MIN_INTENT_TTL_SECONDS = 60
MAX_INTENT_TTL_SECONDS = 300
NIL_UUID = UUID(int=0)


@dataclass(slots=True)
class _StoredObject:
    body: bytes
    content_type: str


class InMemoryMediaStoragePort:
    def __init__(
        self,
        clock: Clock,
        *,
        public_base_url: str = "https://media.example.test",
        max_bytes: int = 10485760,
    ) -> None:
        self._clock = clock
        self._public_base_url = public_base_url.rstrip("/")
        self._max_bytes = max_bytes
        self._objects: dict[str, _StoredObject] = {}

    def create_upload_intent(self, request: UploadIntentRequest) -> SignedUploadIntent:
        key = _validate_staging_key(request.key)
        content_type = _validate_content_type(request.content_type)
        expires_seconds = _validate_ttl(request.expires_seconds)
        expires_at = self._clock.now() + timedelta(seconds=expires_seconds)
        return SignedUploadIntent(
            method="PUT",
            url=f"{self._public_base_url}/fake-upload/{quote(key, safe='/')}",
            expires_at=expires_at,
            headers={"Content-Type": content_type},
            fields=None,
        )

    def put_object(self, key: StorageKey, body: bytes, content_type: str) -> None:
        key_value = _validate_object_key(key)
        if not key_value.startswith("staging/") and key_value in self._objects:
            raise MediaStoragePermanentError("media destination object already exists")
        self._objects[key_value] = _StoredObject(body=body, content_type=content_type)

    def head_object(self, key: StorageKey) -> ObjectHead:
        stored = self._objects.get(_validate_object_key(key))
        if stored is None:
            return ObjectHead(exists=False)
        return ObjectHead(
            exists=True,
            byte_size=len(stored.body),
            content_type=stored.content_type,
            etag=f'"{len(stored.body):x}"',
        )

    def read_or_inspect_object(self, key: StorageKey, *, max_bytes: int) -> InspectedObject:
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes < 1:
            raise MediaStoragePermanentError("inspection limit must be positive")
        stored = self._objects.get(_validate_object_key(key))
        if stored is None:
            raise MediaStoragePermanentError("media object does not exist")
        limit = min(max_bytes, self._max_bytes)
        body = stored.body[:limit]
        total = len(stored.body)
        return InspectedObject(
            body=body,
            byte_size=total,
            content_type=stored.content_type,
            etag=f'"{total:x}"',
            truncated=total > len(body),
        )

    def copy_object(self, *, source_key: StorageKey, destination_key: StorageKey) -> None:
        source = _validate_object_key(source_key)
        destination = _validate_object_key(destination_key)
        stored = self._objects.get(source)
        if stored is None:
            raise MediaStoragePermanentError("media source object does not exist")
        if destination in self._objects:
            raise MediaStoragePermanentError("media destination object already exists")
        self._objects[destination] = stored
        if not self.head_object(destination_key).exists:
            raise MediaStoragePermanentError("media destination object was not promoted")

    def delete_object(self, request: DeleteObjectRequest) -> None:
        self._objects.pop(_validate_delete_request(request), None)

    def resolve_public_url(self, request: ResolvePublicUrlRequest) -> str:
        key = _validate_resolve_request(request)
        _validate_public_base_url(self._public_base_url)
        return f"{self._public_base_url}/{quote(key, safe='/')}"

    def close(self) -> None:
        return None


def _validate_staging_key(key: object) -> str:
    value = str(key)
    if ".." in value or value.startswith("/") or not value.isascii():
        raise MediaStoragePermanentError("upload intent key is not a server-generated staging key")
    if not STAGING_KEY_PATTERN.fullmatch(value):
        raise MediaStoragePermanentError("upload intent key is not a server-generated staging key")
    nonce = value.rsplit("/", 1)[-1]
    try:
        parsed = UUID(nonce)
    except ValueError:
        raise MediaStoragePermanentError(
            "upload intent key is not a server-generated staging key"
        ) from None
    if str(parsed) != nonce.lower() or parsed == NIL_UUID:
        raise MediaStoragePermanentError("upload intent key is not a server-generated staging key")
    return value


def _validate_content_type(content_type: object) -> str:
    value = str(content_type)
    try:
        MediaMimeType(value)
    except ValueError:
        raise MediaStoragePermanentError("upload intent content type is not supported") from None
    return value


def _validate_ttl(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise MediaStoragePermanentError("upload intent duration is out of range")
    if not MIN_INTENT_TTL_SECONDS <= value <= MAX_INTENT_TTL_SECONDS:
        raise MediaStoragePermanentError("upload intent duration is out of range")
    return value


def _validate_object_key(key: object) -> str:
    value = str(key)
    if (
        not value
        or not value.isascii()
        or ".." in value
        or value.startswith("/")
        or value.endswith("/")
        or "//" in value
        or any(character.isspace() for character in value)
    ):
        raise MediaStoragePermanentError("media key is not usable")
    return value


def _validate_delete_request(request: DeleteObjectRequest) -> str:
    key = _validate_object_key(request.key)
    authorization = getattr(request, "authorized_deletion_id", None)
    if (
        not isinstance(authorization, DeletionAuthorizationId)
        or not isinstance(authorization.value, UUID)
        or authorization.value == NIL_UUID
    ):
        raise MediaStoragePermanentError("deletion is not authorized")
    return key


def _validate_resolve_request(request: ResolvePublicUrlRequest) -> str:
    key = _validate_object_key(request.key)
    proof = getattr(request, "readiness_proof_id", None)
    if not isinstance(proof, UUID) or proof == NIL_UUID:
        raise MediaStoragePermanentError("readiness proof is missing")
    return key


def _validate_public_base_url(public_base_url: str) -> None:
    parsed = urlsplit(public_base_url)
    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise MediaStoragePermanentError("public base URL is not usable")
