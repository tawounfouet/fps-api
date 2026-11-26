from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fps_platform.modules.identity.domain.exceptions import AuthorizationError
from fps_platform.modules.identity.domain.value_objects import PermissionCode
from fps_platform.modules.media.application.dto import MediaUsageResult
from fps_platform.modules.media.application.services.usage_sources import MediaUsageLookup
from fps_platform.shared.auth.principal import CurrentPrincipal


@dataclass(frozen=True, slots=True)
class GetMediaUsageQuery:
    media_id: UUID


def get_media_usage(
    *,
    lookup: MediaUsageLookup,
    principal: CurrentPrincipal,
    query: GetMediaUsageQuery,
) -> MediaUsageResult:
    if PermissionCode.VIEW_MEDIA not in principal.permissions:
        raise AuthorizationError("PERMISSION_DENIED")
    return lookup.lookup(query.media_id)
