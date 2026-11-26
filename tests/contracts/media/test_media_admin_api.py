from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fps_platform.api.v1.admin.media_routes import MediaRouteServices, get_media_route_services
from fps_platform.modules.identity.domain.value_objects import RoleCode
from fps_platform.modules.media.application.commands.confirm_upload import ConfirmMediaUploadHandler
from fps_platform.modules.media.application.commands.request_upload import (
    MediaIntentIdempotencyStore,
    RequestMediaUploadHandler,
)
from fps_platform.modules.media.application.queries.get_media import get_media
from fps_platform.modules.media.application.queries.list_media import list_media
from fps_platform.modules.media.application.services.promotion import MediaPromotionService
from fps_platform.modules.media.domain.entities import MediaAsset
from fps_platform.modules.media.domain.enums import MediaStatus
from fps_platform.modules.media.infrastructure.fake_storage import (
    STAGING_KEY_PATTERN,
    InMemoryMediaStoragePort,
)
from fps_platform.modules.media.infrastructure.image_inspection import PillowImageInspector
from fps_platform.shared.auth.dependencies import get_current_principal
from fps_platform.shared.domain.clock import FakeClock
from fps_platform.shared.domain.identifiers import Uuid4IdGenerator
from tests.api.identity.test_admin import make_principal
from tests.security.media.fixtures import (
    FakeDatabase,
    FakeMediaAssetRepository,
    FakeUnitOfWork,
    make_asset,
)

MOMENT = datetime(2026, 6, 4, 9, 0, tzinfo=UTC)


class ListingMediaRepository(FakeMediaAssetRepository):
    def add(self, asset: MediaAsset) -> None:
        self._pending[asset.id] = replace(asset)

    def get_by_storage_key(self, storage_key: str) -> MediaAsset | None:
        assets = list(self._pending.values()) + list(self._database.assets.values())
        return next(
            (replace(asset) for asset in assets if str(asset.storage_key) == storage_key), None
        )

    def list(
        self,
        *,
        limit: int,
        offset: int,
        status: MediaStatus | None = None,
    ) -> Sequence[MediaAsset]:
        assets = list(self._pending.values()) + list(self._database.assets.values())
        if status is not None:
            assets = [asset for asset in assets if asset.status is status]
        assets.sort(key=lambda asset: (asset.created_at, asset.id), reverse=True)
        return [replace(asset) for asset in assets[offset : offset + limit]]

    def count(self, *, status: MediaStatus | None = None) -> int:
        assets = list(self._pending.values()) + list(self._database.assets.values())
        if status is not None:
            assets = [asset for asset in assets if asset.status is status]
        return len(assets)


class ListingUnitOfWork(FakeUnitOfWork):
    @property
    def media_assets(self) -> ListingMediaRepository:
        return ListingMediaRepository(self._database, self._pending_assets)


def install_services(
    app: FastAPI,
    database: FakeDatabase,
    clock: FakeClock,
    *,
    roles: tuple[RoleCode, ...] = (RoleCode.SUPER_ADMIN,),
) -> tuple[MediaRouteServices, InMemoryMediaStoragePort]:
    principal = make_principal(roles=roles)
    uow = ListingUnitOfWork(database, clock)
    storage = InMemoryMediaStoragePort(clock)
    promotion = MediaPromotionService(
        storage=storage,
        inspector=PillowImageInspector(clock),
        uow_factory=lambda: ListingUnitOfWork(database, clock),
        clock=clock,
        id_generator=Uuid4IdGenerator(),
    )
    services = MediaRouteServices(
        principal=principal,
        request_upload=RequestMediaUploadHandler(
            uow=uow,
            storage=storage,
            clock=clock,
            id_generator=Uuid4IdGenerator(),
            idempotency=MediaIntentIdempotencyStore(clock),
            max_bytes=10 * 1024 * 1024,
        ),
        confirm_upload=ConfirmMediaUploadHandler(
            uow=uow,
            promotion=promotion,
            clock=clock,
            principal=principal,
        ),
        list_media=lambda query: list_media(uow=uow.media_assets, principal=principal, query=query),
        get_media=lambda query: get_media(uow=uow.media_assets, principal=principal, query=query),
    )
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_media_route_services] = lambda: services
    return services, storage


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/v1/admin/media/upload-intents"),
        ("POST", f"/api/v1/admin/media/{uuid4()}/confirm"),
        ("GET", "/api/v1/admin/media"),
        ("GET", f"/api/v1/admin/media/{uuid4()}"),
    ],
)
def test_media_admin_routes_require_authentication(
    client: TestClient, method: str, path: str
) -> None:
    response = client.request(method, path, json={} if method == "POST" else None)

    assert response.status_code == 401
    assert response.json()["code"] == "AUTHENTICATION_REQUIRED"
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/v1/admin/media/upload-intents"),
        ("POST", f"/api/v1/admin/media/{uuid4()}/confirm"),
    ],
)
def test_media_admin_routes_require_manage_media(app: FastAPI, method: str, path: str) -> None:
    install_services(app, FakeDatabase(), FakeClock(MOMENT), roles=(RoleCode.VIEWER,))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.request(method, path, json={} if method == "POST" else None)

    assert response.status_code == 403
    assert response.json()["code"] == "PERMISSION_DENIED"


