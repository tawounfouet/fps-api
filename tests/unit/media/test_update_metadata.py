from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from fps_platform.modules.audit.domain.enums import AuditAction
from fps_platform.modules.identity.domain.exceptions import AuthorizationError
from fps_platform.modules.identity.domain.value_objects import RoleCode
from fps_platform.modules.media.application.commands.update_metadata import (
    UpdateMediaMetadataCommand,
    UpdateMetadataHandler,
)
from fps_platform.modules.media.application.dto import (
    MediaConflictError,
    MediaInvalidInputError,
    MediaNotFoundError,
)
from fps_platform.modules.media.domain.entities import MediaAsset
from fps_platform.modules.media.domain.enums import ChecksumAlgorithm, MediaStatus
from fps_platform.modules.media.domain.value_objects import (
    ByteSize,
    Checksum,
    LocalizedTextMap,
    MediaAttribution,
    MediaDimensions,
    MediaMetadata,
    MediaText,
    MimeType,
    OriginalFileName,
)
from fps_platform.shared.auth.principal import CurrentPrincipal
from fps_platform.shared.domain.clock import FakeClock
from fps_platform.shared.domain.errors import ConcurrentModificationError
from tests.api.identity.test_admin import make_principal
from tests.security.media.fixtures import (
    FINAL_KEY,
    MOMENT,
    FakeDatabase,
    FakeMediaAssetRepository,
    FakeUnitOfWork,
)

ADMIN = make_principal(roles=(RoleCode.SUPER_ADMIN,))


def make_asset(*, status: MediaStatus = MediaStatus.READY, metadata: MediaMetadata) -> MediaAsset:
    return MediaAsset(
        id=uuid4(),
        storage_key=FINAL_KEY,
        original_filename=OriginalFileName("photo.jpg"),
        mime_type=MimeType("image/jpeg"),
        byte_size=ByteSize(128),
        status=status,
        metadata=metadata,
        uploaded_by=uuid4(),
        created_at=MOMENT,
        updated_at=datetime(2026, 6, 4, 10, tzinfo=UTC),
        version=3,
        dimensions=MediaDimensions(12, 8),
        checksum=Checksum(ChecksumAlgorithm.SHA256, "a" * 64),
        ready_at=MOMENT if status is not MediaStatus.UPLOADING else None,
        promoted_at=MOMENT,
        verified_at=MOMENT,
        promotion_proof_id=uuid4(),
    )


def full_metadata() -> MediaMetadata:
    return MediaMetadata(
        title=MediaText("Original title"),
        alt_texts=LocalizedTextMap(fr=MediaText("Texte FR"), en=MediaText("English alt")),
        captions=LocalizedTextMap(fr=MediaText("Legende FR"), en=MediaText("Caption EN")),
        attribution=MediaAttribution(source=MediaText("Source"), license=MediaText("Licence")),
    )


def build_handler(
    database: FakeDatabase, clock: FakeClock, principal: CurrentPrincipal = ADMIN
) -> UpdateMetadataHandler:
    return UpdateMetadataHandler(
        uow=FakeUnitOfWork(database, clock), clock=clock, principal=principal
    )


def test_fr_only_update_after_en_existing_keeps_en() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    asset = make_asset(metadata=full_metadata())
    database.assets[asset.id] = asset
    handler = build_handler(database, clock)

    result = handler.handle(
        UpdateMediaMetadataCommand(
            media_id=asset.id,
            expected_version=3,
            title="Titre modifie",
            alt_texts={"fr": "Nouveau texte FR"},
            captions={"fr": "Nouvelle legende FR"},
        )
    )

    assert result.version == 4
    updated = database.assets[asset.id]
    assert updated.metadata.title is not None
    assert str(updated.metadata.title) == "Titre modifie"
    assert updated.metadata.alt_texts.as_mapping() == {
        "fr": "Nouveau texte FR",
        "en": "English alt",
    }
    assert updated.metadata.captions.as_mapping() == {
        "fr": "Nouvelle legende FR",
        "en": "Caption EN",
    }
    assert updated.metadata.attribution is not None
    assert updated.metadata.attribution.as_mapping() == {
        "source": "Source",
        "license": "Licence",
    }
    assert database.audit_events[0].action is AuditAction.MEDIA_METADATA_UPDATED
    assert database.audit_events[0].metadata == {"from_version": 3, "to_version": 4}
    assert database.commit_calls == 1


