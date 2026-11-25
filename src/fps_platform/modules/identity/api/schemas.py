from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from fps_platform.modules.identity.domain.value_objects import (
    PermissionCode,
    RoleCode,
    UserStatus,
)

REASON_PATTERN = r"^[a-zA-Z0-9_]+$"


class MeResponse(BaseModel):
    id: UUID
    email: str
    display_name: str
    status: UserStatus
    roles: list[RoleCode]
    permissions: list[PermissionCode]


class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str
    status: UserStatus
    roles: list[RoleCode]
    version: int
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None
    suspended_at: datetime | None = None
    disabled_at: datetime | None = None


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    limit: int
    offset: int


class RoleResponse(BaseModel):
    id: UUID
    code: RoleCode
    name: str
    description: str


class RoleListResponse(BaseModel):
    items: list[RoleResponse]


class AssignRoleRequest(BaseModel):
    role_code: RoleCode
    expected_version: int | None = Field(default=None, ge=1)


class StatusChangeRequest(BaseModel):
    reason_code: str = Field(min_length=1, max_length=64, pattern=REASON_PATTERN)
    expected_version: int | None = Field(default=None, ge=1)


class CommandResultResponse(BaseModel):
    user_id: UUID
    changed: bool
    version: int
