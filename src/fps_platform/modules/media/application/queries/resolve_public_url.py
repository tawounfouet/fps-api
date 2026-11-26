from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Protocol
from uuid import UUID

from fps_platform.modules.media.application.dto import (
    MediaNotFoundError,
    MediaStorageUnavailableError,
    PublicMediaUrlResult,
)
from fps_platform.modules.media.application.ports import MediaAssetRepository
from fps_platform.modules.media.domain.enums import MediaStatus
from fps_platform.modules.media.domain.exceptions import MediaStorageError
from fps_platform.observability.metrics import (
    MetricLabels,
    MetricName,
    MetricOperation,
    MetricsRegistry,
    MetricStatus,
    normalize_provider_code,
)


class PublicUrlResolverPort(Protocol):
    @property
    def provider_code(self) -> str: ...

    def resolve(self, *, media_id: UUID, storage_key: str, readiness_proof_id: UUID) -> str: ...


@dataclass(frozen=True, slots=True)
class ResolvePublicMediaUrlQuery:
    media_id: UUID


def resolve_public_media_url(
    *,
    query: ResolvePublicMediaUrlQuery,
    assets: MediaAssetRepository,
    resolver: PublicUrlResolverPort,
    metrics: MetricsRegistry | None = None,
) -> PublicMediaUrlResult:
    started_at = perf_counter()
    provider_code = normalize_provider_code(getattr(resolver, "provider_code", None))
    status = MetricStatus.NOT_FOUND
    try:
        asset = assets.get(query.media_id)
        if (
            asset is None
            or asset.status is not MediaStatus.READY
            or asset.ready_at is None
            or asset.promotion_proof_id is None
            or asset.verified_at is None
            or asset.checksum is None
            or asset.dimensions is None
        ):
            raise MediaNotFoundError("media asset was not found")
        url = resolver.resolve(
            media_id=asset.id,
            storage_key=str(asset.storage_key),
            readiness_proof_id=asset.promotion_proof_id,
        )
        status = MetricStatus.SUCCESS
    except MediaNotFoundError:
        raise
    except MediaStorageError:
        status = MetricStatus.UNAVAILABLE
        raise MediaStorageUnavailableError("media public URL is unavailable") from None
    except Exception:
        status = MetricStatus.INVALID
        raise
    finally:
        if metrics is not None:
            labels = MetricLabels(
                status=status,
                operation=MetricOperation.RESOLVE_PUBLIC_URL,
                provider_code=provider_code,
            )
            duration_ms = round((perf_counter() - started_at) * 1000, 3)
            metrics.record(name=MetricName.MEDIA_OPERATIONS_TOTAL, labels=labels)
            metrics.record(
                name=MetricName.MEDIA_OPERATION_DURATION_MS,
                labels=labels,
                value=duration_ms,
            )
    return PublicMediaUrlResult(media_id=query.media_id, url=url)
