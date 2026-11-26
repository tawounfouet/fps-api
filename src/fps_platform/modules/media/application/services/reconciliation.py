from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from fps_platform.modules.media.application.dto import (
    ReconciliationFinding,
    ReconciliationFindingCode,
    ReconciliationReport,
)
from fps_platform.modules.media.application.ports import (
    MediaAssetRepository,
    MediaStoragePort,
)
from fps_platform.modules.media.domain.entities import MediaAsset
from fps_platform.modules.media.domain.enums import MediaStatus
from fps_platform.modules.media.domain.exceptions import MediaStorageError
from fps_platform.modules.media.domain.value_objects import MAX_UPLOAD_ATTEMPTS
from fps_platform.shared.domain.clock import Clock

DEFAULT_STALLED_AFTER_SECONDS = 3600
DEFAULT_PAGE_SIZE = 100
MAX_PAGES = 1000


@dataclass(frozen=True, slots=True)
class ObjectListing:
    key: str
    byte_size: int | None = None

    def __post_init__(self) -> None:
        if (
            not self.key
            or len(self.key) > 512
            or any(character.isspace() for character in self.key)
        ):
            raise ValueError("object listing key is invalid")


class StorageObjectCatalog(Protocol):
    def list(self, *, prefix: str) -> Sequence[ObjectListing]: ...


class FakeStorageObjectCatalog:
    def __init__(self, storage: MediaStoragePort) -> None:
        self._storage = storage

    def list(self, *, prefix: str) -> Sequence[ObjectListing]:
        objects = getattr(self._storage, "_objects", None)
        if not isinstance(objects, dict):
            return ()
        listings: list[ObjectListing] = []
        for key, value in objects.items():
            name = str(key)
            if not name.startswith(prefix):
                continue
            body = getattr(value, "body", None)
            byte_size = len(body) if isinstance(body, bytes) else None
            listings.append(ObjectListing(key=name, byte_size=byte_size))
        return tuple(sorted(listings, key=lambda item: item.key))


@dataclass(frozen=True, slots=True)
class ReconciliationService:
    assets: MediaAssetRepository
    storage: MediaStoragePort
    catalog: StorageObjectCatalog
    clock: Clock
    stalled_after_seconds: int = DEFAULT_STALLED_AFTER_SECONDS
    page_size: int = DEFAULT_PAGE_SIZE

    def __post_init__(self) -> None:
        if self.stalled_after_seconds < 1 or self.stalled_after_seconds > 86_400 * 30:
            raise ValueError("stalled_after_seconds is out of range")
        if not 1 <= self.page_size <= 100:
            raise ValueError("page_size is out of range")

    def run(self) -> ReconciliationReport:
        assets = self._load_assets()
        objects = tuple(self.catalog.list(prefix=""))
        known_keys = {str(asset.storage_key) for asset in assets}
        findings: list[ReconciliationFinding] = []
        now = self.clock.now()

        for asset in assets:
            findings.extend(self._inspect_asset(asset, now))
        for obj in objects:
            if obj.key.startswith("staging/") and obj.key not in known_keys:
                findings.append(ReconciliationFinding(code=ReconciliationFindingCode.ORPHAN_OBJECT))

        return ReconciliationReport(
            dry_run=True,
            scanned_assets=len(assets),
            scanned_objects=len(objects),
            findings=tuple(
                sorted(
                    findings,
                    key=lambda item: (
                        item.code.value,
                        str(item.media_id) if item.media_id is not None else "",
                    ),
                )
            ),
        )

    def _load_assets(self) -> tuple[MediaAsset, ...]:
        assets: list[MediaAsset] = []
        for _page in range(MAX_PAGES):
            batch = self.assets.list(limit=self.page_size, offset=len(assets))
            if not batch:
                break
            assets.extend(batch)
        return tuple(assets)

    def _inspect_asset(self, asset: MediaAsset, now: datetime) -> tuple[ReconciliationFinding, ...]:
        findings: list[ReconciliationFinding] = []
        current = now.astimezone(UTC)
        if asset.status is MediaStatus.UPLOADING:
            expires_at = asset.intent_expires_at
            if expires_at is not None and expires_at < current:
                if asset.attempt_count >= MAX_UPLOAD_ATTEMPTS:
                    findings.append(
                        ReconciliationFinding(
                            code=ReconciliationFindingCode.ATTEMPT_BUDGET_EXHAUSTED,
                            media_id=asset.id,
                            observed=asset.attempt_count,
                            recommended_status=MediaStatus.FAILED,
                        )
                    )
                else:
                    findings.append(
                        ReconciliationFinding(
                            code=ReconciliationFindingCode.UPLOADING_EXPIRED,
                            media_id=asset.id,
                            observed=asset.attempt_count,
                        )
                    )
        if asset.status is MediaStatus.PROCESSING:
            age_seconds = int((current - asset.updated_at).total_seconds())
            if age_seconds >= self.stalled_after_seconds:
                findings.append(
                    ReconciliationFinding(
                        code=ReconciliationFindingCode.PROCESSING_STALLED,
                        media_id=asset.id,
                        observed=max(age_seconds, 0),
                    )
                )
        if asset.status is MediaStatus.READY:
            findings.extend(self._inspect_ready(asset))
        return tuple(findings)

    def _inspect_ready(self, asset: MediaAsset) -> tuple[ReconciliationFinding, ...]:
        try:
            head = self.storage.head_object(asset.storage_key)
        except MediaStorageError:
            return (
                ReconciliationFinding(
                    code=ReconciliationFindingCode.STORAGE_UNAVAILABLE,
                    media_id=asset.id,
                ),
            )
        if not head.exists:
            return (
                ReconciliationFinding(
                    code=ReconciliationFindingCode.MISSING_OBJECT,
                    media_id=asset.id,
                ),
            )
        if head.byte_size is None or head.byte_size != asset.byte_size.value:
            return (
                ReconciliationFinding(
                    code=ReconciliationFindingCode.SIZE_MISMATCH,
                    media_id=asset.id,
                    observed=max(head.byte_size or 0, 0),
                ),
            )
        return ()


def report_to_mapping(report: ReconciliationReport) -> dict[str, object]:
    return {
        "dry_run": report.dry_run,
        "scanned_assets": report.scanned_assets,
        "scanned_objects": report.scanned_objects,
        "findings": [
            {
                "code": finding.code.value,
                "media_id": str(finding.media_id) if finding.media_id is not None else None,
                "observed": finding.observed,
                "recommended_status": (
                    finding.recommended_status.value
                    if finding.recommended_status is not None
                    else None
                ),
            }
            for finding in report.findings
        ],
    }
