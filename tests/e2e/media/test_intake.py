from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from fps_platform.api.v1.admin.media_routes import MediaRouteServices, get_media_route_services
from fps_platform.modules.audit.domain.enums import AuditAction
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
from fps_platform.modules.media.infrastructure.fake_storage import InMemoryMediaStoragePort
from fps_platform.modules.media.infrastructure.image_inspection import PillowImageInspector
from fps_platform.shared.auth.dependencies import get_current_principal
from fps_platform.shared.domain.clock import FakeClock
from fps_platform.shared.domain.identifiers import Uuid4IdGenerator
from tests.api.identity.test_admin import make_principal
from tests.security.media.fixtures import (
    FakeDatabase,
    FakeMediaAssetRepository,
    FakeUnitOfWork,
    valid_jpeg,
)

MOMENT = datetime(2026, 6, 4, 9, 0, tzinfo=UTC)


class E2EMediaRepository(FakeMediaAssetRepository):
    def add(self, asset: MediaAsset) -> None:
        self._pending[asset.id] = replace(asset)

    def get_by_storage_key(self, storage_key: str) -> MediaAsset | None:
        assets = list(self._pending.values()) + list(self._database.assets.values())
        return next(
            (replace(asset) for asset in assets if str(asset.storage_key) == storage_key), None
        )

    def list(
        self, *, limit: int, offset: int, status: MediaStatus | None = None
    ) -> list[MediaAsset]:
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


class E2EUnitOfWork(FakeUnitOfWork):
    @property
    def media_assets(self) -> E2EMediaRepository:
        return E2EMediaRepository(self._database, self._pending_assets)


def test_admin_media_intake_end_to_end(app: FastAPI) -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    principal = make_principal(roles=(RoleCode.SUPER_ADMIN,))
    uow = E2EUnitOfWork(database, clock)
    storage = InMemoryMediaStoragePort(clock)
    promotion = MediaPromotionService(
        storage=storage,
        inspector=PillowImageInspector(clock),
        uow_factory=lambda: E2EUnitOfWork(database, clock),
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

    body_bytes = valid_jpeg()
    with TestClient(app, raise_server_exceptions=False) as client:
        intent = client.post(
            "/api/v1/admin/media/upload-intents",
            json={
                "filename_safe": "cropped.jpg",
                "declared_mime": "image/jpeg",
                "declared_size_bytes": len(body_bytes),
            },
        )
        assert intent.status_code == 201
        intent_payload: dict[str, Any] = intent.json()
        asset_id = UUID(intent_payload["media_asset_id"])

        storage.put_object(database.assets[asset_id].storage_key, body_bytes, "image/jpeg")
        confirm = client.post(
            f"/api/v1/admin/media/{asset_id}/confirm",
            json={"expected_version": intent_payload["version"]},
        )
        assert confirm.status_code == 200
        confirm_payload: dict[str, Any] = confirm.json()
        assert confirm_payload["status"] == "READY"
        assert confirm_payload["checksum_sha256"]

        replay = client.post(
            f"/api/v1/admin/media/{asset_id}/confirm",
            json={"expected_version": 1},
        )
        assert replay.status_code == 200
        assert replay.json() == confirm_payload

        detail = client.get(f"/api/v1/admin/media/{asset_id}")
        assert detail.status_code == 200
        detail_payload: dict[str, Any] = detail.json()
        assert detail_payload["status"] == "READY"
        assert "bucket" not in detail.text.lower()
        assert "staging/" not in detail.text
        assert "fake-upload" not in detail.text

        listing = client.get("/api/v1/admin/media", params={"limit": 10, "offset": 0})
        assert listing.status_code == 200
        assert listing.json()["items"][0]["id"] == str(asset_id)

    actions = [event.action for event in database.audit_events]
    assert AuditAction.MEDIA_UPLOAD_REQUESTED in actions
    assert AuditAction.MEDIA_UPLOAD_CONFIRMED in actions
    assert AuditAction.CONTENT_REVALIDATION_REQUESTED in actions
