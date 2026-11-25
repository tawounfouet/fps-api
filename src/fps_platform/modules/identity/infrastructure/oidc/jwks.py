from __future__ import annotations

import json
import time
from threading import Lock
from typing import Any, Protocol
from urllib.request import Request, urlopen

from fps_platform.modules.identity.domain.exceptions import TokenValidationError


class JwksFetcher(Protocol):
    def fetch(self) -> dict[str, Any]: ...


class HttpJwksFetcher:
    def __init__(self, url: str, *, timeout_seconds: int = 5) -> None:
        self.url = url
        self.timeout_seconds = timeout_seconds

    def fetch(self) -> dict[str, Any]:
        request = Request(self.url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=self.timeout_seconds) as response:
            payload = json.load(response)
        if not isinstance(payload, dict):
            raise TokenValidationError("JWKS payload is invalid")
        return payload


class JwksCache:
    def __init__(
        self,
        fetcher: JwksFetcher,
        *,
        ttl_seconds: int,
        monotonic: Any = time.monotonic,
    ) -> None:
        self.fetcher = fetcher
        self.ttl_seconds = ttl_seconds
        self.monotonic = monotonic
        self._keys: list[dict[str, Any]] = []
        self._loaded_at: float | None = None
        self._lock = Lock()

    def keys(self, *, refresh: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            if (
                not refresh
                and self._loaded_at is not None
                and self.monotonic() - self._loaded_at < self.ttl_seconds
            ):
                return list(self._keys)
            payload = self.fetcher.fetch()
            keys = payload.get("keys")
            if not isinstance(keys, list):
                raise TokenValidationError("JWKS keys are invalid")
            validated = [key for key in keys if isinstance(key, dict) and key]
            if not validated:
                raise TokenValidationError("JWKS keys are empty")
            self._keys = validated
            self._loaded_at = self.monotonic()
            return list(self._keys)
