from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from fps_platform.modules.audit.domain.enums import AuditAction
from fps_platform.modules.identity.domain.exceptions import AuthorizationError
from fps_platform.modules.identity.domain.value_objects import RoleCode
from fps_platform.modules.media.application.commands.request_upload import (
    MAX_INTENT_TTL_SECONDS,
    MediaIntentIdempotencyStore,
    RequestMediaUploadCommand,
    RequestMediaUploadHandler,
)
from fps_platform.modules.media.application.dto import (
    MediaInvalidInputError,
    MediaPayloadTooLargeError,
    MediaStorageUnavailableError,
    MediaUnsupportedTypeError,
)
from fps_platform.modules.media.application.ports import SignedUploadIntent
from fps_platform.modules.media.domain.entities import MediaAsset
from fps_platform.modules.media.domain.enums import MediaStatus
from fps_platform.modules.media.domain.exceptions import MediaStorageTransientError
from fps_platform.modules.media.infrastructure.fake_storage import (
    STAGING_KEY_PATTERN,
    InMemoryMediaStoragePort,
)
from fps_platform.shared.auth.principal import CurrentPrincipal
from fps_platform.shared.domain.clock import FakeClock
from fps_platform.shared.domain.identifiers import Uuid4IdGenerator
from tests.api.identity.test_admin import make_principal
from tests.security.media.fixtures import (
    FakeDatabase,
    FakeMediaAssetRepository,
    FakeUnitOfWork,
)

MOMENT = datetime(2026, 6, 4, 9, 0, tzinfo=UTC)


class AddableMediaRepository(FakeMediaAssetRepository):
    def add(self, asset: MediaAsset) -> None:
        self._pending[asset.id] = replace(asset)


class AddableUnitOfWork(FakeUnitOfWork):
    @property
    def media_assets(self) -> AddableMediaRepository:
        return AddableMediaRepository(self._database, self._pending_assets)


class FailingIntentStorage(InMemoryMediaStoragePort):
    def create_upload_intent(self, request: object) -> SignedUploadIntent:
        raise MediaStorageTransientError("intent storage unavailable")


def build_handler(
    database: FakeDatabase,
    clock: FakeClock,
    *,
    ttl_seconds: int = MAX_INTENT_TTL_SECONDS,
    max_bytes: int = 10 * 1024 * 1024,
    storage: InMemoryMediaStoragePort | None = None,
) -> tuple[RequestMediaUploadHandler, FakeUnitOfWork, InMemoryMediaStoragePort]:
    uow = AddableUnitOfWork(database, clock)
    media_storage = storage or InMemoryMediaStoragePort(clock)
    handler = RequestMediaUploadHandler(
        uow=uow,
        storage=media_storage,
        clock=clock,
        id_generator=Uuid4IdGenerator(),
        idempotency=MediaIntentIdempotencyStore(clock),
        max_bytes=max_bytes,
        ttl_seconds=ttl_seconds,
    )
    return handler, uow, media_storage


def admin_principal() -> CurrentPrincipal:
    return make_principal(roles=(RoleCode.SUPER_ADMIN,))


def test_request_upload_creates_bounded_server_generated_intent() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    handler, _, _ = build_handler(database, clock)
    command = RequestMediaUploadCommand("photo.jpg", "image/jpeg", 2048)

    result = handler.handle(command, principal=admin_principal())

    assert result.method == "PUT"
    assert result.required_headers == {"Content-Type": "image/jpeg"}
    assert result.expires_at == MOMENT + timedelta(seconds=MAX_INTENT_TTL_SECONDS)
    asset = database.assets[result.media_asset_id]
    assert asset.status is MediaStatus.UPLOADING
    assert asset.version == 1
    assert asset.intent_expires_at == result.expires_at
    assert str(asset.storage_key).startswith("staging/2026.06.")
    assert STAGING_KEY_PATTERN.fullmatch(str(asset.storage_key))
    assert len(database.audit_events) == 1
    assert database.audit_events[0].action is AuditAction.MEDIA_UPLOAD_REQUESTED
    assert database.audit_events[0].metadata["declared_mime"] == "image/jpeg"


def test_request_upload_is_idempotent_inside_ttl_and_expires() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    handler, _, _ = build_handler(database, clock)
    command = RequestMediaUploadCommand("photo.jpg", "image/jpeg", 2048)
    principal = admin_principal()

    first = handler.handle(command, principal=principal)
    second = handler.handle(command, principal=principal)

    assert first == second
    assert len(database.assets) == 1
    assert len(database.audit_events) == 1

    clock.advance(seconds=MAX_INTENT_TTL_SECONDS)
    third = handler.handle(command, principal=principal)

    assert third.media_asset_id != first.media_asset_id
    assert len(database.assets) == 2


def test_request_upload_rejects_unsafe_filename_and_mime() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    handler, _, _ = build_handler(database, clock)

    with pytest.raises(MediaInvalidInputError):
        handler.handle(
            RequestMediaUploadCommand("../photo.jpg", "image/jpeg", 2048),
            principal=admin_principal(),
        )
    with pytest.raises(MediaUnsupportedTypeError):
        handler.handle(
            RequestMediaUploadCommand("photo.avif", "image/avif", 2048),
            principal=admin_principal(),
        )
    assert database.assets == {}
    assert database.audit_events == []


def test_request_upload_enforces_size_budget() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    handler, _, _ = build_handler(database, clock, max_bytes=1024)

    with pytest.raises(MediaPayloadTooLargeError):
        handler.handle(
            RequestMediaUploadCommand("photo.jpg", "image/jpeg", 1025),
            principal=admin_principal(),
        )
    assert database.assets == {}


def test_request_upload_maps_storage_failure() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    storage = FailingIntentStorage(clock)
    handler, _, _ = build_handler(database, clock, storage=storage)

    with pytest.raises(MediaStorageUnavailableError):
        handler.handle(
            RequestMediaUploadCommand("photo.jpg", "image/jpeg", 2048),
            principal=admin_principal(),
        )
    assert database.assets == {}


def test_request_upload_requires_manage_media() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    handler, _, _ = build_handler(database, clock)
    viewer = make_principal(roles=(RoleCode.VIEWER,))

    with pytest.raises(AuthorizationError):
        handler.handle(
            RequestMediaUploadCommand("photo.jpg", "image/jpeg", 2048),
            principal=viewer,
        )
    assert database.assets == {}
