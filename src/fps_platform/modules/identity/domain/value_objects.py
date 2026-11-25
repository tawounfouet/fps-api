from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from re import Pattern, compile
from urllib.parse import urlparse

EMAIL_PATTERN: Pattern[str] = compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
SUBJECT_FORBIDDEN_CHARACTERS = frozenset("\r\n\t\x00")


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DISABLED = "DISABLED"


class RoleCode(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    CONTENT_ADMIN = "CONTENT_ADMIN"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"


class PermissionCode(StrEnum):
    CREATE_CONTENT = "CREATE_CONTENT"
    EDIT_CONTENT = "EDIT_CONTENT"
    PUBLISH_CONTENT = "PUBLISH_CONTENT"
    ARCHIVE_CONTENT = "ARCHIVE_CONTENT"
    RESTORE_CONTENT = "RESTORE_CONTENT"
    VIEW_DRAFTS = "VIEW_DRAFTS"
    VIEW_MEDIA = "VIEW_MEDIA"
    MANAGE_MEDIA = "MANAGE_MEDIA"
    DELETE_MEDIA = "DELETE_MEDIA"
    VIEW_CONTACTS = "VIEW_CONTACTS"
    MANAGE_CONTACTS = "MANAGE_CONTACTS"
    EXPORT_CONTACTS = "EXPORT_CONTACTS"
    DELETE_CONTACTS = "DELETE_CONTACTS"
    VIEW_USERS = "VIEW_USERS"
    MANAGE_USERS = "MANAGE_USERS"
    MANAGE_ROLES = "MANAGE_ROLES"
    VIEW_SETTINGS = "VIEW_SETTINGS"
    MANAGE_SETTINGS = "MANAGE_SETTINGS"
    VIEW_AUDIT = "VIEW_AUDIT"
    MANAGE_SEO = "MANAGE_SEO"


@dataclass(frozen=True, slots=True)
class EmailAddress:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip().lower()
        if len(value) > 254 or not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("email address is invalid")
        object.__setattr__(self, "value", value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ExternalIdentity:
    issuer: str
    subject: str

    def __post_init__(self) -> None:
        issuer = self.issuer.strip()
        subject = self.subject.strip()
        if not issuer or len(issuer) > 512:
            raise ValueError("issuer is invalid")
        parsed = urlparse(issuer)
        if parsed.scheme not in {"http", "https"} or parsed.netloc == "":
            raise ValueError("issuer must be an absolute http or https URL")
        if not subject or len(subject) > 256:
            raise ValueError("subject is invalid")
        if any(character in subject for character in SUBJECT_FORBIDDEN_CHARACTERS):
            raise ValueError("subject contains forbidden characters")
        object.__setattr__(self, "issuer", issuer)
        object.__setattr__(self, "subject", subject)

    def key(self) -> tuple[str, str]:
        return self.issuer, self.subject


@dataclass(frozen=True, slots=True)
class ReasonCode:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip().lower()
        if not value or len(value) > 64 or not value.replace("_", "").isalnum():
            raise ValueError("reason code is invalid")
        object.__setattr__(self, "value", value)

    def __str__(self) -> str:
        return self.value
