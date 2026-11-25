from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Any, TypeGuard, cast
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from fps_platform.shared.domain.errors import (
    ConcurrentModificationError,
    ConflictError,
    NotFoundError,
)
from fps_platform.shared.infrastructure.persistence.naming import create_metadata

type ProbeMetadataValue = str | int | bool


def is_probe_metadata_value(value: object) -> TypeGuard[ProbeMetadataValue]:
    return isinstance(value, (bool, int, str))


class ProbeBase(DeclarativeBase):
    metadata = create_metadata()


class ProbeParentRecord(ProbeBase):
    __tablename__ = "persistence_probe_parents"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)


class PersistenceProbeRecord(ProbeBase):
    __tablename__ = "persistence_probes"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    parent_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("persistence_probe_parents.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (CheckConstraint("version > 0", name="version_positive"),)


@dataclass(frozen=True, slots=True)
class ProbeParent:
    id: UUID
    code: str


@dataclass(frozen=True, slots=True)
class PersistenceProbe:
    id: UUID
    parent_id: UUID
    code: str
    version: int
    metadata: Mapping[str, ProbeMetadataValue]
    created_at: datetime

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("probe version must be positive")
        if not self.code or len(self.code) > 64:
            raise ValueError("probe code is invalid")


def to_domain(record: PersistenceProbeRecord) -> PersistenceProbe:
    raw = {key: value for key, value in (record.metadata_ or {}).items()}
    metadata = {key: value for key, value in raw.items() if is_probe_metadata_value(value)}
    return PersistenceProbe(
        id=record.id,
        parent_id=record.parent_id,
        code=record.code,
        version=record.version,
        metadata=MappingProxyType(metadata),
        created_at=record.created_at,
    )


class PersistenceProbeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_parent(self, parent: ProbeParent) -> None:
        self._session.add(ProbeParentRecord(id=parent.id, code=parent.code))
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise ConflictError("Probe parent could not be added") from exc

    def add(self, probe: PersistenceProbe) -> None:
        self._session.add(
            PersistenceProbeRecord(
                id=probe.id,
                parent_id=probe.parent_id,
                code=probe.code,
                version=probe.version,
                metadata_=dict(probe.metadata),
                created_at=probe.created_at,
            )
        )
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise ConflictError("Probe could not be added") from exc

    def get(self, probe_id: UUID) -> PersistenceProbe | None:
        record = self._session.get(PersistenceProbeRecord, probe_id)
        return None if record is None else to_domain(record)

    def update_code(self, *, probe_id: UUID, expected_version: int, code: str) -> PersistenceProbe:
        statement = (
            update(PersistenceProbeRecord)
            .where(
                PersistenceProbeRecord.id == probe_id,
                PersistenceProbeRecord.version == expected_version,
            )
            .values(code=code, version=expected_version + 1)
        )
        result = cast(CursorResult[Any], self._session.execute(statement))
        if result.rowcount != 1:
            if self._session.get(PersistenceProbeRecord, probe_id) is None:
                raise NotFoundError("Probe does not exist")
            raise ConcurrentModificationError("Probe version changed")
        self._session.flush()
        record = self._session.get(PersistenceProbeRecord, probe_id)
        if record is None:
            raise NotFoundError("Probe does not exist")
        return to_domain(record)
