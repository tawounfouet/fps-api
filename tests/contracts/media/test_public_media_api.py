from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fps_platform.api.v1.public.media_routes import get_public_media_services
from fps_platform.modules.media.application.dto import (
    MediaNotFoundError,
    MediaStorageUnavailableError,
    PublicMediaUrlResult,
)
from fps_platform.modules.media.application.queries.resolve_public_url import (
    ResolvePublicMediaUrlQuery,
)

PUBLIC_URL = "https://media.example.test/media/asset/original.jpg"


@dataclass(frozen=True, slots=True)
class StubServices:
    resolve: Callable[[ResolvePublicMediaUrlQuery], PublicMediaUrlResult]


def install(
    app: FastAPI,
    *,
    resolve: Callable[[ResolvePublicMediaUrlQuery], PublicMediaUrlResult] | None = None,
) -> None:
    def callback() -> StubServices:
        return StubServices(
            resolve=resolve
            or (lambda query: PublicMediaUrlResult(media_id=query.media_id, url=PUBLIC_URL))
        )

    app.dependency_overrides[get_public_media_services] = cast(Any, callback)


def test_public_media_route_is_unauthenticated_and_cacheable(
    app: FastAPI, client: TestClient
) -> None:
    install(app)
    media_id = uuid4()

    response = client.get(f"/api/v1/media/{media_id}")

    assert response.status_code == 200
    assert response.json() == {"media_id": str(media_id), "url": PUBLIC_URL}
    assert response.headers["cache-control"] == "public, max-age=60"
    assert "no-store" not in response.headers["cache-control"]
    assert "x-correlation-id" in response.headers


def test_public_media_route_returns_404_for_unknown_or_non_ready(
    app: FastAPI, client: TestClient
) -> None:
    def missing(_: ResolvePublicMediaUrlQuery) -> PublicMediaUrlResult:
        raise MediaNotFoundError("media asset was not found")

    install(app, resolve=missing)

    response = client.get(f"/api/v1/media/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["code"] == "MEDIA_NOT_FOUND"


def test_public_media_route_returns_503_for_provider_failure(
    app: FastAPI, client: TestClient
) -> None:
    def unavailable(_: ResolvePublicMediaUrlQuery) -> PublicMediaUrlResult:
        raise MediaStorageUnavailableError("media public URL is unavailable")

    install(app, resolve=unavailable)

    response = client.get(f"/api/v1/media/{uuid4()}")

    assert response.status_code == 503
    assert response.json()["code"] == "DEPENDENCY_UNAVAILABLE"


def test_public_media_contract_has_no_security_requirement(app: FastAPI) -> None:
    schema = app.openapi()
    operation = schema["paths"]["/api/v1/media/{media_id}"]["get"]

    assert operation["operationId"] == "resolvePublicMediaUrl"
    assert "security" not in operation
    assert "Authorization" not in str(operation)
    assert "Cache-Control" in operation["responses"]["200"]["headers"]
    response_schema = schema["components"]["schemas"]["PublicMediaUrlResponse"]
    assert set(response_schema["required"]) == {"media_id", "url"}


def test_public_media_response_never_exposes_signed_query(app: FastAPI, client: TestClient) -> None:
    install(app)

    response = client.get(f"/api/v1/media/{uuid4()}")

    assert "?" not in response.json()["url"]
    assert "#" not in response.json()["url"]
    for token in ("signature", "bucket", "credential", "endpoint", "region"):
        assert token not in response.text.lower()


def test_unknown_public_media_path_remains_404(app: FastAPI, client: TestClient) -> None:
    install(app)

    response = client.get(f"/api/v1/media/{uuid4()}/usage")

    assert response.status_code == 404


@pytest.mark.parametrize("method", ["POST", "PATCH", "DELETE"])
def test_public_media_route_is_read_only(app: FastAPI, client: TestClient, method: str) -> None:
    install(app)

    response = client.request(method, f"/api/v1/media/{uuid4()}")

    assert response.status_code == 405
