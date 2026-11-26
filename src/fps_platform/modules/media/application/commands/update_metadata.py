from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID

from fps_platform.modules.audit.domain.enums import AuditAction, AuditSource
from fps_platform.modules.identity.domain.exceptions import AuthorizationError
from fps_platform.modules.identity.domain.value_objects import PermissionCode
from fps_platform.modules.media.application.dto import (
    MediaConflictError,
    MediaInvalidInputError,
    MediaNotFoundError,
    MediaReadModel,
    project_media,
)
from fps_platform.modules.media.application.services.promotion import MediaUnitOfWork
from fps_platform.modules.media.domain.exceptions import InvalidMediaTransitionError
from fps_platform.modules.media.domain.value_objects import (
    LocalizedTextMap,
    MediaAttribution,
    MediaMetadata,
    MediaText,
    to_localized_text_map,
)
from fps_platform.shared.auth.principal import CurrentPrincipal
from fps_platform.shared.domain.clock import Clock
from fps_platform.shared.domain.errors import ConcurrentModificationError

AUDIT_RESOURCE_TYPE = "MEDIA_ASSET"


@dataclass(frozen=True, slots=True)
class UpdateMediaMetadataCommand:
    media_id: UUID
    expected_version: int
    title: str | None = None
    alt_texts: Mapping[str, str] | None = None
    captions: Mapping[str, str] | None = None
    attribution: Mapping[str, str] | None = None


class UpdateMetadataHandler:
    def __init__(
        self,
        *,
        uow: MediaUnitOfWork,
        clock: Clock,
        principal: CurrentPrincipal,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._principal = principal

    def handle(self, command: UpdateMediaMetadataCommand) -> MediaReadModel:
        if PermissionCode.MANAGE_MEDIA not in self._principal.permissions:
            raise AuthorizationError("PERMISSION_DENIED")
        if not _has_updates(command):
            raise MediaInvalidInputError("at least one metadata field is required")

        asset = self._uow.media_assets.get(command.media_id)
        if asset is None:
            raise MediaNotFoundError("media asset does not exist")
        if asset.version != command.expected_version:
            raise MediaConflictError("media version changed")

        try:
            merged = _merge_metadata(asset.metadata, command)
        except ValueError as exc:
            raise MediaInvalidInputError("media metadata is invalid") from exc

        from_version = asset.version
        try:
            asset.update_metadata(self._clock.now(), merged)
        except InvalidMediaTransitionError as exc:
            raise MediaConflictError("media metadata is read only in this status") from exc
        try:
            self._uow.media_assets.save(asset, expected_version=command.expected_version)
        except ConcurrentModificationError as exc:
            raise MediaConflictError("media version changed") from exc

        self._uow.audit_recorder.record(
            action=AuditAction.MEDIA_METADATA_UPDATED,
            resource_type=AUDIT_RESOURCE_TYPE,
            resource_id=asset.id,
            metadata={"from_version": from_version, "to_version": asset.version},
            source=AuditSource.APPLICATION,
        )
        self._uow.commit()
        return project_media(asset)


def _has_updates(command: UpdateMediaMetadataCommand) -> bool:
    return any(
        value is not None
        for value in (
            command.title,
            command.alt_texts,
            command.captions,
            command.attribution,
        )
    )


def _merge_metadata(current: MediaMetadata, command: UpdateMediaMetadataCommand) -> MediaMetadata:
    title = MediaText(command.title) if command.title is not None else current.title
    return MediaMetadata(
        title=title,
        alt_texts=_merge_localized(current.alt_texts, command.alt_texts),
        captions=_merge_localized(current.captions, command.captions),
        attribution=_merge_attribution(current.attribution, command.attribution),
    )


def _merge_localized(
    current: LocalizedTextMap, updates: Mapping[str, str] | None
) -> LocalizedTextMap:
    values = current.as_mapping()
    if updates is not None:
        values.update(updates)
    return to_localized_text_map(values)


def _merge_attribution(
    current: MediaAttribution | None, updates: Mapping[str, str] | None
) -> MediaAttribution | None:
    values = current.as_mapping() if current is not None else {}
    if updates is not None:
        if set(updates) - {"source", "license"}:
            raise ValueError("attribution contains an unsupported key")
        values.update(updates)
    if not values:
        return None
    return MediaAttribution(
        source=MediaText(values["source"]) if "source" in values else None,
        license=MediaText(values["license"]) if "license" in values else None,
    )
