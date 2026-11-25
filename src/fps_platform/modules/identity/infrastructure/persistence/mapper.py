from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from fps_platform.modules.identity.domain.entities import Role, User
from fps_platform.modules.identity.domain.value_objects import (
    EmailAddress,
    ExternalIdentity,
    RoleCode,
    UserStatus,
)
from fps_platform.modules.identity.infrastructure.persistence.models import (
    RoleRecord,
    UserRecord,
)


def to_user(record: UserRecord, role_ids: Iterable[UUID]) -> User:
    return User(
        id=record.id,
        external_identity=ExternalIdentity(record.external_issuer, record.external_subject),
        email=EmailAddress(record.email),
        display_name=record.display_name,
        status=UserStatus(record.status),
        role_ids=set(role_ids),
        created_at=record.created_at,
        updated_at=record.updated_at,
        last_login_at=record.last_login_at,
        suspended_at=record.suspended_at,
        disabled_at=record.disabled_at,
        version=record.version,
    )


def to_user_record(user: User) -> UserRecord:
    return UserRecord(
        id=user.id,
        external_issuer=user.external_identity.issuer,
        external_subject=user.external_identity.subject,
        email=str(user.email),
        display_name=user.display_name,
        status=user.status.value,
        last_login_at=user.last_login_at,
        suspended_at=user.suspended_at,
        disabled_at=user.disabled_at,
        version=user.version,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def to_role(record: RoleRecord) -> Role:
    return Role(
        id=record.id,
        code=RoleCode(record.code),
        name=record.name,
        description=record.description,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def to_role_record(role: Role) -> RoleRecord:
    return RoleRecord(
        id=role.id,
        code=role.code.value,
        name=role.name,
        description=role.description,
        created_at=role.created_at,
        updated_at=role.updated_at,
    )
