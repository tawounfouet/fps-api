from __future__ import annotations

from uuid import uuid4

import pytest

from fps_platform.modules.media.application.dto import (
    MediaConflictError,
    MediaInvalidInputError,
    MediaNotFoundError,
)
from fps_platform.modules.media.application.services.public_usage import (
    validate_media_for_public_usage,
)
from fps_platform.modules.media.domain.entities import MediaAsset
from fps_platform.modules.media.domain.enums import ChecksumAlgorithm, MediaStatus
from fps_platform.modules.media.domain.value_objects import (
    ByteSize,
    Checksum,
    MediaDimensions,
    MediaMetadata,
    MediaText,
    MimeType,
    OriginalFileName,
    to_localized_text_map,
)
from fps_platform.shared.domain.clock import FakeClock
from tests.security.media.fixtures import (
    FINAL_KEY,
    MOMENT,
    FakeDatabase,
    FakeMediaAssetRepository,
    FakeUnitOfWork,
)


def make_asset(
    *,
    status: MediaStatus = MediaStatus.READY,
    alts: dict[str, str] | None = None,
    title: str | None = "Titre public",
) -> MediaAsset:
    return MediaAsset(
        id=uuid4(),
        storage_key=FINAL_KEY,
        original_filename=OriginalFileName("photo.jpg"),
        mime_type=MimeType("image/jpeg"),
        byte_size=ByteSize(128),
        status=status,
        metadata=MediaMetadata(
            title=MediaText(title) if title is not None else None,
            alt_texts=to_localized_text_map(alts or {}),
        ),
        uploaded_by=uuid4(),
        created_at=MOMENT,
        updated_at=MOMENT,
        version=1,
        dimensions=MediaDimensions(12, 8),
        checksum=Checksum(ChecksumAlgorithm.SHA256, "a" * 64),
        ready_at=MOMENT,
        promotion_proof_id=uuid4(),
        detected_mime=MimeType("image/jpeg"),
        verified_at=MOMENT,
    )


def lookup_for(asset: MediaAsset) -> FakeMediaAssetRepository:
    database = FakeDatabase()
    database.assets[asset.id] = asset
    return FakeUnitOfWork(database, FakeClock(MOMENT)).media_assets


@pytest.mark.parametrize(
    ("alts", "locale", "expected"),
    [
        ({"fr": "Texte FR"}, "fr", "Texte FR"),
        ({"en": "English alt"}, "en", "English alt"),
        ({"fr": "Texte FR", "en": "English alt"}, "fr", "Texte FR"),
        ({"fr": "Texte FR", "en": "English alt"}, "en", "English alt"),
    ],
)
def test_alt_in_publication_locale_is_consumable(
    alts: dict[str, str], locale: str, expected: str
) -> None:
    asset = make_asset(alts=alts)

    contract = validate_media_for_public_usage(asset.id, locale, False, assets=lookup_for(asset))

    assert contract.media_id == asset.id
    assert contract.locale == locale
    assert contract.decorative is False
    assert contract.alt_text == expected
    assert contract.title == "Titre public"
    assert not hasattr(contract, "url")
    assert not hasattr(contract, "upload_url")
    assert not hasattr(contract, "storage_key")
    assert "http" not in str(contract).lower()
    assert "secret" not in str(contract).lower()
    assert "credential" not in str(contract).lower()


@pytest.mark.parametrize(
    ("alts", "locale"),
    [
        ({}, "fr"),
        ({}, "en"),
        ({"fr": "Texte FR"}, "en"),
        ({"en": "English alt"}, "fr"),
    ],
    ids=["no-alt-fr", "no-alt-en", "fr-only-en", "en-only-fr"],
)
def test_missing_alt_in_publication_locale_is_refused_without_fallback(
    alts: dict[str, str], locale: str
) -> None:
    asset = make_asset(alts=alts)

    with pytest.raises(MediaInvalidInputError):
        validate_media_for_public_usage(asset.id, locale, False, assets=lookup_for(asset))


@pytest.mark.parametrize(
    ("alts", "locale", "expected_alt"),
    [
        ({}, "fr", None),
        ({"fr": "Texte FR"}, "en", None),
        ({"en": "English alt"}, "fr", None),
        ({"fr": "Texte FR", "en": "English alt"}, "en", None),
    ],
)
def test_explicit_decorative_never_falls_back_to_fr(
    alts: dict[str, str], locale: str, expected_alt: str | None
) -> None:
    asset = make_asset(alts=alts)

    contract = validate_media_for_public_usage(asset.id, locale, True, assets=lookup_for(asset))

    assert contract.decorative is True
    assert contract.alt_text == expected_alt


def test_unsupported_locale_is_refused() -> None:
    asset = make_asset(alts={"fr": "Texte FR"})

    with pytest.raises(MediaInvalidInputError):
        validate_media_for_public_usage(asset.id, "de", False, assets=lookup_for(asset))
    with pytest.raises(MediaInvalidInputError):
        validate_media_for_public_usage(asset.id, "FR-ca", False, assets=lookup_for(asset))


@pytest.mark.parametrize(
    "status", [MediaStatus.ARCHIVED, MediaStatus.UPLOADING, MediaStatus.FAILED]
)
def test_non_ready_status_is_refused(status: MediaStatus) -> None:
    asset = make_asset(status=status, alts={"fr": "Texte FR"})

    with pytest.raises(MediaConflictError):
        validate_media_for_public_usage(asset.id, "fr", False, assets=lookup_for(asset))


def test_missing_asset_is_refused() -> None:
    with pytest.raises(MediaNotFoundError):
        validate_media_for_public_usage(uuid4(), "fr", False, assets=lookup_for(make_asset()))
