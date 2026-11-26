from __future__ import annotations

from dataclasses import dataclass

from fps_platform.modules.identity.domain.exceptions import AuthorizationError
from fps_platform.modules.identity.domain.value_objects import PermissionCode
from fps_platform.modules.media.application.dto import (
    MediaInvalidInputError,
    MediaListResult,
    project_media,
)
from fps_platform.modules.media.application.ports import MediaAssetRepository
from fps_platform.modules.media.domain.enums import MediaStatus
from fps_platform.shared.auth.principal import CurrentPrincipal

MAX_PAGE_SIZE = 100


@dataclass(frozen=True, slots=True)
class ListMediaQuery:
    limit: int = 20
    offset: int = 0
    status: MediaStatus | None = None


def list_media(
    *,
    uow: MediaAssetRepository,
    principal: CurrentPrincipal,
    query: ListMediaQuery,
) -> MediaListResult:
    if PermissionCode.VIEW_MEDIA not in principal.permissions:
        raise AuthorizationError("PERMISSION_DENIED")
    if isinstance(query.limit, bool) or not 1 <= query.limit <= MAX_PAGE_SIZE:
        raise MediaInvalidInputError("limit is out of range")
    if isinstance(query.offset, bool) or query.offset < 0:
        raise MediaInvalidInputError("offset is out of range")
    assets = uow.list(limit=query.limit, offset=query.offset, status=query.status)
    return MediaListResult(
        items=tuple(project_media(asset) for asset in assets),
        total=uow.count(status=query.status),
        limit=query.limit,
        offset=query.offset,
    )
