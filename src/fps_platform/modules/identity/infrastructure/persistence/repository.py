from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fps_platform.modules.identity.domain.entities import Role, User
from fps_platform.modules.identity.domain.exceptions import DuplicateExternalIdentityError
from fps_platform.modules.identity.domain.ports import RoleRepository, UserRepository
from fps_platform.modules.identity.domain.value_objects import (
    ExternalIdentity,
    RoleCode,
    UserStatus,
)
from fps_platform.modules.identity.infrastructure.persistence.mapper import (
    to_role,
    to_role_record,
    to_user,
    to_user_record,
)
from fps_platform.modules.identity.infrastructure.persistence.models import (
    RoleRecord,
    UserRecord,
    UserRoleRecord,
)
from fps_platform.shared.domain.clock import Clock
from fps_platform.shared.domain.errors import ConcurrentModificationError, ConflictError


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: Session, clock: Clock) -> None:
        self._session = session
        self._clock = clock

    def _role_ids(self, user_id: UUID) -> set[UUID]:
        statement = select(UserRoleRecord.role_id).where(UserRoleRecord.user_id == user_id)
        return set(self._session.scalars(statement))

    def add(self, user: User) -> None:
        self._session.add(to_user_record(user))
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise DuplicateExternalIdentityError("external identity already exists") from exc

    def get(self, user_id: UUID) -> User | None:
        record = self._session.get(UserRecord, user_id)
        if record is None:
            return None
        return to_user(record, self._role_ids(user_id))

    def get_by_external_identity(self, identity: ExternalIdentity) -> User | None:
        statement = select(UserRecord).where(
            UserRecord.external_issuer == identity.issuer,
            UserRecord.external_subject == identity.subject,
        )
        record = self._session.scalars(statement).first()
        if record is None:
            return None
        return to_user(record, self._role_ids(record.id))

    def list(
        self,
        *,
        limit: int,
        offset: int,
        status: UserStatus | None = None,
    ) -> Sequence[User]:
        statement = select(UserRecord)
        if status is not None:
            statement = statement.where(UserRecord.status == status.value)
        statement = (
            statement.order_by(UserRecord.created_at, UserRecord.id).limit(limit).offset(offset)
        )
        records = list(self._session.scalars(statement))
        return [to_user(record, self._role_ids(record.id)) for record in records]

    def count(self, *, status: UserStatus | None = None) -> int:
        statement = select(func.count()).select_from(UserRecord)
        if status is not None:
            statement = statement.where(UserRecord.status == status.value)
        return int(self._session.scalar(statement) or 0)

    def save(self, user: User, *, expected_version: int | None = None) -> None:
        version = expected_version if expected_version is not None else user.version - 1
        statement = (
            update(UserRecord)
            .where(UserRecord.id == user.id, UserRecord.version == version)
            .values(
                email=str(user.email),
                display_name=user.display_name,
                status=user.status.value,
                last_login_at=user.last_login_at,
                suspended_at=user.suspended_at,
                disabled_at=user.disabled_at,
                version=user.version,
                updated_at=user.updated_at,
            )
        )
        result = cast(CursorResult[Any], self._session.execute(statement))
        if result.rowcount != 1:
            raise ConcurrentModificationError("user version changed")

    def count_active_with_role(self, role_code: RoleCode) -> int:
        statement = (
            select(func.count())
            .select_from(UserRecord)
            .join(UserRoleRecord, UserRoleRecord.user_id == UserRecord.id)
            .join(RoleRecord, RoleRecord.id == UserRoleRecord.role_id)
            .where(UserRecord.status == UserStatus.ACTIVE.value, RoleRecord.code == role_code.value)
        )
        return int(self._session.scalar(statement) or 0)

    def add_role_assignment(self, user_id: UUID, role_id: UUID) -> None:
        assigned_at: datetime = self._clock.now()
        self._session.add(
            UserRoleRecord(
                user_id=user_id,
                role_id=role_id,
                assigned_at=assigned_at,
            )
        )
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise ConflictError("role assignment already exists") from exc

    def remove_role_assignment(self, user_id: UUID, role_id: UUID) -> None:
        statement = select(UserRoleRecord).where(
            UserRoleRecord.user_id == user_id,
            UserRoleRecord.role_id == role_id,
        )
        record = self._session.scalars(statement).first()
        if record is not None:
            self._session.delete(record)
            self._session.flush()

    def has_role_assignment(self, user_id: UUID, role_id: UUID) -> bool:
        statement = select(UserRoleRecord.user_id).where(
            UserRoleRecord.user_id == user_id,
            UserRoleRecord.role_id == role_id,
        )
        return self._session.scalars(statement).first() is not None


class SqlAlchemyRoleRepository(RoleRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, role: Role) -> None:
        self._session.add(to_role_record(role))
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise ConflictError("role code already exists") from exc

    def get(self, role_id: UUID) -> Role | None:
        record = self._session.get(RoleRecord, role_id)
        return None if record is None else to_role(record)

    def get_by_code(self, code: RoleCode) -> Role | None:
        statement = select(RoleRecord).where(RoleRecord.code == code.value)
        record = self._session.scalars(statement).first()
        return None if record is None else to_role(record)

    def list(self) -> Sequence[Role]:
        statement = select(RoleRecord).order_by(RoleRecord.code)
        return [to_role(record) for record in self._session.scalars(statement)]

    def list_by_ids(self, role_ids: Sequence[UUID]) -> Sequence[Role]:
        if not role_ids:
            return []
        statement = select(RoleRecord).where(RoleRecord.id.in_(role_ids))
        return [to_role(record) for record in self._session.scalars(statement)]
