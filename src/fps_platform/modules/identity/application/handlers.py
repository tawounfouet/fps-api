from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fps_platform.modules.audit.domain.enums import AuditAction, AuditSource
from fps_platform.modules.identity.application.commands import (
    ActivateUserCommand,
    AssignRoleCommand,
    BootstrapSuperAdminCommand,
    DisableUserCommand,
    IdentityCommandResult,
    RemoveRoleCommand,
    SeedRolesCommand,
    SuspendUserCommand,
)
from fps_platform.modules.identity.application.ports import IdentityUnitOfWork
from fps_platform.modules.identity.domain.entities import Role, User
from fps_platform.modules.identity.domain.exceptions import (
    InvalidUserTransitionError,
    LastSuperAdminViolationError,
    RoleNotFoundError,
    SuperAdminExistsError,
    UserNotFoundError,
)
from fps_platform.modules.identity.domain.value_objects import (
    EmailAddress,
    ExternalIdentity,
    RoleCode,
    UserStatus,
)
from fps_platform.shared.domain.errors import ConcurrentModificationError

ROLE_NAMES: dict[RoleCode, str] = {
    RoleCode.SUPER_ADMIN: "Super Administrator",
    RoleCode.CONTENT_ADMIN: "Content Administrator",
    RoleCode.EDITOR: "Editor",
    RoleCode.VIEWER: "Viewer",
}

ROLE_DESCRIPTIONS: dict[RoleCode, str] = {
    RoleCode.SUPER_ADMIN: "Full administrative governance",
    RoleCode.CONTENT_ADMIN: "Content, publishing and media administration",
    RoleCode.EDITOR: "Draft content creation and editing",
    RoleCode.VIEWER: "Read-only views explicitly authorized",
}


def _require_version(user: User, expected_version: int | None) -> None:
    if expected_version is not None and user.version != expected_version:
        raise ConcurrentModificationError("user version changed")


def _get_user(uow: IdentityUnitOfWork, user_id: UUID) -> User:
    user = uow.users.get(user_id)
    if user is None:
        raise UserNotFoundError(user_id)
    return user


def _get_role(uow: IdentityUnitOfWork, code: RoleCode) -> Role:
    role = uow.roles.get_by_code(code)
    if role is None:
        raise RoleNotFoundError(role_code=code)
    return role


def _assert_not_last_super_admin(uow: IdentityUnitOfWork, user: User) -> None:
    super_admin_role = _get_role(uow, RoleCode.SUPER_ADMIN)
    if user.status is not UserStatus.ACTIVE:
        return
    if not uow.users.has_role_assignment(user.id, super_admin_role.id):
        return
    if uow.users.count_active_with_role(RoleCode.SUPER_ADMIN) <= 1:
        raise LastSuperAdminViolationError("the last active SUPER_ADMIN cannot be removed")


def seed_roles(uow: IdentityUnitOfWork, command: SeedRolesCommand) -> int:
    now: datetime = uow.clock.now()
    inserted = 0
    for code in RoleCode:
        if uow.roles.get_by_code(code) is not None:
            continue
        uow.roles.add(
            Role(
                id=uow.id_generator.new_id(),
                code=code,
                name=ROLE_NAMES[code],
                description=ROLE_DESCRIPTIONS[code],
                created_at=now,
                updated_at=now,
            )
        )
        inserted += 1
    return inserted


