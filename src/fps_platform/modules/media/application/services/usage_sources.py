from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from fps_platform.modules.media.application.dto import (
    MediaNotFoundError,
    MediaUsageResult,
    MediaUsageSourceResult,
)
from fps_platform.modules.media.application.ports import MediaAssetRepository
from fps_platform.modules.media.domain.enums import MediaCoverageStatus


class MediaUsageSource(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def coverage_status(self) -> MediaCoverageStatus: ...

    def find_references(self, media_id: UUID) -> Sequence[str]: ...


@dataclass(slots=True)
class MediaUsageSourceRegistry:
    _sources: list[MediaUsageSource] = field(default_factory=list)

    def register(self, source: MediaUsageSource) -> None:
        self._sources.append(source)

    def all(self) -> tuple[MediaUsageSource, ...]:
        return tuple(self._sources)


class MediaUsageLookup:
    def __init__(
        self,
        *,
        assets: MediaAssetRepository,
        registry: MediaUsageSourceRegistry | None = None,
    ) -> None:
        self._assets = assets
        self._registry = registry if registry is not None else MediaUsageSourceRegistry()

    def lookup(self, media_id: UUID) -> MediaUsageResult:
        if self._assets.get(media_id) is None:
            raise MediaNotFoundError("media asset does not exist")
        results = tuple(self._source_result(source, media_id) for source in self._registry.all())
        coverage_status = (
            MediaCoverageStatus.FULL
            if results and all(item.coverage_status is MediaCoverageStatus.FULL for item in results)
            else MediaCoverageStatus.PARTIAL
        )
        return MediaUsageResult(
            media_id=media_id,
            coverage_status=coverage_status,
            found=any(item.found for item in results),
            sources=results,
        )

    @staticmethod
    def _source_result(source: MediaUsageSource, media_id: UUID) -> MediaUsageSourceResult:
        references = source.find_references(media_id)
        return MediaUsageSourceResult(
            source=source.name,
            coverage_status=source.coverage_status,
            found=bool(references),
            reference_count=len(references),
        )
