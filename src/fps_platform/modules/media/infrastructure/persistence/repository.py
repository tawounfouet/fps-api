from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fps_platform.modules.media.domain.entities import MediaAsset
from fps_platform.modules.media.domain.enums import MediaStatus
from fps_platform.modules.media.infrastructure.persistence.mapper import (
    to_media_asset,
    to_media_asset_record,
)
from fps_platform.modules.media.infrastructure.persistence.models import MediaAssetRecord
from fps_platform.shared.domain.errors import ConcurrentModificationError, ConflictError


class SqlAlchemyMediaAssetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, asset: MediaAsset) -> None:
        self._session.add(to_media_asset_record(asset))
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise ConflictError("media asset could not be added") from exc

    def get(self, asset_id: UUID) -> MediaAsset | None:
        record = self._session.get(MediaAssetRecord, asset_id)
        return None if record is None else to_media_asset(record)

    def get_by_storage_key(self, storage_key: str) -> MediaAsset | None:
        statement = select(MediaAssetRecord).where(MediaAssetRecord.storage_key == storage_key)
        record = self._session.scalars(statement).first()
        return None if record is None else to_media_asset(record)

    def list(
        self,
        *,
        limit: int,
        offset: int,
        status: MediaStatus | None = None,
    ) -> Sequence[MediaAsset]:
        statement = select(MediaAssetRecord)
        if status is not None:
            statement = statement.where(MediaAssetRecord.status == status.value)
        statement = (
            statement.order_by(MediaAssetRecord.created_at.desc(), MediaAssetRecord.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return [to_media_asset(record) for record in self._session.scalars(statement)]

    def count(self, *, status: MediaStatus | None = None) -> int:
        statement = select(func.count()).select_from(MediaAssetRecord)
        if status is not None:
            statement = statement.where(MediaAssetRecord.status == status.value)
        return int(self._session.scalar(statement) or 0)

    def save(self, asset: MediaAsset, *, expected_version: int | None = None) -> None:
        version = expected_version if expected_version is not None else asset.version - 1
        record = to_media_asset_record(asset)
        statement = (
            update(MediaAssetRecord)
            .where(
                MediaAssetRecord.id == asset.id,
                MediaAssetRecord.version == version,
            )
            .values(
                storage_key=record.storage_key,
                original_filename=record.original_filename,
                mime_type=record.mime_type,
                byte_size=record.byte_size,
                width=record.width,
                height=record.height,
                checksum_algorithm=record.checksum_algorithm,
                checksum_digest=record.checksum_digest,
                status=record.status,
                title=record.title,
                alt_texts=record.alt_texts,
                captions=record.captions,
                attribution=record.attribution,
                updated_at=record.updated_at,
                ready_at=record.ready_at,
                archived_at=record.archived_at,
                version=record.version,
                intent_expires_at=record.intent_expires_at,
                claimed_at=record.claimed_at,
                claim_owner=record.claim_owner,
                attempt_count=record.attempt_count,
                failure_code=record.failure_code,
                detected_mime=record.detected_mime,
                promotion_proof_id=record.promotion_proof_id,
                promoted_at=record.promoted_at,
                verified_at=record.verified_at,
            )
        )
        result = cast(CursorResult[Any], self._session.execute(statement))
        if result.rowcount != 1:
            raise ConcurrentModificationError("media version changed")
