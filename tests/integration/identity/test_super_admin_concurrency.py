from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import UUID

import pytest

from fps_platform.modules.audit.domain.enums import AuditAction
from fps_platform.modules.identity.application.commands import (
    AssignRoleCommand,
    RemoveRoleCommand,
    SeedRolesCommand,
)
from fps_platform.modules.identity.application.handlers import assign_role, remove_role, seed_roles
from fps_platform.modules.identity.domain.entities import User
from fps_platform.modules.identity.domain.exceptions import LastSuperAdminViolationError
from fps_platform.modules.identity.domain.value_objects import (
    EmailAddress,
    ExternalIdentity,
    RoleCode,
    UserStatus,
)
from fps_platform.shared.domain.clock import FakeClock
from fps_platform.shared.infrastructure.persistence.uow import SqlAlchemyUnitOfWork

pytestmark = pytest.mark.integration

NOW = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
MakeUow = Callable[..., SqlAlchemyUnitOfWork]
Outcome = tuple[str, UUID, str]


def test_two_super_admin_removals_accept_one_change_and_reject_one(make_uow: MakeUow) -> None:
    clock = FakeClock(NOW)
    with make_uow(clock=clock) as uow:
        seed_roles(uow, SeedRolesCommand())
        first = User(
            id=UUID("11111111-1111-4111-8111-111111111111"),
            external_identity=ExternalIdentity("https://idp.example.test", "super-admin-1"),
            email=EmailAddress("admin-one@example.test"),
            display_name="Admin One",
            status=UserStatus.ACTIVE,
            created_at=clock.now(),
            updated_at=clock.now(),
        )
        second = User(
            id=UUID("22222222-2222-4222-8222-222222222222"),
            external_identity=ExternalIdentity("https://idp.example.test", "super-admin-2"),
            email=EmailAddress("admin-two@example.test"),
            display_name="Admin Two",
            status=UserStatus.ACTIVE,
            created_at=clock.now(),
            updated_at=clock.now(),
        )
        uow.users.add(first)
        uow.users.add(second)
        assign_role(
            uow,
            AssignRoleCommand(user_id=first.id, role_code=RoleCode.SUPER_ADMIN),
        )
        assign_role(
            uow,
            AssignRoleCommand(user_id=second.id, role_code=RoleCode.SUPER_ADMIN),
        )
        super_admin_role = uow.roles.get_by_code(RoleCode.SUPER_ADMIN)
        assert super_admin_role is not None
        super_admin_role_id = super_admin_role.id
        uow.commit()

    barrier = Barrier(2, timeout=10)

    def remove_super_admin(user_id: UUID) -> Outcome:
        barrier.wait(timeout=10)
        try:
            with make_uow(clock=clock) as uow:
                result = remove_role(
                    uow,
                    RemoveRoleCommand(user_id=user_id, role_code=RoleCode.SUPER_ADMIN),
                )
                uow.commit()
            return ("changed", user_id, str(result.changed))
        except LastSuperAdminViolationError as exc:
            return ("rejected", user_id, str(exc))

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(remove_super_admin, first.id),
            executor.submit(remove_super_admin, second.id),
        ]
        outcomes = [future.result() for future in futures]

    changed = [outcome for outcome in outcomes if outcome[0] == "changed"]
    rejected = [outcome for outcome in outcomes if outcome[0] == "rejected"]
    assert len(changed) == 1
    assert len(rejected) == 1

    with make_uow(clock=clock) as uow:
        assert uow.users.count_active_with_role(RoleCode.SUPER_ADMIN) == 1
        assert uow.users.has_role_assignment(changed[0][1], super_admin_role_id) is False
        assert uow.users.has_role_assignment(rejected[0][1], super_admin_role_id) is True
        events = [
            *uow.audit_events.list_by_resource(resource_type="User", resource_id=first.id),
            *uow.audit_events.list_by_resource(resource_type="User", resource_id=second.id),
        ]
    removed_events = [event for event in events if event.action is AuditAction.ROLE_REMOVED]
    assert len(removed_events) == 1
