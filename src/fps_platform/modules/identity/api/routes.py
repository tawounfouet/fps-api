from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from fps_platform.api.schemas import ErrorResponse
from fps_platform.modules.identity.api.schemas import (
    AssignRoleRequest,
    CommandResultResponse,
    MeResponse,
    RoleListResponse,
    RoleResponse,
    StatusChangeRequest,
    UserListResponse,
    UserResponse,
)
from fps_platform.modules.identity.application import handlers, queries
from fps_platform.modules.identity.application.commands import (
    ActivateUserCommand,
    AssignRoleCommand,
    DisableUserCommand,
    RemoveRoleCommand,
    SuspendUserCommand,
)
from fps_platform.modules.identity.application.ports import IdentityUnitOfWork
from fps_platform.modules.identity.domain.entities import Role, User
from fps_platform.modules.identity.domain.value_objects import (
    PermissionCode,
    ReasonCode,
    UserStatus,
)
from fps_platform.shared.auth.dependencies import (
    get_current_principal,
    get_uow_for_principal,
    require_permission,
)
from fps_platform.shared.auth.principal import CurrentPrincipal

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

AUTH_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Authentication is required"},
    403: {"model": ErrorResponse, "description": "Permission is denied"},
}
IAM_RESPONSES: dict[int | str, dict[str, object]] = {
    **AUTH_RESPONSES,
    404: {"model": ErrorResponse, "description": "Resource not found"},
    409: {"model": ErrorResponse, "description": "Command conflicts with current state"},
    422: {"model": ErrorResponse, "description": "Validation error"},
}


def user_response(uow: IdentityUnitOfWork, user: User) -> UserResponse:
    if user.created_at is None or user.updated_at is None:
        raise RuntimeError("persisted user must have timestamps")
    roles: Sequence[Role] = uow.roles.list_by_ids(list(user.role_ids))
    return UserResponse(
        id=user.id,
        email=str(user.email),
        display_name=user.display_name,
        status=user.status,
        roles=[role.code for role in sorted(roles, key=lambda role: role.code.value)],
        version=user.version,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        suspended_at=user.suspended_at,
        disabled_at=user.disabled_at,
    )


@router.get(
    "/me",
    operation_id="adminGetMe",
    response_model=MeResponse,
    responses=AUTH_RESPONSES,
)
def get_me(principal: CurrentPrincipal = Depends(get_current_principal)) -> MeResponse:
    return MeResponse(
        id=principal.user_id,
        email=str(principal.email),
        display_name=principal.display_name,
        status=principal.status,
        roles=list(principal.roles),
        permissions=sorted(principal.permissions, key=lambda permission: permission.value),
    )


@router.get(
    "/users",
    operation_id="adminListUsers",
    response_model=UserListResponse,
    responses=IAM_RESPONSES,
)
def list_users(
    response: Response,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_status: UserStatus | None = Query(default=None, alias="status"),
    _: CurrentPrincipal = Depends(require_permission(PermissionCode.VIEW_USERS)),
    uow: IdentityUnitOfWork = Depends(get_uow_for_principal),
) -> UserListResponse:
    users = queries.list_users(uow, limit=limit, offset=offset, status=user_status)
    response.headers["Cache-Control"] = "no-store"
    return UserListResponse(
        items=[user_response(uow, user) for user in users],
        total=queries.count_users(uow, status=user_status),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/users/{user_id}",
    operation_id="adminGetUser",
    response_model=UserResponse,
    responses=IAM_RESPONSES,
)
def get_user(
    user_id: UUID,
    _: CurrentPrincipal = Depends(require_permission(PermissionCode.VIEW_USERS)),
    uow: IdentityUnitOfWork = Depends(get_uow_for_principal),
) -> UserResponse:
    return user_response(uow, queries.get_user(uow, user_id))


@router.post(
    "/users/{user_id}/roles",
    operation_id="adminAssignRole",
    response_model=CommandResultResponse,
    responses=IAM_RESPONSES,
)
def assign_role(
    user_id: UUID,
    payload: AssignRoleRequest,
    _: CurrentPrincipal = Depends(require_permission(PermissionCode.MANAGE_ROLES)),
    uow: IdentityUnitOfWork = Depends(get_uow_for_principal),
) -> CommandResultResponse:
    result = handlers.assign_role(
        uow,
        AssignRoleCommand(
            user_id=user_id,
            role_code=payload.role_code,
            expected_version=payload.expected_version,
        ),
    )
    uow.commit()
    return CommandResultResponse(
        user_id=result.user_id,
        changed=result.changed,
        version=result.version,
    )


