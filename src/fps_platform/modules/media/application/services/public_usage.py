from __future__ import annotations

from uuid import UUID

from fps_platform.modules.media.application.dto import (
    MediaConflictError,
    MediaInvalidInputError,
    MediaNotFoundError,
    PublicUsageContract,
)
from fps_platform.modules.media.application.ports import MediaAssetRepository
from fps_platform.modules.media.domain.enums import MediaLocale, MediaStatus
from fps_platform.modules.media.domain.value_objects import SUPPORTED_LOCALES

PUBLIC_STATUSES = frozenset({MediaStatus.READY})


def validate_media_for_public_usage(
    media_id: UUID,
    locale: MediaLocale | str,
    decorative: bool,
    *,
    assets: MediaAssetRepository,
) -> PublicUsageContract:
    normalized_locale = _locale(locale)
    asset = assets.get(media_id)
    if asset is None:
        raise MediaNotFoundError("media asset does not exist")
    if asset.status not in PUBLIC_STATUSES:
        raise MediaConflictError("media is not available for public usage")

    alt_texts = asset.metadata.alt_texts.as_mapping()
    alt_text = alt_texts.get(normalized_locale)
    if not decorative and not alt_text:
        raise MediaInvalidInputError("alt text is required in the publication locale")

    return PublicUsageContract(
        media_id=asset.id,
        locale=normalized_locale,
        decorative=decorative,
        alt_text=None if decorative else alt_text,
        title=asset.metadata.title.value if asset.metadata.title is not None else None,
    )


def _locale(locale: MediaLocale | str) -> str:
    value = str(locale).strip().lower()
    if value not in SUPPORTED_LOCALES:
        raise MediaInvalidInputError("publication locale is not supported")
    return value
