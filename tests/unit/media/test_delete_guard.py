from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from fps_platform.modules.identity.domain.exceptions import AuthorizationError
from fps_platform.modules.identity.domain.value_objects import RoleCode
from fps_platform.modules.media.application.dto import (
    MediaErrorCode,
    MediaNotFoundError,
    MediaStillInUseError,
)
from fps_platform.modules.media.application.queries.get_media_usage import (
    GetMediaUsageQuery,
    get_media_usage,
)
from fps_platform.modules.media.application.services.delete_guard import (
    DELETE_MEDIA,
    DeleteGuard,
    DeleteMediaCommand,
)
from fps_platform.modules.media.application.services.usage_sources import (
    MediaUsageLookup,
    MediaUsageSourceRegistry,
)
from fps_platform.modules.media.domain.enums import MediaCoverageStatus
from fps_platform.modules.media.infrastructure.fake_storage import InMemoryMediaStoragePort
from fps_platform.shared.domain.clock import FakeClock
from tests.api.identity.test_admin import make_principal
from tests.security.media.fixtures import (
    FINAL_KEY,
    MOMENT,
    FakeDatabase,
    FakeUnitOfWork,
    make_asset,
)

ADMIN = make_principal(roles=(RoleCode.SUPER_ADMIN,))
VIEWER = make_principal(roles=(RoleCode.VIEWER,))
NO_ROLE = make_principal(roles=())


@dataclass(frozen=True, slots=True)
class StaticSource:
    name: str
    coverage_status: MediaCoverageStatus = MediaCoverageStatus.PARTIAL
    references: tuple[str, ...] = ()

    def find_references(self, media_id: UUID) -> Sequence[str]:
        return self.references


class NoDeleteStorage(InMemoryMediaStoragePort):
    def delete_object(self, request: object) -> None:
        raise AssertionError("delete_object must never be called by the delete guard")


def build(
    *, sources: tuple[StaticSource, ...] = (), asset_id: UUID | None = None
) -> tuple[MediaUsageLookup, FakeDatabase, UUID]:
    database = FakeDatabase()
    asset = make_asset()
    if asset_id is not None:
        asset.id = asset_id
    database.assets[asset.id] = asset
    registry = MediaUsageSourceRegistry()
    for source in sources:
        registry.register(source)
    lookup = MediaUsageLookup(
        assets=FakeUnitOfWork(database, FakeClock(MOMENT)).media_assets, registry=registry
    )
    return lookup, database, asset.id


def test_default_registry_is_partial_and_refuses_deletion() -> None:
    lookup, _, media_id = build()
    guard = DeleteGuard(lookup=lookup)

    usage = lookup.lookup(media_id)
    assert usage.coverage_status is MediaCoverageStatus.PARTIAL
    assert usage.found is False
    assert usage.sources == ()

    with pytest.raises(MediaStillInUseError) as exc_info:
        guard.assert_deletable(media_id)
    assert exc_info.value.code == str(MediaErrorCode.MEDIA_STILL_IN_USE)


def test_full_coverage_without_usage_allows_deletion_decision_only() -> None:
    lookup, _, media_id = build(sources=(StaticSource("content-db", MediaCoverageStatus.FULL),))
    storage = NoDeleteStorage(FakeClock(MOMENT))
    storage.put_object(FINAL_KEY, b"bytes", "image/jpeg")

    usage = lookup.lookup(media_id)
    assert usage.coverage_status is MediaCoverageStatus.FULL
    assert usage.found is False
    assert usage.sources[0].reference_count == 0

    DeleteGuard(lookup=lookup).assert_deletable(media_id)
    assert storage.head_object(FINAL_KEY).exists


def test_found_usage_refuses_deletion_even_with_full_coverage() -> None:
    lookup, _, media_id = build(
        sources=(StaticSource("content-db", MediaCoverageStatus.FULL, ("page-1", "page-2")),)
    )

    usage = lookup.lookup(media_id)
    assert usage.found is True
    assert usage.sources[0].reference_count == 2

    with pytest.raises(MediaStillInUseError):
        DeleteGuard(lookup=lookup).assert_deletable(media_id)


@pytest.mark.parametrize(
    "sources",
    [
        (StaticSource("partial-source"),),
        (
            StaticSource("full-source", MediaCoverageStatus.FULL),
            StaticSource("partial-source"),
        ),
    ],
)
def test_partial_coverage_refuses_deletion(sources: tuple[StaticSource, ...]) -> None:
    lookup, _, media_id = build(sources=sources)

    assert lookup.lookup(media_id).coverage_status is MediaCoverageStatus.PARTIAL
    with pytest.raises(MediaStillInUseError):
        DeleteGuard(lookup=lookup).assert_deletable(media_id)


def test_delete_media_command_is_distinct_and_not_a_route() -> None:
    media_id = uuid4()
    command = DeleteMediaCommand(media_id=media_id)

    assert command.action == DELETE_MEDIA
    assert command.media_id == media_id


def test_usage_query_requires_view_media_and_existing_asset() -> None:
    lookup, _, media_id = build()

    result = get_media_usage(
        lookup=lookup, principal=VIEWER, query=GetMediaUsageQuery(media_id=media_id)
    )
    assert result.media_id == media_id

    with pytest.raises(AuthorizationError):
        get_media_usage(
            lookup=lookup, principal=NO_ROLE, query=GetMediaUsageQuery(media_id=media_id)
        )
    with pytest.raises(MediaNotFoundError):
        get_media_usage(lookup=lookup, principal=ADMIN, query=GetMediaUsageQuery(media_id=uuid4()))
    with pytest.raises(MediaNotFoundError):
        DeleteGuard(lookup=lookup).assert_deletable(uuid4())
