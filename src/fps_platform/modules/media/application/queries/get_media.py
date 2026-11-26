from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fps_platform.modules.identity.domain.exceptions import AuthorizationError
from fps_platform.modules.identity.domain.value_objects import PermissionCode
from fps_platform.modules.media.application.dto import (
    MediaNotFoundError,
    MediaReadModel,
    project_media,
)
from fps_platform.modules.media.application.ports import MediaAssetRepository
from fps_platform.shared.auth.principal import CurrentPrincipal


@dataclass(frozen=True, slots=True)
class GetMediaQuery:
    media_id: UUID


def get_media(
    *,
    uow: MediaAssetRepository,
    principal: CurrentPrincipal,
    query: GetMediaQuery,
) -> MediaReadModel:
    if PermissionCode.VIEW_MEDIA not in principal.permissions:
        raise AuthorizationError("PERMISSION_DENIED")
    asset = uow.get(query.media_id)
    if asset is None:
        raise MediaNotFoundError("media asset does not exist")
    return project_media(asset)
