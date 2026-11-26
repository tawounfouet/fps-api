from __future__ import annotations

from hashlib import sha256
from uuid import uuid4

import pytest

from fps_platform.modules.audit.domain.enums import AuditAction
from fps_platform.modules.identity.domain.exceptions import AuthorizationError
from fps_platform.modules.identity.domain.value_objects import RoleCode
from fps_platform.modules.media.application.commands.archive_media import (
    ArchiveMediaCommand,
    ArchiveMediaHandler,
)
from fps_platform.modules.media.application.commands.restore_media import (
    RestoreMediaCommand,
    RestoreMediaHandler,
)
from fps_platform.modules.media.application.dto import (
    MediaConflictError,
    MediaNotFoundError,
    MediaStorageUnavailableError,
)
from fps_platform.modules.media.application.ports import ObjectHead
from fps_platform.modules.media.application.services.public_usage import (
    validate_media_for_public_usage,
)
from fps_platform.modules.media.domain.entities import MediaAsset
from fps_platform.modules.media.domain.enums import ChecksumAlgorithm, MediaStatus
from fps_platform.modules.media.domain.exceptions import MediaStorageTransientError
from fps_platform.modules.media.domain.value_objects import (
    ByteSize,
    Checksum,
    LocalizedTextMap,
    MediaDimensions,
    MediaMetadata,
    MediaText,
    MimeType,
    OriginalFileName,
    StorageKey,
)
from fps_platform.modules.media.infrastructure.fake_storage import InMemoryMediaStoragePort
from fps_platform.shared.auth.principal import CurrentPrincipal
from fps_platform.shared.domain.clock import FakeClock
from tests.api.identity.test_admin import make_principal
from tests.security.media.fixtures import (
    FINAL_KEY,
    MOMENT,
    STAGING_KEY,
    FakeDatabase,
    FakeUnitOfWork,
)

ADMIN = make_principal(roles=(RoleCode.SUPER_ADMIN,))
FINAL_BODY = b"final-bytes"


def make_asset(
    *,
    status: MediaStatus = MediaStatus.READY,
    version: int = 3,
    storage_key: StorageKey = FINAL_KEY,
    proof: bool = True,
) -> MediaAsset:
    return MediaAsset(
        id=uuid4(),
        storage_key=storage_key,
        original_filename=OriginalFileName("photo.jpg"),
        mime_type=MimeType("image/jpeg"),
        byte_size=ByteSize(len(FINAL_BODY)),
        status=status,
        metadata=MediaMetadata(
            title=MediaText(" titre "),
            alt_texts=LocalizedTextMap(fr=MediaText("Texte FR"), en=MediaText("English alt")),
        ),
        uploaded_by=uuid4(),
        created_at=MOMENT,
        updated_at=MOMENT,
        version=version,
        dimensions=MediaDimensions(12, 8),
        checksum=Checksum(ChecksumAlgorithm.SHA256, sha256(FINAL_BODY).hexdigest()),
        ready_at=MOMENT,
        promoted_at=MOMENT,
        verified_at=MOMENT,
        promotion_proof_id=uuid4() if proof else None,
        detected_mime=MimeType("image/jpeg"),
    )


def seed_final(storage: InMemoryMediaStoragePort, body: bytes = FINAL_BODY) -> None:
    storage.put_object(FINAL_KEY, body, "image/jpeg")


def archive_handler(
    database: FakeDatabase, clock: FakeClock, principal: CurrentPrincipal = ADMIN
) -> ArchiveMediaHandler:
    return ArchiveMediaHandler(
        uow=FakeUnitOfWork(database, clock), clock=clock, principal=principal
    )


def restore_handler(
    database: FakeDatabase,
    clock: FakeClock,
    storage: InMemoryMediaStoragePort,
    principal: CurrentPrincipal = ADMIN,
) -> RestoreMediaHandler:
    return RestoreMediaHandler(
        uow=FakeUnitOfWork(database, clock),
        storage=storage,
        clock=clock,
        principal=principal,
    )


def test_archive_is_reversible_and_keeps_binary_and_history() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    storage = InMemoryMediaStoragePort(clock)
    asset = make_asset()
    database.assets[asset.id] = asset
    seed_final(storage)

    result = archive_handler(database, clock).handle(ArchiveMediaCommand(media_id=asset.id))

    archived = database.assets[asset.id]
    assert result.status is MediaStatus.ARCHIVED
    assert archived.status is MediaStatus.ARCHIVED
    assert archived.archived_at is not None
    assert archived.version == 4
    assert archived.storage_key == asset.storage_key
    assert archived.promotion_proof_id == asset.promotion_proof_id
    assert archived.checksum == asset.checksum
    assert archived.dimensions == asset.dimensions
    assert archived.verified_at == asset.verified_at
    assert archived.promoted_at == asset.promoted_at
    assert archived.metadata == asset.metadata
    assert storage.head_object(FINAL_KEY).exists
    assert database.audit_events[0].action is AuditAction.MEDIA_ARCHIVED
    assert database.audit_events[0].metadata == {"from_status": "READY", "to_status": "ARCHIVED"}


def test_archived_asset_is_not_assignable_for_public_usage() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    storage = InMemoryMediaStoragePort(clock)
    asset = make_asset()
    database.assets[asset.id] = asset
    seed_final(storage)
    archive_handler(database, clock).handle(ArchiveMediaCommand(media_id=asset.id))

    with pytest.raises(MediaConflictError):
        validate_media_for_public_usage(
            asset.id, "fr", False, assets=FakeUnitOfWork(database, clock).media_assets
        )
    with pytest.raises(MediaConflictError):
        archive_handler(database, clock).handle(ArchiveMediaCommand(media_id=asset.id))


