from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from json import dumps
from re import Pattern, compile

from fps_platform.modules.contact.domain.enums import ContactLocale, ContactSubject

EMAIL_PATTERN: Pattern[str] = compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")
IDEMPOTENCY_PATTERN: Pattern[str] = compile(r"^[A-Za-z0-9_-]{16,128}$")
REASON_PATTERN: Pattern[str] = compile(r"^[A-Za-z0-9_]{1,64}$")
PHONE_PATTERN: Pattern[str] = compile(r"^[+0-9 ()-]{3,32}$")
FORBIDDEN_CHARACTERS = frozenset("\r\n\t\x00")

type ContactFingerprintValue = str | int | bool | None


def normalize_text(value: str, field_name: str, *, minimum: int, maximum: int) -> str:
    normalized = value.strip()
    if len(normalized) < minimum or len(normalized) > maximum:
        raise ValueError(f"{field_name} length is invalid")
    if any(character in normalized for character in FORBIDDEN_CHARACTERS):
        raise ValueError(f"{field_name} contains forbidden characters")
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        raise ValueError(f"{field_name} contains control characters")
    return normalized


@dataclass(frozen=True, slots=True)
class PersonName:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "value", normalize_text(self.value, "name", minimum=1, maximum=128)
        )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ContactEmailAddress:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip().lower()
        if len(value) > 254 or not EMAIL_PATTERN.fullmatch(value):
            raise ValueError("email address is invalid")
        object.__setattr__(self, "value", value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ContactMessage:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            normalize_text(self.value, "message", minimum=1, maximum=4000),
        )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ContactOptionalText:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "value", normalize_text(self.value, "field", minimum=1, maximum=128)
        )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class PhoneNumber:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip()
        if len(value) > 32 or not PHONE_PATTERN.fullmatch(value):
            raise ValueError("phone number is invalid")
        object.__setattr__(self, "value", value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ContactIdempotencyKey:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip()
        if not IDEMPOTENCY_PATTERN.fullmatch(value):
            raise ValueError("idempotency key is invalid")
        object.__setattr__(self, "value", value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ContactCloseReason:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip().lower()
        if not REASON_PATTERN.fullmatch(value):
            raise ValueError("close reason is invalid")
        object.__setattr__(self, "value", value)

    def __str__(self) -> str:
        return self.value


def normalize_failure_code(value: str) -> str:
    normalized = "".join(character if character.isalnum() else "_" for character in value.strip())
    normalized = normalized.strip("_").upper()
    if not normalized:
        return "PROVIDER_ERROR"
    return normalized[:64]


def normalize_provider_reference(value: str) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > 128:
        raise ValueError("provider reference is invalid")
    if any(
        not character.isascii() or not (character.isalnum() or character in "-_.")
        for character in normalized
    ):
        raise ValueError("provider reference contains unsafe characters")
    return normalized


def contact_fingerprint(payload: Mapping[str, ContactFingerprintValue]) -> str:
    canonical = dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def normalize_subject(value: str | ContactSubject) -> ContactSubject:
    if isinstance(value, ContactSubject):
        return value
    return ContactSubject(value.strip())


def normalize_locale(value: str | ContactLocale) -> ContactLocale:
    if isinstance(value, ContactLocale):
        return value
    return ContactLocale(value.strip().lower())
