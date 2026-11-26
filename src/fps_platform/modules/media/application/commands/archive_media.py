from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fps_platform.modules.audit.domain.enums import AuditAction, AuditSource
from fps_platform.modules.identity.domain.exceptions import AuthorizationError
from fps_platform.modules.identity.domain.value_objects import PermissionCode
from fps_platform.modules.media.application.dto import (
    MediaConflictError,
    MediaNotFoundError,
    MediaReadModel,
    project_media,
)
from fps_platform.modules.media.application.services.promotion import MediaUnitOfWork
from fps_platform.modules.media.domain.exceptions import InvalidMediaTransitionError
from fps_platform.shared.auth.principal import CurrentPrincipal
from fps_platform.shared.domain.clock import Clock
from fps_platform.shared.domain.errors import ConcurrentModificationError

AUDIT_RESOURCE_TYPE = "MEDIA_ASSET"


@dataclass(frozen=True, slots=True)
class ArchiveMediaCommand:
    media_id: UUID
    expected_version: int | None = None


class ArchiveMediaHandler:
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

    def handle(self, command: ArchiveMediaCommand) -> MediaReadModel:
        if PermissionCode.MANAGE_MEDIA not in self._principal.permissions:
            raise AuthorizationError("PERMISSION_DENIED")

        asset = self._uow.media_assets.get(command.media_id)
        if asset is None:
            raise MediaNotFoundError("media asset does not exist")
        expected_version = (
            command.expected_version if command.expected_version is not None else asset.version
        )
        if asset.version != expected_version:
            raise MediaConflictError("media version changed")

        from_status = asset.status.value
        try:
            asset.archive(self._clock.now())
        except InvalidMediaTransitionError as exc:
            raise MediaConflictError("only READY media can be archived") from exc
        try:
            self._uow.media_assets.save(asset, expected_version=expected_version)
        except ConcurrentModificationError as exc:
            raise MediaConflictError("media version changed") from exc

        self._uow.audit_recorder.record(
            action=AuditAction.MEDIA_ARCHIVED,
            resource_type=AUDIT_RESOURCE_TYPE,
            resource_id=asset.id,
            metadata={"from_status": from_status, "to_status": asset.status.value},
            source=AuditSource.APPLICATION,
        )
        self._uow.commit()
        return project_media(asset)
