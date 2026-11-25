from __future__ import annotations

from collections.abc import Iterable

from fps_platform.modules.identity.domain.value_objects import PermissionCode, RoleCode

ROLE_PERMISSIONS: dict[RoleCode, frozenset[PermissionCode]] = {
    RoleCode.SUPER_ADMIN: frozenset(PermissionCode),
    RoleCode.CONTENT_ADMIN: frozenset(
        {
            PermissionCode.CREATE_CONTENT,
            PermissionCode.EDIT_CONTENT,
            PermissionCode.PUBLISH_CONTENT,
            PermissionCode.ARCHIVE_CONTENT,
            PermissionCode.RESTORE_CONTENT,
            PermissionCode.VIEW_DRAFTS,
            PermissionCode.VIEW_MEDIA,
            PermissionCode.MANAGE_MEDIA,
            PermissionCode.DELETE_MEDIA,
            PermissionCode.MANAGE_SEO,
        }
    ),
    RoleCode.EDITOR: frozenset(
        {
            PermissionCode.CREATE_CONTENT,
            PermissionCode.EDIT_CONTENT,
            PermissionCode.VIEW_DRAFTS,
            PermissionCode.VIEW_MEDIA,
        }
    ),
    RoleCode.VIEWER: frozenset(
        {
            PermissionCode.VIEW_DRAFTS,
            PermissionCode.VIEW_MEDIA,
        }
    ),
}


def permissions_for(role_codes: Iterable[RoleCode]) -> frozenset[PermissionCode]:
    resolved: set[PermissionCode] = set()
    for role_code in role_codes:
        resolved.update(ROLE_PERMISSIONS.get(role_code, frozenset()))
    return frozenset(resolved)
