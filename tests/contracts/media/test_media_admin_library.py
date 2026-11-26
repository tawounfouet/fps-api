from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fps_platform.api.v1.admin.media_routes import MediaRouteServices, get_media_route_services
from fps_platform.modules.identity.domain.value_objects import RoleCode
from fps_platform.modules.media.application.commands.archive_media import ArchiveMediaHandler
from fps_platform.modules.media.application.commands.restore_media import RestoreMediaHandler
from fps_platform.modules.media.application.commands.update_metadata import UpdateMetadataHandler
from fps_platform.modules.media.application.queries.get_media import get_media
from fps_platform.modules.media.application.services.usage_sources import MediaUsageLookup
from fps_platform.modules.media.domain.entities import MediaAsset
from fps_platform.modules.media.domain.enums import ChecksumAlgorithm, MediaStatus
from fps_platform.modules.media.domain.value_objects import (
    ByteSize,
    Checksum,
    LocalizedTextMap,
    MediaDimensions,
    MediaMetadata,
    MediaText,
    MimeType,
    OriginalFileName,
)
from fps_platform.modules.media.infrastructure.fake_storage import InMemoryMediaStoragePort
from fps_platform.shared.auth.dependencies import get_current_principal
from fps_platform.shared.domain.clock import FakeClock
from tests.api.identity.test_admin import make_principal
from tests.security.media.fixtures import FINAL_KEY, MOMENT, FakeDatabase, FakeUnitOfWork

FINAL_BODY = b"library-bytes"


def make_asset(*, status: MediaStatus = MediaStatus.READY) -> MediaAsset:
    return MediaAsset(
        id=uuid4(),
        storage_key=FINAL_KEY,
        original_filename=OriginalFileName("photo.jpg"),
        mime_type=MimeType("image/jpeg"),
        byte_size=ByteSize(len(FINAL_BODY)),
        status=status,
        metadata=MediaMetadata(
            title=MediaText("Titre"),
            alt_texts=LocalizedTextMap(fr=MediaText("Texte FR"), en=MediaText("English alt")),
        ),
        uploaded_by=uuid4(),
        created_at=MOMENT,
        updated_at=datetime(2026, 6, 4, 10, tzinfo=UTC),
        version=3,
        dimensions=MediaDimensions(12, 8),
        checksum=Checksum(ChecksumAlgorithm.SHA256, sha256(FINAL_BODY).hexdigest()),
        ready_at=MOMENT,
        promoted_at=MOMENT,
        verified_at=MOMENT,
        promotion_proof_id=uuid4(),
        detected_mime=MimeType("image/jpeg"),
    )


def install_services(
    app: FastAPI,
    database: FakeDatabase,
    clock: FakeClock,
    *,
    roles: tuple[RoleCode, ...] = (RoleCode.SUPER_ADMIN,),
) -> tuple[MediaRouteServices, InMemoryMediaStoragePort]:
    principal = make_principal(roles=roles)
    uow = FakeUnitOfWork(database, clock)
    storage = InMemoryMediaStoragePort(clock)
    services = MediaRouteServices(
        principal=principal,
        request_upload=cast(Any, object()),
        confirm_upload=cast(Any, object()),
        list_media=cast(Any, object()),
        get_media=lambda query: get_media(uow=uow.media_assets, principal=principal, query=query),
        update_metadata=UpdateMetadataHandler(uow=uow, clock=clock, principal=principal),
        archive_media=ArchiveMediaHandler(uow=uow, clock=clock, principal=principal),
        restore_media=RestoreMediaHandler(
            uow=uow, storage=storage, clock=clock, principal=principal
        ),
        usage_lookup=MediaUsageLookup(assets=uow.media_assets),
    )
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_media_route_services] = lambda: services
    return services, storage


def seed_final(storage: InMemoryMediaStoragePort) -> None:
    storage.put_object(FINAL_KEY, FINAL_BODY, "image/jpeg")


def test_media_library_routes_are_exposed_without_delete(app: FastAPI) -> None:
    schema = app.openapi()
    paths = schema["paths"]
    expected = {
        "/api/v1/admin/media/{media_id}": "patch",
        "/api/v1/admin/media/{media_id}/archive": "post",
        "/api/v1/admin/media/{media_id}/restore": "post",
        "/api/v1/admin/media/{media_id}/usage": "get",
    }
    for path, method in expected.items():
        assert method in paths[path]
    media_operations = {
        method
        for path, operations in paths.items()
        if path.startswith("/api/v1/admin/media")
        for method in operations
    }
    assert "delete" not in media_operations


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("PATCH", f"/api/v1/admin/media/{uuid4()}", {"expected_version": 3}),
        ("POST", f"/api/v1/admin/media/{uuid4()}/archive", {}),
        ("POST", f"/api/v1/admin/media/{uuid4()}/restore", {}),
        ("GET", f"/api/v1/admin/media/{uuid4()}/usage", None),
    ],
)
def test_new_media_routes_require_authentication(
    client: TestClient, method: str, path: str, body: dict[str, Any] | None
) -> None:
    response = client.request(method, path, json=body)

    assert response.status_code == 401
    assert response.json()["code"] == "AUTHENTICATION_REQUIRED"
    assert response.headers["cache-control"] == "no-store"


def test_manage_routes_require_manage_media_but_usage_allows_view_media(app: FastAPI) -> None:
    install_services(app, FakeDatabase(), FakeClock(MOMENT), roles=(RoleCode.VIEWER,))
    asset = make_asset()
    missing = uuid4()

    with TestClient(app, raise_server_exceptions=False) as client:
        patch = client.patch(
            f"/api/v1/admin/media/{missing}",
            json={"expected_version": 1, "alt_texts": {"fr": "Texte"}},
        )
        archive = client.post(f"/api/v1/admin/media/{missing}/archive", json={})
        restore = client.post(f"/api/v1/admin/media/{missing}/restore", json={})
        usage = client.get(f"/api/v1/admin/media/{asset.id}/usage")

    assert patch.status_code == 403
    assert archive.status_code == 403
    assert restore.status_code == 403
    assert usage.status_code == 404