@router.delete(
    "/users/{user_id}/roles/{role_id}",
    operation_id="adminRemoveRole",
    response_model=CommandResultResponse,
    responses=IAM_RESPONSES,
)
def remove_role(
    user_id: UUID,
    role_id: UUID,
    _: CurrentPrincipal = Depends(require_permission(PermissionCode.MANAGE_ROLES)),
    uow: IdentityUnitOfWork = Depends(get_uow_for_principal),
) -> CommandResultResponse:
    role = queries.get_role(uow, role_id)
    result = handlers.remove_role(uow, RemoveRoleCommand(user_id=user_id, role_code=role.code))
    uow.commit()
    return CommandResultResponse(
        user_id=result.user_id,
        changed=result.changed,
        version=result.version,
    )


@router.post(
    "/users/{user_id}/suspend",
    operation_id="adminSuspendUser",
    response_model=CommandResultResponse,
    responses=IAM_RESPONSES,
)
def suspend_user(
    user_id: UUID,
    payload: StatusChangeRequest,
    _: CurrentPrincipal = Depends(require_permission(PermissionCode.MANAGE_USERS)),
    uow: IdentityUnitOfWork = Depends(get_uow_for_principal),
) -> CommandResultResponse:
    result = handlers.suspend_user(
        uow,
        SuspendUserCommand(
            user_id=user_id,
            reason_code=ReasonCode(payload.reason_code),
            expected_version=payload.expected_version,
        ),
    )
    uow.commit()
    return CommandResultResponse(
        user_id=result.user_id,
        changed=result.changed,
        version=result.version,
    )


@router.post(
    "/users/{user_id}/activate",
    operation_id="adminActivateUser",
    response_model=CommandResultResponse,
    responses=IAM_RESPONSES,
)
def activate_user(
    user_id: UUID,
    payload: StatusChangeRequest,
    _: CurrentPrincipal = Depends(require_permission(PermissionCode.MANAGE_USERS)),
    uow: IdentityUnitOfWork = Depends(get_uow_for_principal),
) -> CommandResultResponse:
    result = handlers.activate_user(
        uow,
        ActivateUserCommand(
            user_id=user_id,
            reason_code=ReasonCode(payload.reason_code),
            expected_version=payload.expected_version,
        ),
    )
    uow.commit()
    return CommandResultResponse(
        user_id=result.user_id,
        changed=result.changed,
        version=result.version,
    )


@router.post(
    "/users/{user_id}/disable",
    operation_id="adminDisableUser",
    response_model=CommandResultResponse,
    responses=IAM_RESPONSES,
)
def disable_user(
    user_id: UUID,
    payload: StatusChangeRequest,
    _: CurrentPrincipal = Depends(require_permission(PermissionCode.MANAGE_USERS)),
    uow: IdentityUnitOfWork = Depends(get_uow_for_principal),
) -> CommandResultResponse:
    result = handlers.disable_user(
        uow,
        DisableUserCommand(
            user_id=user_id,
            reason_code=ReasonCode(payload.reason_code),
            expected_version=payload.expected_version,
        ),
    )
    uow.commit()
    return CommandResultResponse(
        user_id=result.user_id,
        changed=result.changed,
        version=result.version,
    )


@router.get(
    "/roles",
    operation_id="adminListRoles",
    response_model=RoleListResponse,
    responses=IAM_RESPONSES,
)
def list_roles(
    _: CurrentPrincipal = Depends(require_permission(PermissionCode.VIEW_USERS)),
    uow: IdentityUnitOfWork = Depends(get_uow_for_principal),
) -> RoleListResponse:
    roles = queries.list_roles(uow)
    return RoleListResponse(
        items=[
            RoleResponse(
                id=role.id,
                code=role.code,
                name=role.name,
                description=role.description,
            )
            for role in roles
        ]
    )
