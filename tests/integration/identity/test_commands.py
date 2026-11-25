from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from fps_platform.modules.audit.domain.enums import AuditAction
from fps_platform.modules.identity.application.commands import (
    ActivateUserCommand,
    AssignRoleCommand,
    BootstrapSuperAdminCommand,
    DisableUserCommand,
    SeedRolesCommand,
    SuspendUserCommand,
)
from fps_platform.modules.identity.application.handlers import (
    activate_user,
    assign_role,
    bootstrap_super_admin,
    disable_user,
    seed_roles,
    suspend_user,
)
from fps_platform.modules.identity.domain.entities import User
from fps_platform.modules.identity.domain.exceptions import LastSuperAdminViolationError
from fps_platform.modules.identity.domain.value_objects import (
    EmailAddress,
    ExternalIdentity,
    ReasonCode,
    RoleCode,
    UserStatus,
)
from fps_platform.shared.domain.clock import FakeClock
from fps_platform.shared.infrastructure.persistence.uow import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration
NOW = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
MakeUow = Callable[..., SqlAlchemyUnitOfWork]


def test_iam_commands_and_last_super_admin_guard(make_uow: MakeUow) -> None:
    clock = FakeClock(NOW)
    with make_uow(clock=clock) as uow:
        seed_roles(uow, SeedRolesCommand())
        bootstrap = bootstrap_super_admin(
            uow,
            BootstrapSuperAdminCommand(
                issuer="https://idp.example.test",
                subject="super-admin-1",
                email="super@example.test",
                display_name="Super Admin",
            ),
        )
        editor = User(
            id=uuid4(),
            external_identity=ExternalIdentity("https://idp.example.test", "editor-1"),
            email=EmailAddress("editor@example.test"),
            display_name="Editor",
            status=UserStatus.ACTIVE,
            created_at=clock.now(),
            updated_at=clock.now(),
        )
        uow.users.add(editor)
        assigned = assign_role(
            uow,
            AssignRoleCommand(user_id=editor.id, role_code=RoleCode.EDITOR),
        )
        uow.commit()
    assert bootstrap.created is True
    assert assigned.changed is True

    with make_uow(clock=clock) as uow:
        with pytest.raises(LastSuperAdminViolationError):
            suspend_user(
                uow,
                SuspendUserCommand(
                    user_id=bootstrap.user_id,
                    reason_code=ReasonCode("lockout_test"),
                ),
            )
        suspended = suspend_user(
            uow,
            SuspendUserCommand(
                user_id=editor.id,
                reason_code=ReasonCode("temporary_review"),
            ),
        )
        uow.commit()
    assert suspended.changed is True

    with make_uow(clock=clock) as uow:
        activated = activate_user(
            uow,
            ActivateUserCommand(
                user_id=editor.id,
                reason_code=ReasonCode("review_complete"),
            ),
        )
        disabled = disable_user(
            uow,
            DisableUserCommand(
                user_id=editor.id,
                reason_code=ReasonCode("offboarding"),
            ),
        )
        uow.commit()
    assert activated.changed is True
    assert disabled.changed is True

    with make_uow(clock=clock) as uow:
        events = uow.audit_events.list_by_resource(
            resource_type="User", resource_id=editor.id, limit=50
        )
    actions = {event.action for event in events}
    assert AuditAction.ROLE_ASSIGNED in actions
    assert AuditAction.USER_SUSPENDED in actions
    assert AuditAction.USER_ACTIVATED in actions
    assert AuditAction.USER_DISABLED in actions
