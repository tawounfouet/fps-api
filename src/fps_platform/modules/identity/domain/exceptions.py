from __future__ import annotations

from uuid import UUID

from fps_platform.modules.identity.domain.value_objects import RoleCode


class IdentityError(Exception):
    pass


class UserNotFoundError(IdentityError):
    def __init__(self, user_id: UUID) -> None:
        super().__init__(f"user {user_id} was not found")
        self.user_id = user_id


class RoleNotFoundError(IdentityError):
    def __init__(self, role_id: UUID | None = None, role_code: RoleCode | None = None) -> None:
        super().__init__("role was not found")
        self.role_id = role_id
        self.role_code = role_code


class DuplicateExternalIdentityError(IdentityError):
    pass


class InvalidUserTransitionError(IdentityError):
    pass


class LastSuperAdminViolationError(IdentityError):
    pass


class SuperAdminExistsError(IdentityError):
    pass


class AuthenticationError(IdentityError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class AuthorizationError(IdentityError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class TokenValidationError(Exception):
    pass


class ActorNotFoundError(IdentityError):
    pass
