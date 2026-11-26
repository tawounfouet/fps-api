from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from io import BytesIO
from struct import pack
from types import TracebackType
from typing import Self
from uuid import UUID, uuid4
from zlib import crc32

from PIL import Image
from PIL.TiffImagePlugin import IFDRational

from fps_platform.modules.audit.application.recorder import AuditRecorder
from fps_platform.modules.audit.domain.audit_event import AuditEvent
from fps_platform.modules.audit.domain.ports import AuditEventRepository
from fps_platform.modules.media.application.ports import InspectedObject
from fps_platform.modules.media.domain.entities import MediaAsset
from fps_platform.modules.media.domain.enums import MediaStatus
from fps_platform.modules.media.domain.exceptions import (
    MediaStoragePermanentError,
    MediaStorageTransientError,
)
from fps_platform.modules.media.domain.value_objects import (
    ByteSize,
    MediaMetadata,
    MimeType,
    OriginalFileName,
    StorageKey,
)
from fps_platform.modules.media.infrastructure.fake_storage import InMemoryMediaStoragePort
from fps_platform.shared.application.uow import UnitOfWork
from fps_platform.shared.domain.actor import ActorContext, ActorType
from fps_platform.shared.domain.clock import Clock
from fps_platform.shared.domain.errors import ConcurrentModificationError
from fps_platform.shared.domain.identifiers import Uuid4IdGenerator

MOMENT = datetime(2026, 6, 4, 9, 0, tzinfo=UTC)
STAGING_KEY = StorageKey("staging/worker-1/5a3c1e44-19c9-4e0e-9c0a-6d1f2a5b8c11")
FINAL_KEY = StorageKey("media/asset.jpg")


@dataclass(frozen=True, slots=True)
class ImageFixture:
    name: str
    body: bytes
    declared_type: str | None
    valid: bool


def valid_jpeg(*, with_gps: bool = False) -> bytes:
    image = Image.new("RGB", (12, 8), (46, 144, 19))
    buffer = BytesIO()
    if with_gps:
        exif = Image.Exif()
        exif[274] = 6
        gps = exif.get_ifd(34853)
        gps[1] = "N"
        gps[2] = (IFDRational(1, 1), IFDRational(2, 1), IFDRational(3, 1))
        gps[3] = "E"
        image.save(buffer, format="JPEG", exif=exif)
    else:
        image.save(buffer, format="JPEG")
    return buffer.getvalue()


def valid_png() -> bytes:
    image = Image.new("RGB", (10, 10), (87, 61, 78))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def valid_webp() -> bytes:
    image = Image.new("RGB", (9, 7), (245, 166, 23))
    buffer = BytesIO()
    image.save(buffer, format="WEBP")
    return buffer.getvalue()


def avif_structural() -> bytes:
    return pack(">I", 24) + b"ftypavif\x00\x00\x00\x00avifmif1"


