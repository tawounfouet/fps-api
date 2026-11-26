from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from fps_platform.modules.audit.domain.enums import AuditAction, AuditSource
from fps_platform.modules.identity.domain.exceptions import AuthorizationError
from fps_platform.modules.identity.domain.value_objects import PermissionCode
from fps_platform.modules.media.application.dto import (
    MediaConflictError,
    MediaNotFoundError,
    MediaReadModel,
    MediaStorageUnavailableError,
    project_media,
)
from fps_platform.modules.media.application.ports import MediaStoragePort
from fps_platform.modules.media.application.services.promotion import (
    MAX_IMAGE_BYTES,
    MediaUnitOfWork,
)
from fps_platform.modules.media.domain.entities import MediaAsset
from fps_platform.modules.media.domain.enums import MediaStatus
from fps_platform.modules.media.domain.exceptions import (
    InvalidMediaObjectError,
    InvalidMediaTransitionError,
    MediaStorageError,
)
from fps_platform.modules.media.domain.value_objects import PromotionEvidence
from fps_platform.shared.auth.principal import CurrentPrincipal
from fps_platform.shared.domain.clock import Clock
from fps_platform.shared.domain.errors import ConcurrentModificationError

AUDIT_RESOURCE_TYPE = "MEDIA_ASSET"
FINAL_KEY_PREFIX = "media/"


@dataclass(frozen=True, slots=True)
class RestoreMediaCommand:
    media_id: UUID
    expected_version: int | None = None


class RestoreMediaHandler:
    def __init__(
        self,
        *,
        uow: MediaUnitOfWork,
        storage: MediaStoragePort,
        clock: Clock,
        principal: CurrentPrincipal,
        max_bytes: int = MAX_IMAGE_BYTES,
    ) -> None:
        self._uow = uow
        self._storage = storage
        self._clock = clock
        self._principal = principal
        self._max_bytes = max_bytes

    def handle(self, command: RestoreMediaCommand) -> MediaReadModel:
        if PermissionCode.MANAGE_MEDIA not in self._principal.permissions:
            raise AuthorizationError("PERMISSION_DENIED")

        asset = self._uow.media_assets.get(command.media_id)
        if asset is None:
            raise MediaNotFoundError("media asset does not exist")
        expected_version = (
            command.expected_version if command.expected_version is not None else asset.version
        )
        if asset.version != expected_version:
            raise MediaConflictError("media version changed")
        if asset.status is not MediaStatus.ARCHIVED:
            raise MediaConflictError("only ARCHIVED media can be restored")

        evidence = _promotion_evidence(asset)
        self._verify_final_object(evidence)

        from_status = asset.status.value
        try:
            asset.restore(self._clock.now(), evidence=evidence)
        except (InvalidMediaTransitionError, InvalidMediaObjectError) as exc:
            raise MediaConflictError("media cannot be restored") from exc
        try:
            self._uow.media_assets.save(asset, expected_version=expected_version)
        except ConcurrentModificationError as exc:
            raise MediaConflictError("media version changed") from exc

        self._uow.audit_recorder.record(
            action=AuditAction.MEDIA_RESTORED,
            resource_type=AUDIT_RESOURCE_TYPE,
            resource_id=asset.id,
            metadata={"from_status": from_status, "to_status": asset.status.value},
            source=AuditSource.APPLICATION,
        )
        self._uow.commit()
        return project_media(asset)

    def _verify_final_object(self, evidence: PromotionEvidence) -> None:
        key = evidence.storage_key
        try:
            head = self._storage.head_object(key)
            if (
                not head.exists
                or head.byte_size is None
                or head.byte_size <= 0
                or head.byte_size != evidence.byte_size.value
                or head.byte_size > self._max_bytes
            ):
                raise MediaConflictError("final object does not match promotion evidence")
            allowed_types = {str(evidence.detected_mime), str(evidence.detected_mime.value)}
            if head.content_type is not None and head.content_type not in allowed_types:
                raise MediaConflictError("final object content type does not match evidence")
            final = self._storage.read_or_inspect_object(key, max_bytes=self._max_bytes)
        except MediaStorageError as exc:
            raise MediaStorageUnavailableError("final object could not be verified") from exc
        if (
            final.truncated
            or final.byte_size != head.byte_size
            or len(final.body) != final.byte_size
            or sha256(final.body).hexdigest() != evidence.checksum.digest
        ):
            raise MediaConflictError("final object does not match promotion evidence")


def _promotion_evidence(asset: MediaAsset) -> PromotionEvidence:
    if not str(asset.storage_key).startswith(FINAL_KEY_PREFIX):
        raise MediaConflictError("promotion evidence does not point to a final object")
    if (
        asset.promotion_proof_id is None
        or asset.promotion_proof_id.int == 0
        or asset.detected_mime is None
        or asset.dimensions is None
        or asset.checksum is None
        or asset.verified_at is None
    ):
        raise MediaConflictError("promotion evidence is incomplete")
    try:
        return PromotionEvidence(
            proof_id=asset.promotion_proof_id,
            storage_key=asset.storage_key,
            detected_mime=asset.detected_mime,
            byte_size=asset.byte_size,
            dimensions=asset.dimensions,
            checksum=asset.checksum,
            verified_at=asset.verified_at,
        )
    except ValueError as exc:
        raise MediaConflictError("promotion evidence is inconsistent") from exc
