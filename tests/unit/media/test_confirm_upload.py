from __future__ import annotations

from datetime import UTC, datetime

import pytest

from fps_platform.modules.audit.domain.enums import AuditAction
from fps_platform.modules.identity.domain.exceptions import AuthorizationError
from fps_platform.modules.identity.domain.value_objects import RoleCode
from fps_platform.modules.media.application.commands.confirm_upload import (
    ConfirmMediaUploadCommand,
    ConfirmMediaUploadHandler,
)
from fps_platform.modules.media.application.dto import (
    MediaConflictError,
    MediaNotFoundError,
)
from fps_platform.modules.media.application.services.promotion import (
    MediaInspectionError,
    MediaPromotionService,
    PromotionBlockedError,
)
from fps_platform.modules.media.domain.entities import MediaAsset
from fps_platform.modules.media.domain.enums import MediaStatus
from fps_platform.modules.media.domain.value_objects import MAX_UPLOAD_ATTEMPTS, StorageKey
from fps_platform.modules.media.infrastructure.fake_storage import InMemoryMediaStoragePort
from fps_platform.modules.media.infrastructure.image_inspection import PillowImageInspector
from fps_platform.shared.auth.principal import CurrentPrincipal
from fps_platform.shared.domain.clock import FakeClock
from fps_platform.shared.domain.identifiers import Uuid4IdGenerator
from tests.api.identity.test_admin import make_principal
from tests.security.media.fixtures import (
    FakeDatabase,
    FakeUnitOfWork,
    make_asset,
    valid_jpeg,
)

MOMENT = datetime(2026, 6, 4, 9, 0, tzinfo=UTC)


def build_handler(
    database: FakeDatabase,
    clock: FakeClock,
    principal: CurrentPrincipal,
    *,
    storage: InMemoryMediaStoragePort | None = None,
) -> tuple[ConfirmMediaUploadHandler, FakeUnitOfWork, InMemoryMediaStoragePort]:
    uow = FakeUnitOfWork(database, clock)
    media_storage = storage or InMemoryMediaStoragePort(clock)
    promotion = MediaPromotionService(
        storage=media_storage,
        inspector=PillowImageInspector(clock),
        uow_factory=lambda: FakeUnitOfWork(database, clock),
        clock=clock,
        id_generator=Uuid4IdGenerator(),
    )
    handler = ConfirmMediaUploadHandler(
        uow=uow,
        promotion=promotion,
        clock=clock,
        principal=principal,
    )
    return handler, uow, media_storage


def admin_principal() -> CurrentPrincipal:
    return make_principal(roles=(RoleCode.SUPER_ADMIN,))


def seed_uploaded_asset(
    database: FakeDatabase, storage: InMemoryMediaStoragePort, *, body: bytes | None = None
) -> MediaAsset:
    asset = make_asset(status=MediaStatus.UPLOADING, version=1)
    database.assets[asset.id] = asset
    storage.put_object(asset.storage_key, body if body is not None else valid_jpeg(), "image/jpeg")
    return asset


def test_confirm_upload_promotes_to_ready_with_audit() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    principal = admin_principal()
    handler, _, storage = build_handler(database, clock, principal)
    asset = seed_uploaded_asset(database, storage)

    result = handler.handle(ConfirmMediaUploadCommand(media_id=asset.id, expected_version=1))

    assert result.status is MediaStatus.READY
    assert result.checksum_sha256 is not None
    promoted = database.assets[asset.id]
    assert promoted.status is MediaStatus.READY
    assert promoted.version == result.version
    assert promoted.checksum is not None
    actions = [event.action for event in database.audit_events]
    assert AuditAction.MEDIA_UPLOAD_CONFIRMED in actions
    assert AuditAction.CONTENT_REVALIDATION_REQUESTED in actions


def test_confirm_upload_is_stable_after_ready() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    principal = admin_principal()
    handler, _, storage = build_handler(database, clock, principal)
    asset = seed_uploaded_asset(database, storage)

    first = handler.handle(ConfirmMediaUploadCommand(media_id=asset.id, expected_version=1))
    replay = handler.handle(ConfirmMediaUploadCommand(media_id=asset.id, expected_version=1))

    assert replay == first
    assert len(database.audit_events) == 2


def test_confirm_upload_rejects_stale_version_and_missing_asset() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    principal = admin_principal()
    handler, _, storage = build_handler(database, clock, principal)
    asset = seed_uploaded_asset(database, storage)

    with pytest.raises(MediaConflictError):
        handler.handle(ConfirmMediaUploadCommand(media_id=asset.id, expected_version=99))
    missing = make_asset()
    with pytest.raises(MediaNotFoundError):
        handler.handle(ConfirmMediaUploadCommand(media_id=missing.id, expected_version=1))


def test_confirm_upload_rejects_foreign_claim() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    principal = admin_principal()
    handler, _, storage = build_handler(database, clock, principal)
    asset = make_asset(
        status=MediaStatus.PROCESSING,
        version=2,
        claim_owner="someone-else",
        storage_key=StorageKey("staging/worker-1/5a3c1e44-19c9-4e0e-9c0a-6d1f2a5b8c11"),
    )
    database.assets[asset.id] = asset
    storage.put_object(asset.storage_key, valid_jpeg(), "image/jpeg")

    with pytest.raises(MediaConflictError):
        handler.handle(ConfirmMediaUploadCommand(media_id=asset.id, expected_version=2))


def test_confirm_upload_retry_budget_is_bounded() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    principal = admin_principal()
    handler, _, storage = build_handler(database, clock, principal)
    asset = seed_uploaded_asset(database, storage, body=b"<html>not an image</html>")

    for _ in range(MAX_UPLOAD_ATTEMPTS):
        with pytest.raises((MediaInspectionError, PromotionBlockedError)):
            handler.handle(
                ConfirmMediaUploadCommand(
                    media_id=asset.id, expected_version=database.assets[asset.id].version
                )
            )

    assert database.assets[asset.id].status is MediaStatus.FAILED
    assert database.assets[asset.id].attempt_count == MAX_UPLOAD_ATTEMPTS
    with pytest.raises(MediaConflictError):
        handler.handle(
            ConfirmMediaUploadCommand(
                media_id=asset.id, expected_version=database.assets[asset.id].version
            )
        )


def test_confirm_upload_requires_manage_media() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    viewer = make_principal(roles=(RoleCode.VIEWER,))
    handler, _, storage = build_handler(database, clock, viewer)
    asset = seed_uploaded_asset(database, storage)

    with pytest.raises(AuthorizationError):
        handler.handle(ConfirmMediaUploadCommand(media_id=asset.id, expected_version=1))