@pytest.mark.parametrize(
    "status", [MediaStatus.UPLOADING, MediaStatus.PROCESSING, MediaStatus.FAILED]
)
def test_archive_from_non_ready_status_is_refused(status: MediaStatus) -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    storage = InMemoryMediaStoragePort(clock)
    asset = make_asset(status=status)
    database.assets[asset.id] = asset
    seed_final(storage)

    with pytest.raises(MediaConflictError):
        archive_handler(database, clock).handle(ArchiveMediaCommand(media_id=asset.id))


def test_restore_requires_final_head_and_promotion_evidence() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    storage = InMemoryMediaStoragePort(clock)
    asset = make_asset(status=MediaStatus.ARCHIVED)
    database.assets[asset.id] = asset
    seed_final(storage)

    result = restore_handler(database, clock, storage).handle(
        RestoreMediaCommand(media_id=asset.id)
    )

    restored = database.assets[asset.id]
    assert result.status is MediaStatus.READY
    assert restored.status is MediaStatus.READY
    assert restored.archived_at is None
    assert restored.version == 4
    assert restored.storage_key == asset.storage_key
    assert restored.promotion_proof_id == asset.promotion_proof_id
    assert restored.checksum == asset.checksum
    assert restored.metadata == asset.metadata
    assert storage.head_object(FINAL_KEY).exists
    assert database.audit_events[0].action is AuditAction.MEDIA_RESTORED
    assert database.audit_events[0].metadata == {"from_status": "ARCHIVED", "to_status": "READY"}


@pytest.mark.parametrize(
    ("body", "proof", "storage_key", "expected_version"),
    [
        (None, True, FINAL_KEY, None),
        (b"final-byteZ", True, FINAL_KEY, None),
        (FINAL_BODY, False, FINAL_KEY, None),
        (FINAL_BODY, True, STAGING_KEY, None),
        (FINAL_BODY, True, FINAL_KEY, 99),
    ],
    ids=["missing-object", "tampered-object", "missing-proof", "staging-key", "stale-version"],
)
def test_restore_refuses_inconsistent_evidence(
    body: bytes | None,
    proof: bool,
    storage_key: StorageKey,
    expected_version: int | None,
) -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    storage = InMemoryMediaStoragePort(clock)
    asset = make_asset(status=MediaStatus.ARCHIVED, storage_key=storage_key, proof=proof)
    database.assets[asset.id] = asset
    if body is not None:
        storage.put_object(storage_key, body, "image/jpeg")

    with pytest.raises(MediaConflictError):
        restore_handler(database, clock, storage).handle(
            RestoreMediaCommand(media_id=asset.id, expected_version=expected_version)
        )

    assert database.assets[asset.id].status is MediaStatus.ARCHIVED
    assert database.audit_events == []
    assert database.commit_calls == 0


def test_restore_from_ready_and_missing_asset_are_refused() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    storage = InMemoryMediaStoragePort(clock)
    seed_final(storage)
    ready = make_asset()
    database.assets[ready.id] = ready

    with pytest.raises(MediaConflictError):
        restore_handler(database, clock, storage).handle(RestoreMediaCommand(media_id=ready.id))
    with pytest.raises(MediaNotFoundError):
        restore_handler(database, clock, storage).handle(RestoreMediaCommand(media_id=uuid4()))


class FailingHeadStorage(InMemoryMediaStoragePort):
    def head_object(self, key: StorageKey) -> ObjectHead:
        raise MediaStorageTransientError("final object head failed")


def test_restore_maps_storage_failure_to_unavailable() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    storage = FailingHeadStorage(clock)
    asset = make_asset(status=MediaStatus.ARCHIVED)
    database.assets[asset.id] = asset

    with pytest.raises(MediaStorageUnavailableError):
        restore_handler(database, clock, storage).handle(RestoreMediaCommand(media_id=asset.id))


def test_lifecycle_handlers_require_manage_media() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    storage = InMemoryMediaStoragePort(clock)
    viewer = make_principal(roles=(RoleCode.VIEWER,))
    ready = make_asset()
    archived = make_asset(status=MediaStatus.ARCHIVED)
    database.assets[ready.id] = ready
    database.assets[archived.id] = archived
    seed_final(storage)

    with pytest.raises(AuthorizationError):
        archive_handler(database, clock, viewer).handle(ArchiveMediaCommand(media_id=ready.id))
    with pytest.raises(AuthorizationError):
        restore_handler(database, clock, storage, viewer).handle(
            RestoreMediaCommand(media_id=archived.id)
        )


def test_restore_commit_failure_keeps_archived_state() -> None:
    database = FakeDatabase(fail_commit_at=1)
    clock = FakeClock(MOMENT)
    storage = InMemoryMediaStoragePort(clock)
    asset = make_asset(status=MediaStatus.ARCHIVED)
    database.assets[asset.id] = asset
    seed_final(storage)

    with pytest.raises(RuntimeError, match="database commit failed"):
        restore_handler(database, clock, storage).handle(RestoreMediaCommand(media_id=asset.id))

    assert database.assets[asset.id].status is MediaStatus.ARCHIVED
    assert database.audit_events == []
    assert storage.head_object(FINAL_KEY).exists