def test_media_read_routes_allow_view_media(app: FastAPI) -> None:
    install_services(app, FakeDatabase(), FakeClock(MOMENT), roles=(RoleCode.VIEWER,))

    with TestClient(app, raise_server_exceptions=False) as client:
        listing = client.get("/api/v1/admin/media")
        detail = client.get(f"/api/v1/admin/media/{uuid4()}")

    assert listing.status_code == 200
    assert detail.status_code == 404


def test_create_upload_intent_contract(app: FastAPI) -> None:
    database = FakeDatabase()
    install_services(app, database, FakeClock(MOMENT))
    body = {
        "filename_safe": "photo.jpg",
        "declared_mime": "image/jpeg",
        "declared_size_bytes": 2048,
    }

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/v1/admin/media/upload-intents", json=body)

    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    payload = response.json()
    assert payload["method"] == "PUT"
    assert payload["required_headers"] == {"Content-Type": "image/jpeg"}
    assert "bucket" not in response.text.lower()
    assert "credential" not in response.text.lower()
    asset = database.assets[UUID(payload["media_asset_id"])]
    assert STAGING_KEY_PATTERN.fullmatch(str(asset.storage_key))


def test_create_upload_intent_is_idempotent(app: FastAPI) -> None:
    database = FakeDatabase()
    install_services(app, database, FakeClock(MOMENT))
    body = {
        "filename_safe": "photo.jpg",
        "declared_mime": "image/jpeg",
        "declared_size_bytes": 2048,
    }

    with TestClient(app, raise_server_exceptions=False) as client:
        first = client.post("/api/v1/admin/media/upload-intents", json=body)
        second = client.post("/api/v1/admin/media/upload-intents", json=body)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json() == second.json()
    assert len(database.assets) == 1
    assert len(database.audit_events) == 1


def test_create_upload_intent_error_codes(app: FastAPI) -> None:
    install_services(app, FakeDatabase(), FakeClock(MOMENT))
    cases: list[tuple[dict[str, Any], int, str]] = [
        (
            {
                "filename_safe": "../photo.jpg",
                "declared_mime": "image/jpeg",
                "declared_size_bytes": 10,
            },
            422,
            "MEDIA_INVALID_INPUT",
        ),
        (
            {
                "filename_safe": "photo.avif",
                "declared_mime": "image/avif",
                "declared_size_bytes": 10,
            },
            415,
            "UNSUPPORTED_MEDIA_TYPE",
        ),
        (
            {
                "filename_safe": "photo.jpg",
                "declared_mime": "image/jpeg",
                "declared_size_bytes": 10 * 1024 * 1024 + 1,
            },
            413,
            "PAYLOAD_TOO_LARGE",
        ),
    ]
    with TestClient(app, raise_server_exceptions=False) as client:
        for body, status_code, code in cases:
            response = client.post("/api/v1/admin/media/upload-intents", json=body)
            assert response.status_code == status_code
            assert response.json()["code"] == code


def test_confirm_upload_contract_errors(app: FastAPI) -> None:
    database = FakeDatabase()
    install_services(app, database, FakeClock(MOMENT))
    missing = uuid4()
    asset = make_asset(status=MediaStatus.UPLOADING, version=1)
    database.assets[asset.id] = asset

    with TestClient(app, raise_server_exceptions=False) as client:
        not_found = client.post(
            f"/api/v1/admin/media/{missing}/confirm", json={"expected_version": 1}
        )
        conflict = client.post(
            f"/api/v1/admin/media/{asset.id}/confirm", json={"expected_version": 99}
        )

    assert not_found.status_code == 404
    assert not_found.json()["code"] == "MEDIA_NOT_FOUND"
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "MEDIA_CONFLICT"


def test_media_read_contract_has_no_storage_secrets(app: FastAPI) -> None:
    database = FakeDatabase()
    install_services(app, database, FakeClock(MOMENT))
    asset = make_asset(status=MediaStatus.UPLOADING, version=4)
    database.assets[asset.id] = asset

    with TestClient(app, raise_server_exceptions=False) as client:
        listing = client.get("/api/v1/admin/media", params={"limit": 1, "offset": 0})
        detail = client.get(f"/api/v1/admin/media/{asset.id}")

    assert listing.status_code == 200
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["id"] == str(asset.id)
    assert payload["status"] == "UPLOADING"
    assert listing.json()["total"] == 1
    for text in (listing.text, detail.text):
        assert "bucket" not in text.lower()
        assert "credential" not in text.lower()
        assert "staging/" not in text
        assert "fake-upload" not in text
