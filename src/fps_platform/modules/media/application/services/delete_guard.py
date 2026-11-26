from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fps_platform.modules.media.application.dto import MediaStillInUseError
from fps_platform.modules.media.application.services.usage_sources import MediaUsageLookup
from fps_platform.modules.media.domain.enums import MediaCoverageStatus

DELETE_MEDIA = "DELETE_MEDIA"


@dataclass(frozen=True, slots=True)
class DeleteMediaCommand:
    media_id: UUID
    action: str = DELETE_MEDIA


class DeleteGuard:
    def __init__(self, *, lookup: MediaUsageLookup) -> None:
        self._lookup = lookup

    def assert_deletable(self, media_id: UUID) -> None:
        usage = self._lookup.lookup(media_id)
        if usage.found or usage.coverage_status is not MediaCoverageStatus.FULL:
            raise MediaStillInUseError("media usage is unresolved")