def pixel_bomb_png() -> bytes:
    ihdr = pack(">IIBBBBB", 30_000, 30_000, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IEND", b"")


def corpus() -> tuple[ImageFixture, ...]:
    jpeg = valid_jpeg()
    png = valid_png()
    webp = valid_webp()
    avif = avif_structural()
    corrupted_png = bytearray(png)
    corrupted_png[30] ^= 0xFF
    return (
        ImageFixture("jpeg", jpeg, "image/jpeg", True),
        ImageFixture("png", png, "image/png", True),
        ImageFixture("webp", webp, "image/webp", True),
        ImageFixture("avif", avif, "image/avif", False),
        ImageFixture("avif_truncated", avif[:12], "image/avif", False),
        ImageFixture(
            "fake_mime_html", b"<html><body>not an image</body></html>", "image/png", False
        ),
        ImageFixture("fake_mime_png", png, "image/jpeg", False),
        ImageFixture(
            "svg",
            b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"/>',
            "image/svg+xml",
            False,
        ),
        ImageFixture("html", b"<!doctype html><html><body>x</body></html>", "text/html", False),
        ImageFixture("exif_gps", valid_jpeg(with_gps=True), "image/jpeg", False),
        ImageFixture("pixel_bomb", pixel_bomb_png(), "image/png", False),
        ImageFixture("empty", b"", "image/png", False),
        ImageFixture("truncated_jpeg", jpeg[: len(jpeg) // 2], "image/jpeg", False),
        ImageFixture("corrupted_png", bytes(corrupted_png), "image/png", False),
    )


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    return pack(">I", len(payload)) + kind + payload + pack(">I", crc32(kind + payload))


@dataclass(slots=True)
class FakeDatabase:
    assets: dict[UUID, MediaAsset] = field(default_factory=dict)
    audit_events: list[AuditEvent] = field(default_factory=list)
    commit_calls: int = 0
    fail_commit_at: int | None = None


class FakeMediaAssetRepository:
    def __init__(self, database: FakeDatabase, pending: dict[UUID, MediaAsset]) -> None:
        self._database = database
        self._pending = pending

    def add(self, asset: MediaAsset) -> None:
        self._pending[asset.id] = replace(asset)

    def get(self, asset_id: UUID) -> MediaAsset | None:
        stored = self._pending.get(asset_id) or self._database.assets.get(asset_id)
        return None if stored is None else replace(stored)

    def get_by_storage_key(self, storage_key: str) -> MediaAsset | None:
        stored = next(
            (asset for asset in self._pending.values() if str(asset.storage_key) == storage_key),
            None,
        )
        if stored is None:
            stored = next(
                (
                    asset
                    for asset in self._database.assets.values()
                    if str(asset.storage_key) == storage_key
                ),
                None,
            )
        return None if stored is None else replace(stored)

    def list(
        self,
        *,
        limit: int,
        offset: int,
        status: MediaStatus | None = None,
    ) -> Sequence[MediaAsset]:
        assets = {**self._database.assets, **self._pending}
        selected = [
            replace(asset) for asset in assets.values() if status is None or asset.status is status
        ]
        ordered = sorted(selected, key=lambda asset: (asset.created_at, str(asset.id)))
        return tuple(ordered[offset : offset + limit])

    def count(self, *, status: MediaStatus | None = None) -> int:
        assets = {**self._database.assets, **self._pending}
        return sum(1 for asset in assets.values() if status is None or asset.status is status)

    def save(self, asset: MediaAsset, *, expected_version: int | None = None) -> None:
        stored = self._pending.get(asset.id) or self._database.assets.get(asset.id)
        if stored is None:
            raise ConcurrentModificationError("media asset does not exist")
        if expected_version is not None and stored.version != expected_version:
            raise ConcurrentModificationError("media version changed")
        self._pending[asset.id] = replace(asset)


class FakeAuditEventRepository(AuditEventRepository):
    def __init__(self, pending: list[AuditEvent]) -> None:
        self._pending = pending

    def append(self, event: AuditEvent) -> None:
        self._pending.append(event)

    def get(self, event_id: UUID) -> AuditEvent | None:
        return next((event for event in self._pending if event.id == event_id), None)

    def list_by_resource(
        self, *, resource_type: str, resource_id: UUID, limit: int = 100
    ) -> list[AuditEvent]:
        return [
            event
            for event in self._pending
            if event.resource_type == resource_type and event.resource_id == resource_id
        ][:limit]


class FakeUnitOfWork(UnitOfWork):
    def __init__(self, database: FakeDatabase, clock: Clock) -> None:
        self._database = database
        self._clock = clock
        self._pending_assets: dict[UUID, MediaAsset] = {}
        self._pending_events: list[AuditEvent] = []
        self._closed = False

    @property
    def media_assets(self) -> FakeMediaAssetRepository:
        return FakeMediaAssetRepository(self._database, self._pending_assets)

    @property
    def audit_recorder(self) -> AuditRecorder:
        return AuditRecorder(
            repository=FakeAuditEventRepository(self._pending_events),
            clock=self._clock,
            id_generator=Uuid4IdGenerator(),
            actor_context=ActorContext(
                actor_type=ActorType.SYSTEM, correlation_id="test-correlation"
            ),
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.rollback()
        self._closed = True

    def commit(self) -> None:
        self._database.commit_calls += 1
        if self._database.commit_calls == self._database.fail_commit_at:
            raise RuntimeError("database commit failed")
        self._database.assets.update(self._pending_assets)
        self._database.audit_events.extend(self._pending_events)
        self._pending_assets.clear()
        self._pending_events.clear()

    def rollback(self) -> None:
        self._pending_assets.clear()
        self._pending_events.clear()


class FailingReadStorage(InMemoryMediaStoragePort):
    def read_or_inspect_object(self, key: StorageKey, *, max_bytes: int) -> InspectedObject:
        raise MediaStorageTransientError("media object inspection failed")


class CorruptingFinalStorage(InMemoryMediaStoragePort):
    def read_or_inspect_object(self, key: StorageKey, *, max_bytes: int) -> InspectedObject:
        inspected = super().read_or_inspect_object(key, max_bytes=max_bytes)
        if not str(key).startswith("media/"):
            return inspected
        altered = bytearray(inspected.body)
        altered[-1] ^= 0x01
        return replace(inspected, body=bytes(altered))


class FailingCopyStorage(InMemoryMediaStoragePort):
    def copy_object(self, *, source_key: StorageKey, destination_key: StorageKey) -> None:
        raise MediaStoragePermanentError("media destination object already exists")


def make_asset(
    *,
    status: MediaStatus = MediaStatus.UPLOADING,
    version: int = 1,
    claim_owner: str | None = None,
    attempt_count: int = 0,
    storage_key: StorageKey = STAGING_KEY,
) -> MediaAsset:
    return MediaAsset(
        id=uuid4(),
        storage_key=storage_key,
        original_filename=OriginalFileName("photo.jpg"),
        mime_type=MimeType("image/jpeg"),
        byte_size=ByteSize(128),
        status=status,
        metadata=MediaMetadata(),
        uploaded_by=uuid4(),
        created_at=MOMENT,
        updated_at=MOMENT,
        version=version,
        claim_owner=claim_owner,
        claimed_at=MOMENT if claim_owner is not None else None,
        intent_expires_at=MOMENT + timedelta(seconds=120) if claim_owner is not None else None,
        attempt_count=attempt_count,
    )


def claim_expires(clock: Clock) -> datetime:
    return clock.now() + timedelta(seconds=120)