def test_en_only_update_after_fr_existing_keeps_fr() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    asset = make_asset(metadata=full_metadata())
    database.assets[asset.id] = asset
    handler = build_handler(database, clock)

    handler.handle(
        UpdateMediaMetadataCommand(
            media_id=asset.id,
            expected_version=3,
            alt_texts={"en": "Updated English alt"},
            captions={"en": "Updated caption"},
            attribution={"license": "Updated licence"},
        )
    )

    updated = database.assets[asset.id]
    assert updated.metadata.alt_texts.as_mapping() == {
        "fr": "Texte FR",
        "en": "Updated English alt",
    }
    assert updated.metadata.captions.as_mapping() == {
        "fr": "Legende FR",
        "en": "Updated caption",
    }
    assert updated.metadata.attribution is not None
    assert updated.metadata.attribution.as_mapping() == {
        "source": "Source",
        "license": "Updated licence",
    }
    assert updated.metadata.title is not None
    assert str(updated.metadata.title) == "Original title"


def test_stale_version_refuses_update_without_mutation() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    asset = make_asset(metadata=full_metadata())
    database.assets[asset.id] = asset
    handler = build_handler(database, clock)

    with pytest.raises(MediaConflictError):
        handler.handle(
            UpdateMediaMetadataCommand(
                media_id=asset.id,
                expected_version=99,
                alt_texts={"en": "Should not be written"},
            )
        )

    stored = database.assets[asset.id]
    assert stored.version == 3
    assert stored.metadata.alt_texts.as_mapping()["en"] == "English alt"
    assert database.audit_events == []
    assert database.commit_calls == 0


class ConflictingRepository(FakeMediaAssetRepository):
    def save(self, asset: MediaAsset, *, expected_version: int | None = None) -> None:
        raise ConcurrentModificationError("media version changed")


class ConflictingUnitOfWork(FakeUnitOfWork):
    @property
    def media_assets(self) -> ConflictingRepository:
        return ConflictingRepository(self._database, self._pending_assets)


def test_repository_version_race_is_reported_as_conflict() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    asset = make_asset(metadata=full_metadata())
    database.assets[asset.id] = asset
    handler = UpdateMetadataHandler(
        uow=ConflictingUnitOfWork(database, clock), clock=clock, principal=ADMIN
    )

    with pytest.raises(MediaConflictError):
        handler.handle(
            UpdateMediaMetadataCommand(
                media_id=asset.id,
                expected_version=3,
                alt_texts={"en": "Should not be written"},
            )
        )

    assert database.audit_events == []
    assert database.commit_calls == 0


def test_invalid_locale_and_empty_patch_are_refused() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    asset = make_asset(metadata=full_metadata())
    database.assets[asset.id] = asset
    handler = build_handler(database, clock)

    with pytest.raises(MediaInvalidInputError):
        handler.handle(
            UpdateMediaMetadataCommand(
                media_id=asset.id, expected_version=3, alt_texts={"de": "Nein"}
            )
        )
    with pytest.raises(MediaInvalidInputError):
        handler.handle(UpdateMediaMetadataCommand(media_id=asset.id, expected_version=3))

    assert database.assets[asset.id].version == 3
    assert database.audit_events == []


@pytest.mark.parametrize("status", [MediaStatus.PROCESSING, MediaStatus.FAILED])
def test_processing_and_failed_statuses_are_read_only(status: MediaStatus) -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    asset = make_asset(status=status, metadata=full_metadata())
    database.assets[asset.id] = asset
    handler = build_handler(database, clock)

    with pytest.raises(MediaConflictError):
        handler.handle(
            UpdateMediaMetadataCommand(
                media_id=asset.id, expected_version=3, alt_texts={"fr": "Interdit"}
            )
        )


def test_missing_asset_and_permission_are_refused() -> None:
    database = FakeDatabase()
    clock = FakeClock(MOMENT)
    handler = build_handler(database, clock)
    viewer = make_principal(roles=(RoleCode.VIEWER,))
    command = UpdateMediaMetadataCommand(
        media_id=uuid4(), expected_version=1, alt_texts={"fr": "Texte"}
    )

    with pytest.raises(MediaNotFoundError):
        handler.handle(command)
    with pytest.raises(AuthorizationError):
        build_handler(database, clock, viewer).handle(command)


def test_commit_failure_leaves_no_audit_and_no_metadata_change() -> None:
    database = FakeDatabase(fail_commit_at=1)
    clock = FakeClock(MOMENT)
    asset = make_asset(metadata=full_metadata())
    database.assets[asset.id] = asset
    handler = build_handler(database, clock)

    with pytest.raises(RuntimeError, match="database commit failed"):
        handler.handle(
            UpdateMediaMetadataCommand(
                media_id=asset.id, expected_version=3, alt_texts={"fr": "Non persiste"}
            )
        )

    assert database.assets[asset.id].metadata.alt_texts.as_mapping()["fr"] == "Texte FR"
    assert database.audit_events == []
