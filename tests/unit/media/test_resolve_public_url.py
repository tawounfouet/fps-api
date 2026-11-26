from __future__ import annotations

from dataclasses import replace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from fps_platform.modules.media.application.dto import (
    MediaNotFoundError,
    MediaStorageUnavailableError,
    PublicMediaUrlResult,
)
from fps_platform.modules.media.application.ports import MediaAssetRepository, MediaStoragePort
from fps_platform.modules.media.application.queries.resolve_public_url import (
    ResolvePublicMediaUrlQuery,
    resolve_public_media_url,
)
from fps_platform.modules.media.domain.entities import MediaAsset
from fps_platform.modules.media.domain.enums import ChecksumAlgorithm, MediaStatus
from fps_platform.modules.media.domain.exceptions import (
    MediaStoragePermanentError,
    MediaStorageTransientError,
)
from fps_platform.modules.media.domain.value_objects import (
    ByteSize,
    Checksum,
    MediaDimensions,
    MediaMetadata,
    MimeType,
    OriginalFileName,
)
from fps_platform.modules.media.infrastructure.public_url_resolver import (
    StorageBackedPublicUrlResolver,
)
from fps_platform.observability.metrics import (
    MetricOperation,
    MetricsRegistry,
    MetricStatus,
)
from fps_platform.shared.domain.clock import FakeClock
from tests.security.media.fixtures import FINAL_KEY, MOMENT, FakeDatabase, FakeUnitOfWork

PUBLIC_URL = "https://media.example.test/media/asset/original.jpg"
MISSING = object()


def make_asset(
    *,
    status: MediaStatus = MediaStatus.READY,
    proof: Any = MISSING,
    checksum: Any = MISSING,
    dimensions: Any = MISSING,
    verified_at: Any = MISSING,
) -> MediaAsset:
    return MediaAsset(
        id=uuid4(),
        storage_key=FINAL_KEY,
        original_filename=OriginalFileName("original.jpg"),
        mime_type=MimeType("image/jpeg"),
        byte_size=ByteSize(128),
        status=status,
        metadata=MediaMetadata(),
        uploaded_by=uuid4(),
        created_at=MOMENT,
        updated_at=MOMENT,
        version=2,
        dimensions=MediaDimensions(12, 8) if dimensions is MISSING else dimensions,
        checksum=(
            Checksum(ChecksumAlgorithm.SHA256, "a" * 64) if checksum is MISSING else checksum
        ),
        ready_at=MOMENT if status is MediaStatus.READY else None,
        promotion_proof_id=uuid4() if proof is MISSING else proof,
        detected_mime=MimeType("image/jpeg"),
        verified_at=MOMENT if verified_at is MISSING else verified_at,
    )


class StubResolver:
    def __init__(
        self,
        *,
        provider_code: str = "FAKE",
        url: str = PUBLIC_URL,
        failure: Exception | None = None,
    ) -> None:
        self.provider_code = provider_code
        self.url = url
        self.failure = failure
        self.calls: list[tuple[UUID, str, UUID]] = []

    def resolve(self, *, media_id: UUID, storage_key: str, readiness_proof_id: UUID) -> str:
        self.calls.append((media_id, storage_key, readiness_proof_id))
        if self.failure is not None:
            raise self.failure
        return self.url


def resolve(
    asset: MediaAsset | None,
    resolver: StubResolver,
    metrics: MetricsRegistry | None = None,
) -> PublicMediaUrlResult:
    database = FakeDatabase()
    if asset is not None:
        database.assets[asset.id] = asset
    uow = FakeUnitOfWork(database, FakeClock(MOMENT))
    return resolve_public_media_url(
        query=ResolvePublicMediaUrlQuery(media_id=asset.id if asset else uuid4()),
        assets=cast(MediaAssetRepository, uow.media_assets),
        resolver=resolver,
        metrics=metrics,
    )


def test_ready_asset_with_proof_resolves_stable_public_url() -> None:
    asset = make_asset()
    resolver = StubResolver()

    result = resolve(asset, resolver)

    assert result.media_id == asset.id
    assert result.url == PUBLIC_URL
    assert result.cache_control == "public, max-age=60"
    assert resolver.calls == [(asset.id, str(FINAL_KEY), asset.promotion_proof_id)]
    assert "?" not in result.url
    assert "signature" not in str(result).lower()