@pytest.mark.parametrize(
    ("method", "suffix", "body"),
    [
        ("PATCH", "", {"expected_version": 3, "alt_texts": {"fr": "Texte"}}),
        ("POST", "/archive", {}),
        ("POST", "/restore", {}),
        ("GET", "/usage", None),
    ],
)
def test_new_media_routes_report_missing_asset(
    app: FastAPI, method: str, suffix: str, body: dict[str, Any] | None
) -> None:
    install_services(app, FakeDatabase(), FakeClock(MOMENT))
    missing = uuid4()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.request(method, f"/api/v1/admin/media/{missing}{suffix}", json=body)

    assert response.status_code == 404
    assert response.json()["code"] == "MEDIA_NOT_FOUND"


def test_patch_contract_is_partial_audited_and_versioned(app: FastAPI) -> None:
    database = FakeDatabase()
    install_services(app, database, FakeClock(MOMENT))
    asset = make_asset()
    database.assets[asset.id] = asset

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.patch(
            f"/api/v1/admin/media/{asset.id}",
            json={"expected_version": 3, "alt_texts": {"en": "Updated English alt"}},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == 4
    assert payload["status"] == "READY"
    updated = database.assets[asset.id]
    assert updated.metadata.alt_texts.as_mapping() == {
        "fr": "Texte FR",
        "en": "Updated English alt",
    }
    assert len(database.audit_events) == 1
    assert database.audit_events[0].metadata == {"from_version": 3, "to_version": 4}
    assert response.headers["cache-control"] == "no-store"


def test_patch_reports_conflict_and_validation_errors(app: FastAPI) -> None:
    database = FakeDatabase()
    install_services(app, database, FakeClock(MOMENT))
    asset = make_asset()
    database.assets[asset.id] = asset

    with TestClient(app, raise_server_exceptions=False) as client:
        conflict = client.patch(
            f"/api/v1/admin/media/{asset.id}",
            json={"expected_version": 99, "alt_texts": {"fr": "Texte"}},
        )
        bad_locale = client.patch(
            f"/api/v1/admin/media/{asset.id}",
            json={"expected_version": 3, "alt_texts": {"de": "Nein"}},
        )
        extra = client.patch(
            f"/api/v1/admin/media/{asset.id}",
            json={"expected_version": 3, "storage_key": "media/other.jpg"},
        )
        malformed = client.patch(
            f"/api/v1/admin/media/{asset.id}",
            content=b"{",
            headers={"Content-Type": "application/json"},
        )

    assert conflict.status_code == 409
    assert conflict.json()["code"] == "MEDIA_CONFLICT"
    assert bad_locale.status_code == 422
    assert bad_locale.json()["code"] == "MEDIA_INVALID_INPUT"
    assert extra.status_code == 422
    assert malformed.status_code == 400
    assert malformed.json()["code"] == "MALFORMED_JSON"
    assert database.commit_calls == 0


def test_archive_usage_and_restore_flow_keeps_binary(app: FastAPI) -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    _, storage = install_services(app, database, clock)
    asset = make_asset()
    database.assets[asset.id] = asset
    seed_final(storage)

    with TestClient(app, raise_server_exceptions=False) as client:
        archived = client.post(
            f"/api/v1/admin/media/{asset.id}/archive", json={"expected_version": 3}
        )
        usage = client.get(f"/api/v1/admin/media/{asset.id}/usage")
        restored = client.post(
            f"/api/v1/admin/media/{asset.id}/restore", json={"expected_version": 4}
        )

    assert archived.status_code == 200
    assert archived.json()["status"] == "ARCHIVED"
    assert usage.status_code == 200
    assert usage.json()["coverage_status"] == "PARTIAL"
    assert usage.json()["found"] is False
    assert usage.json()["sources"] == []
    assert restored.status_code == 200
    assert restored.json()["status"] == "READY"
    assert storage.head_object(FINAL_KEY).exists
    assert database.assets[asset.id].promotion_proof_id == asset.promotion_proof_id
    assert [event.action.value for event in database.audit_events] == [
        "MEDIA_ARCHIVED",
        "MEDIA_RESTORED",
    ]


def test_media_library_responses_carry_no_storage_material(app: FastAPI) -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    _, storage = install_services(app, database, clock)
    asset = make_asset()
    database.assets[asset.id] = asset
    seed_final(storage)

    with TestClient(app, raise_server_exceptions=False) as client:
        responses = [
            client.patch(
                f"/api/v1/admin/media/{asset.id}",
                json={"expected_version": 3, "title": "Titre public"},
            ),
            client.get(f"/api/v1/admin/media/{asset.id}/usage"),
        ]

    for response in responses:
        assert response.status_code == 200
        lowered = response.text.lower()
        for token in ("bucket", "credential", "secret", "x-amz", "http"):
            assert token not in lowered


def test_media_library_routes_declare_error_responses(app: FastAPI) -> None:
    schema = app.openapi()
    paths = schema["paths"]
    expected_codes = {"401", "403", "404", "409", "413", "415", "422", "503"}
    for path, method in (
        ("/api/v1/admin/media/{media_id}", "patch"),
        ("/api/v1/admin/media/{media_id}/archive", "post"),
        ("/api/v1/admin/media/{media_id}/restore", "post"),
        ("/api/v1/admin/media/{media_id}/usage", "get"),
    ):
        declared = set(paths[path][method]["responses"])
        assert expected_codes <= declared
