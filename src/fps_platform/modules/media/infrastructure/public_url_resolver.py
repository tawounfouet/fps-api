from __future__ import annotations

from re import Pattern, compile
from urllib.parse import urlsplit
from uuid import UUID

from fps_platform.modules.media.application.ports import (
    MediaStoragePort,
    ResolvePublicUrlRequest,
)
from fps_platform.modules.media.domain.exceptions import MediaStoragePermanentError
from fps_platform.modules.media.domain.value_objects import StorageKey
from fps_platform.observability.metrics import normalize_provider_code

MAX_PUBLIC_URL_LENGTH = 2048
SIGNED_MARKERS: tuple[str, ...] = (
    "x-amz-signature",
    "signature=",
    "se=",
    "sp=",
    "sig=",
)
SIGNED_QUERY_PATTERN: Pattern[str] = compile(
    r"(?i)[?&](?:X-Amz-Signature|signature|sig|se|sp)=",
)


class StorageBackedPublicUrlResolver:
    def __init__(self, *, storage: MediaStoragePort) -> None:
        self._storage = storage

    @property
    def provider_code(self) -> str:
        return normalize_provider_code(getattr(self._storage, "provider_code", None))

    def resolve(self, *, media_id: UUID, storage_key: str, readiness_proof_id: UUID) -> str:
        key = self._final_key(media_id, storage_key)
        request = ResolvePublicUrlRequest(key=key, readiness_proof_id=readiness_proof_id)
        return self._validate(self._storage.resolve_public_url(request))

    def _final_key(self, media_id: UUID, storage_key: str) -> StorageKey:
        key = StorageKey(storage_key)
        if not str(key).startswith("media/") or media_id.hex not in str(key).replace("-", ""):
            raise MediaStoragePermanentError("media public path is not usable")
        return key

    def _validate(self, url: str) -> str:
        if not isinstance(url, str) or not url or len(url) > MAX_PUBLIC_URL_LENGTH:
            raise MediaStoragePermanentError("public URL is not usable")
        lowered = url.lower()
        if any(marker in lowered for marker in SIGNED_MARKERS) or SIGNED_QUERY_PATTERN.search(url):
            raise MediaStoragePermanentError("public URL is not usable")
        parsed = urlsplit(url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise MediaStoragePermanentError("public URL is not usable")
        return url
