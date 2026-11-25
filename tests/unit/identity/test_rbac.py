from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from fps_platform.modules.identity.domain.entities import User
from fps_platform.modules.identity.domain.exceptions import InvalidUserTransitionError
from fps_platform.modules.identity.domain.permissions import permissions_for
from fps_platform.modules.identity.domain.value_objects import (
    EmailAddress,
    ExternalIdentity,
    PermissionCode,
    RoleCode,
    UserStatus,
)

NOW = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)


def status_value(user: User) -> str:
    return user.status.value


def make_user(*, status: UserStatus = UserStatus.ACTIVE) -> User:
    return User(
        id=uuid4(),
        external_identity=ExternalIdentity("https://idp.example.test", "subject-1"),
        email=EmailAddress("user@example.test"),
        display_name="Test User",
        status=status,
        created_at=NOW,
        updated_at=NOW,
    )


def test_super_admin_has_every_permission() -> None:
    permissions = permissions_for([RoleCode.SUPER_ADMIN])
    assert permissions == frozenset(PermissionCode)


def test_viewer_permissions_are_read_only() -> None:
    permissions = permissions_for([RoleCode.VIEWER])
    assert permissions == frozenset({PermissionCode.VIEW_DRAFTS, PermissionCode.VIEW_MEDIA})


def test_contacts_are_restricted_to_super_admin() -> None:
    for role in (RoleCode.CONTENT_ADMIN, RoleCode.EDITOR, RoleCode.VIEWER):
        assert PermissionCode.VIEW_CONTACTS not in permissions_for([role])


def test_user_status_transitions() -> None:
    user = make_user()
    user.suspend(NOW)
    assert status_value(user) == "SUSPENDED"
    user.activate(NOW)
    assert status_value(user) == "ACTIVE"
    assert user.suspended_at is None
    user.disable(NOW)
    assert status_value(user) == "DISABLED"


def test_suspended_user_cannot_change_roles() -> None:
    user = make_user(status=UserStatus.SUSPENDED)
    with pytest.raises(InvalidUserTransitionError):
        user.assign_role(uuid4(), NOW)


def test_every_mutation_increments_version() -> None:
    user = make_user()
    role_id = uuid4()
    user.assign_role(role_id, NOW)
    assert user.version == 2
    user.remove_role(role_id, NOW)
    assert user.version == 3
    user.suspend(NOW)
    assert user.version == 4
