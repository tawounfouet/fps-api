from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from fps_platform.modules.audit.domain.enums import AuditAction, AuditSource
from fps_platform.modules.identity.domain.exceptions import AuthorizationError
from fps_platform.modules.identity.domain.value_objects import PermissionCode
from fps_platform.modules.media.application.dto import (
    MediaConfirmResult,
    MediaConflictError,
    MediaNotFoundError,
)
from fps_platform.modules.media.application.services.promotion import (
    MediaPromotionService,
    MediaUnitOfWork,
    PromotionRequest,
)
from fps_platform.modules.media.domain.entities import MediaAsset
from fps_platform.modules.media.domain.enums import MediaStatus
from fps_platform.modules.media.domain.value_objects import (
    MAX_UPLOAD_ATTEMPTS,
    MimeType,
    StorageKey,
)
from fps_platform.shared.auth.principal import CurrentPrincipal
from fps_platform.shared.domain.clock import Clock

DEFAULT_CLAIM_TTL_SECONDS = 120
AUDIT_RESOURCE_TYPE = "MEDIA_ASSET"


@dataclass(frozen=True, slots=True)
class ConfirmMediaUploadCommand:
    media_id: UUID
    expected_version: int


class ConfirmMediaUploadHandler:
    def __init__(
        self,
        *,
        uow: MediaUnitOfWork,
        promotion: MediaPromotionService,
        clock: Clock,
        principal: CurrentPrincipal,
        claim_ttl_seconds: int = DEFAULT_CLAIM_TTL_SECONDS,
    ) -> None:
        self._uow = uow
        self._promotion = promotion
        self._clock = clock
        self._principal = principal
        self._claim_ttl_seconds = claim_ttl_seconds

    def handle(self, command: ConfirmMediaUploadCommand) -> MediaConfirmResult:
        if PermissionCode.MANAGE_MEDIA not in self._principal.permissions:
            raise AuthorizationError("PERMISSION_DENIED")

        asset = self._uow.media_assets.get(command.media_id)
        if asset is None:
            raise MediaNotFoundError("media asset does not exist")
        if asset.status is MediaStatus.READY:
            return _ready_result(asset)
        if command.expected_version != asset.version:
            raise MediaConflictError("media version changed")
        if asset.status is MediaStatus.ARCHIVED:
            raise MediaConflictError("archived media cannot be confirmed")
        if asset.status is MediaStatus.FAILED and asset.attempt_count >= MAX_UPLOAD_ATTEMPTS:
            raise MediaConflictError("upload attempt budget is exhausted")

        now = self._clock.now()
        owner = str(self._principal.user_id)
        claim_expires_at = now + timedelta(seconds=self._claim_ttl_seconds)

        if asset.status is MediaStatus.PROCESSING:
            if asset.claim_owner != owner:
                raise MediaConflictError("claim owner does not match")
            if asset.intent_expires_at is None or asset.intent_expires_at <= now:
                raise MediaConflictError("upload claim has expired")
            target_version = asset.version
            claim_expires_at = asset.intent_expires_at
        else:
            from_status = asset.status.value
            if asset.status is MediaStatus.FAILED:
                asset.retry(now)
            asset.claim(now, owner=owner, expires_at=claim_expires_at)
            asset.mark_processing(now)
            self._uow.media_assets.save(asset, expected_version=command.expected_version)
            self._uow.audit_recorder.record(
                action=AuditAction.MEDIA_UPLOAD_CONFIRMED,
                resource_type=AUDIT_RESOURCE_TYPE,
                resource_id=asset.id,
                metadata={"from_status": from_status, "to_status": asset.status.value},
                source=AuditSource.APPLICATION,
            )
            self._uow.commit()
            target_version = asset.version

        evidence = self._promotion.promote(
            PromotionRequest(
                asset_id=asset.id,
                destination_key=_final_key(asset.storage_key, asset.id, asset.mime_type),
                expected_version=target_version,
                claim_owner=owner,
                claim_expires_at=claim_expires_at,
            )
        )
        promoted = self._uow.media_assets.get(asset.id)
        if promoted is None or promoted.status is not MediaStatus.READY:
            raise MediaConflictError("media promotion did not reach READY")
        return MediaConfirmResult(
            media_asset_id=promoted.id,
            status=promoted.status,
            version=promoted.version,
            checksum_sha256=evidence.checksum.digest,
            failure_code=promoted.failure_code,
        )


def _ready_result(asset: MediaAsset) -> MediaConfirmResult:
    return MediaConfirmResult(
        media_asset_id=asset.id,
        status=asset.status,
        version=asset.version,
        checksum_sha256=asset.checksum.digest if asset.checksum is not None else None,
        failure_code=asset.failure_code,
    )


def _final_key(staging_key: StorageKey, asset_id: UUID, mime_type: MimeType) -> StorageKey:
    extension = str(mime_type).rsplit("/", 1)[-1]
    prefix = str(staging_key).split("/", 2)[1].replace(".", "-")
    return StorageKey(f"media/{prefix}/{asset_id}.{extension}")