@pytest.mark.parametrize(
    "status",
    [MediaStatus.UPLOADING, MediaStatus.PROCESSING, MediaStatus.FAILED, MediaStatus.ARCHIVED],
)
def test_non_ready_asset_is_not_resolved(status: MediaStatus) -> None:
    with pytest.raises(MediaNotFoundError):
        resolve(make_asset(status=status), StubResolver())


def test_unknown_asset_is_not_resolved() -> None:
    with pytest.raises(MediaNotFoundError):
        resolve(None, StubResolver())


@pytest.mark.parametrize(
    "overrides",
    [
        {"proof": None},
        {"verified_at": None},
    ],
)
def test_missing_promotion_evidence_is_refused(overrides: dict[str, Any]) -> None:
    asset = make_asset(**overrides)
    resolver = StubResolver()

    with pytest.raises(MediaNotFoundError):
        resolve(asset, resolver)
    assert resolver.calls == []


class DirectAssetRepository:
    def __init__(self, asset: MediaAsset) -> None:
        self.asset = asset

    def get(self, asset_id: UUID) -> MediaAsset | None:
        return self.asset


@pytest.mark.parametrize("field", ["checksum", "dimensions"])
def test_query_refuses_asset_without_required_evidence(field: str) -> None:
    asset = make_asset()
    object.__setattr__(asset, field, None)
    resolver = StubResolver()

    with pytest.raises(MediaNotFoundError):
        resolve_public_media_url(
            query=ResolvePublicMediaUrlQuery(media_id=asset.id),
            assets=cast(MediaAssetRepository, DirectAssetRepository(asset)),
            resolver=resolver,
        )
    assert resolver.calls == []


def test_transient_provider_failure_maps_to_unavailable() -> None:
    asset = make_asset()
    resolver = StubResolver(failure=MediaStorageTransientError("provider unavailable"))

    with pytest.raises(MediaStorageUnavailableError):
        resolve(asset, resolver)


def test_unsafe_url_is_refused_without_leaking_material() -> None:
    class UnsafeStorage:
        provider_code = "FAKE"

        def resolve_public_url(self, request: object) -> str:
            return PUBLIC_URL + "?X-Amz-Signature=synthetic"

    resolver = StorageBackedPublicUrlResolver(storage=cast(MediaStoragePort, UnsafeStorage()))

    with pytest.raises(MediaStoragePermanentError) as exc_info:
        resolver.resolve(
            media_id=uuid4(),
            storage_key="media/asset/original.jpg",
            readiness_proof_id=uuid4(),
        )
    assert "synthetic" not in str(exc_info.value)
    assert "X-Amz-Signature" not in str(exc_info.value)


def test_provider_permanent_failure_maps_to_unavailable() -> None:
    asset = make_asset()
    resolver = StubResolver(failure=MediaStoragePermanentError("provider refused"))

    with pytest.raises(MediaStorageUnavailableError) as exc_info:
        resolve(asset, resolver)
    assert "provider refused" not in str(exc_info.value)


def test_provider_swap_keeps_public_identifier() -> None:
    asset = make_asset()
    first = resolve(asset, StubResolver(provider_code="FAKE"))
    second = resolve(asset, StubResolver(provider_code="S3"))

    assert first.media_id == second.media_id == asset.id
    assert first.url == second.url


def test_metrics_use_bounded_labels() -> None:
    metrics = MetricsRegistry()
    resolve(make_asset(), StubResolver(), metrics)

    samples = metrics.snapshot()
    assert len(samples) == 2
    assert all(sample.labels.status is MetricStatus.SUCCESS for sample in samples)
    assert all(sample.labels.operation is MetricOperation.RESOLVE_PUBLIC_URL for sample in samples)
    assert all(sample.labels.provider_code == "FAKE" for sample in samples)
    assert all("http" not in str(sample).lower() for sample in samples)


def test_asset_proof_is_immutable_during_resolution() -> None:
    asset = make_asset()
    before = replace(asset)

    resolve(asset, StubResolver())

    assert asset.version == before.version
    assert asset.promotion_proof_id == before.promotion_proof_id
    assert asset.status is MediaStatus.READY