def bootstrap_super_admin(
    uow: IdentityUnitOfWork,
    command: BootstrapSuperAdminCommand,
    *,
    source: AuditSource = AuditSource.SYSTEM,
) -> IdentityCommandResult:
    now: datetime = uow.clock.now()
    identity = ExternalIdentity(command.issuer, command.subject)
    with uow.super_admin_guard.lock():
        super_admin_role = _get_role(uow, RoleCode.SUPER_ADMIN)
        existing = uow.users.get_by_external_identity(identity)
        if (
            existing is not None
            and existing.status is UserStatus.ACTIVE
            and uow.users.has_role_assignment(existing.id, super_admin_role.id)
        ):
            return IdentityCommandResult(
                user_id=existing.id,
                changed=False,
                version=existing.version,
            )
        if uow.users.count_active_with_role(RoleCode.SUPER_ADMIN) > 0:
            raise SuperAdminExistsError("an active SUPER_ADMIN already exists")

        created = existing is None
        if existing is None:
            user = User(
                id=uow.id_generator.new_id(),
                external_identity=identity,
                email=EmailAddress(command.email),
                display_name=command.display_name,
                status=UserStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
            uow.users.add(user)
        else:
            user = existing
            original_version = user.version
            user.replace_email(EmailAddress(command.email), now)
            if user.status is UserStatus.SUSPENDED:
                user.activate(now)
                uow.audit_recorder.record(
                    action=AuditAction.USER_ACTIVATED,
                    resource_type="User",
                    resource_id=user.id,
                    metadata={"reason_code": "bootstrap_recovery"},
                    source=source,
                )
            if user.status is UserStatus.DISABLED:
                raise InvalidUserTransitionError("disabled users cannot be bootstrapped")
            uow.users.save(user, expected_version=original_version)

        assigned = user.assign_role(super_admin_role.id, now)
        if assigned:
            uow.users.add_role_assignment(user.id, super_admin_role.id)
            uow.users.save(user, expected_version=1 if created else user.version - 1)
            uow.audit_recorder.record(
                action=AuditAction.ROLE_ASSIGNED,
                resource_type="User",
                resource_id=user.id,
                metadata={
                    "role_code": RoleCode.SUPER_ADMIN.value,
                    "assigned_by": "bootstrap_cli",
                },
                source=source,
            )
        if created:
            uow.audit_recorder.record(
                action=AuditAction.USER_CREATED,
                resource_type="User",
                resource_id=user.id,
                metadata={"created_by": "bootstrap_cli"},
                source=source,
            )
        return IdentityCommandResult(
            user_id=user.id,
            changed=True,
            version=user.version,
            created=created,
        )


def assign_role(
    uow: IdentityUnitOfWork,
    command: AssignRoleCommand,
    *,
    source: AuditSource = AuditSource.APPLICATION,
) -> IdentityCommandResult:
    now: datetime = uow.clock.now()
    with uow.super_admin_guard.lock():
        user = _get_user(uow, command.user_id)
        _require_version(user, command.expected_version)
        role = _get_role(uow, command.role_code)
        if uow.users.has_role_assignment(user.id, role.id):
            return IdentityCommandResult(user_id=user.id, changed=False, version=user.version)
        original_version = user.version
        user.assign_role(role.id, now)
        uow.users.add_role_assignment(user.id, role.id)
        uow.users.save(user, expected_version=original_version)
        uow.audit_recorder.record(
            action=AuditAction.ROLE_ASSIGNED,
            resource_type="User",
            resource_id=user.id,
            metadata={"role_code": role.code.value},
            source=source,
        )
        return IdentityCommandResult(user_id=user.id, changed=True, version=user.version)


def remove_role(
    uow: IdentityUnitOfWork,
    command: RemoveRoleCommand,
    *,
    source: AuditSource = AuditSource.APPLICATION,
) -> IdentityCommandResult:
    now: datetime = uow.clock.now()
    with uow.super_admin_guard.lock():
        user = _get_user(uow, command.user_id)
        _require_version(user, command.expected_version)
        role = _get_role(uow, command.role_code)
        if not uow.users.has_role_assignment(user.id, role.id):
            return IdentityCommandResult(user_id=user.id, changed=False, version=user.version)
        if command.role_code is RoleCode.SUPER_ADMIN:
            _assert_not_last_super_admin(uow, user)
        original_version = user.version
        user.remove_role(role.id, now)
        uow.users.remove_role_assignment(user.id, role.id)
        uow.users.save(user, expected_version=original_version)
        uow.audit_recorder.record(
            action=AuditAction.ROLE_REMOVED,
            resource_type="User",
            resource_id=user.id,
            metadata={"role_code": role.code.value},
            source=source,
        )
        return IdentityCommandResult(user_id=user.id, changed=True, version=user.version)


def suspend_user(
    uow: IdentityUnitOfWork,
    command: SuspendUserCommand,
    *,
    source: AuditSource = AuditSource.APPLICATION,
) -> IdentityCommandResult:
    now: datetime = uow.clock.now()
    with uow.super_admin_guard.lock():
        user = _get_user(uow, command.user_id)
        _require_version(user, command.expected_version)
        if user.status is UserStatus.ACTIVE:
            _assert_not_last_super_admin(uow, user)
        original_version = user.version
        user.suspend(now)
        uow.users.save(user, expected_version=original_version)
        uow.audit_recorder.record(
            action=AuditAction.USER_SUSPENDED,
            resource_type="User",
            resource_id=user.id,
            metadata={"reason_code": str(command.reason_code)},
            source=source,
        )
        return IdentityCommandResult(user_id=user.id, changed=True, version=user.version)


def activate_user(
    uow: IdentityUnitOfWork,
    command: ActivateUserCommand,
    *,
    source: AuditSource = AuditSource.APPLICATION,
) -> IdentityCommandResult:
    now: datetime = uow.clock.now()
    with uow.super_admin_guard.lock():
        user = _get_user(uow, command.user_id)
        _require_version(user, command.expected_version)
        original_version = user.version
        user.activate(now)
        uow.users.save(user, expected_version=original_version)
        uow.audit_recorder.record(
            action=AuditAction.USER_ACTIVATED,
            resource_type="User",
            resource_id=user.id,
            metadata={"reason_code": str(command.reason_code)},
            source=source,
        )
        return IdentityCommandResult(user_id=user.id, changed=True, version=user.version)


def disable_user(
    uow: IdentityUnitOfWork,
    command: DisableUserCommand,
    *,
    source: AuditSource = AuditSource.APPLICATION,
) -> IdentityCommandResult:
    now: datetime = uow.clock.now()
    with uow.super_admin_guard.lock():
        user = _get_user(uow, command.user_id)
        _require_version(user, command.expected_version)
        if user.status is UserStatus.ACTIVE:
            _assert_not_last_super_admin(uow, user)
        original_version = user.version
        user.disable(now)
        uow.users.save(user, expected_version=original_version)
        uow.audit_recorder.record(
            action=AuditAction.USER_DISABLED,
            resource_type="User",
            resource_id=user.id,
            metadata={"reason_code": str(command.reason_code)},
            source=source,
        )
        return IdentityCommandResult(user_id=user.id, changed=True, version=user.version)
