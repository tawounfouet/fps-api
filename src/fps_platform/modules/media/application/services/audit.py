from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from uuid import UUID, uuid5

from fps_platform.modules.audit.domain.audit_event import AuditMetadataValue
from fps_platform.modules.audit.domain.enums import AuditAction, AuditSource
from fps_platform.modules.media.application.services.promotion import MediaUnitOfWork

AUDIT_RESOURCE_TYPE = "MEDIA_ASSET"
RECONCILIATION_RESOURCE_TYPE = "MEDIA_RECONCILIATION"
RECONCILIATION_RESOURCE_ID = uuid5(
    UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8"), RECONCILIATION_RESOURCE_TYPE
)


@dataclass(frozen=True, slots=True)
class MediaAuditService:
    uow_factory: Callable[[], MediaUnitOfWork]

    def record(
        self,
        *,
        action: AuditAction,
        resource_type: str,
        resource_id: UUID,
        metadata: Mapping[str, AuditMetadataValue] | None = None,
        source: AuditSource = AuditSource.SYSTEM,
    ) -> None:
        with self.uow_factory() as uow:
            uow.audit_recorder.record(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                metadata=metadata or {},
                source=source,
            )
            uow.commit()

    def record_reconciliation_report(self, *, finding_count: int, dry_run: bool) -> None:
        self.record(
            action=AuditAction.MEDIA_RECONCILIATION_REPORTED,
            resource_type=RECONCILIATION_RESOURCE_TYPE,
            resource_id=RECONCILIATION_RESOURCE_ID,
            metadata={"finding_count": finding_count, "dry_run": dry_run},
            source=AuditSource.WORKER,
        )
