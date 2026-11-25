from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from fps_platform.modules.identity.application.ports import IdentityUnitOfWork
from fps_platform.modules.identity.domain.entities import Role, User
from fps_platform.modules.identity.domain.exceptions import RoleNotFoundError, UserNotFoundError
from fps_platform.modules.identity.domain.value_objects import UserStatus


def list_users(
    uow: IdentityUnitOfWork,
    *,
    limit: int,
    offset: int,
    status: UserStatus | None = None,
) -> Sequence[User]:
    return uow.users.list(limit=limit, offset=offset, status=status)


def count_users(uow: IdentityUnitOfWork, *, status: UserStatus | None = None) -> int:
    return uow.users.count(status=status)


def get_user(uow: IdentityUnitOfWork, user_id: UUID) -> User:
    user = uow.users.get(user_id)
    if user is None:
        raise UserNotFoundError(user_id)
    return user


def list_roles(uow: IdentityUnitOfWork) -> Sequence[Role]:
    return uow.roles.list()


def get_role(uow: IdentityUnitOfWork, role_id: UUID) -> Role:
    role = uow.roles.get(role_id)
    if role is None:
        raise RoleNotFoundError(role_id=role_id)
    return role
