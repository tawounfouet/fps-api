from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from re import Pattern, compile
from unicodedata import normalize as normalize_unicode
from uuid import UUID

from fps_platform.modules.media.domain.enums import ChecksumAlgorithm, MediaMimeType

STORAGE_KEY_PATTERN: Pattern[str] = compile(r"^[A-Za-z0-9][A-Za-z0-9/._-]{0,511}$")
HASH_PATTERN: Pattern[str] = compile(r"^[0-9a-f]{64}$")
FORBIDDEN_CHARACTERS = frozenset("\r\n\t\x00")
SUPPORTED_LOCALES = frozenset({"fr", "en"})
MAX_TEXT_LENGTH = 512
MAX_ATTRIBUTION_LENGTH = 256
MAX_STORAGE_KEY_LENGTH = 512
MAX_FILENAME_LENGTH = 255
MAX_DIMENSION = 100_000
MAX_BYTE_SIZE = (1 << 63) - 1
MAX_UPLOAD_ATTEMPTS = 3


def normalize_media_text(value: str, field_name: str, *, maximum: int) -> str:
    normalized = normalize_unicode("NFC", value).strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{field_name} length is invalid")
    if any(character in normalized for character in FORBIDDEN_CHARACTERS):
        raise ValueError(f"{field_name} contains forbidden characters")
    if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
        raise ValueError(f"{field_name} contains control characters")
    return normalized


@dataclass(frozen=True, slots=True)
class StorageKey:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip()
        if not value or len(value) > MAX_STORAGE_KEY_LENGTH:
            raise ValueError("storage key length is invalid")
        if any(character.isspace() for character in value):
            raise ValueError("storage key contains whitespace")
        if value.startswith("/") or value.endswith("/") or "//" in value or ".." in value:
            raise ValueError("storage key contains an unsafe path fragment")
        if not STORAGE_KEY_PATTERN.fullmatch(value):
            raise ValueError("storage key contains unsupported characters")
        object.__setattr__(self, "value", value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class OriginalFileName:
    value: str

    def __post_init__(self) -> None:
        value = normalize_unicode("NFC", self.value.strip())
        if not value or len(value) > MAX_FILENAME_LENGTH:
            raise ValueError("original filename length is invalid")
        if "/" in value or "\\" in value or ".." in value:
            raise ValueError("original filename contains a path fragment")
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError("original filename contains control characters")
        object.__setattr__(self, "value", value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class MimeType:
    value: MediaMimeType | str

    def __post_init__(self) -> None:
        if isinstance(self.value, MediaMimeType):
            return
        try:
            normalized = MediaMimeType(str(self.value).strip().lower())
        except ValueError as exc:
            raise ValueError("MIME type is not allowed") from exc
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class ByteSize:
    value: int

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not isinstance(self.value, int):
            raise ValueError("byte size must be an integer")
        if self.value < 0 or self.value > MAX_BYTE_SIZE:
            raise ValueError("byte size is out of range")


@dataclass(frozen=True, slots=True)
class MediaDimensions:
    width: int
    height: int

    def __post_init__(self) -> None:
        if (
            isinstance(self.width, bool)
            or isinstance(self.height, bool)
            or not isinstance(self.width, int)
            or not isinstance(self.height, int)
        ):
            raise ValueError("dimensions must be integers")
        if not 0 < self.width <= MAX_DIMENSION or not 0 < self.height <= MAX_DIMENSION:
            raise ValueError("dimensions are out of range")


@dataclass(frozen=True, slots=True)
class Checksum:
    algorithm: ChecksumAlgorithm
    digest: str

    def __post_init__(self) -> None:
        try:
            algorithm = ChecksumAlgorithm(str(self.algorithm).strip().lower())
        except ValueError as exc:
            raise ValueError("checksum algorithm is not supported") from exc
        object.__setattr__(self, "algorithm", algorithm)
        digest = self.digest.strip()
        if not HASH_PATTERN.fullmatch(digest):
            raise ValueError("checksum digest must be a lowercase SHA-256 hex string")
        object.__setattr__(self, "digest", digest)


@dataclass(frozen=True, slots=True)
class MediaText:
    value: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "value",
            normalize_media_text(self.value, "media text", maximum=MAX_TEXT_LENGTH),
        )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class LocalizedTextMap:
    fr: MediaText | None = None
    en: MediaText | None = None

    def __post_init__(self) -> None:
        for locale, value in (("fr", self.fr), ("en", self.en)):
            if value is not None and not isinstance(value, MediaText):
                raise ValueError(f"{locale} text must be a MediaText")

    def as_mapping(self) -> dict[str, str]:
        values: dict[str, str] = {}
        if self.fr is not None:
            values["fr"] = str(self.fr)
        if self.en is not None:
            values["en"] = str(self.en)
        return values


@dataclass(frozen=True, slots=True)
class MediaAttribution:
    source: MediaText | None = None
    license: MediaText | None = None

    def __post_init__(self) -> None:
        if self.source is not None and len(str(self.source)) > MAX_ATTRIBUTION_LENGTH:
            raise ValueError("attribution source is too long")
        if self.license is not None and len(str(self.license)) > MAX_ATTRIBUTION_LENGTH:
            raise ValueError("attribution license is too long")

    def as_mapping(self) -> dict[str, str]:
        values: dict[str, str] = {}
        if self.source is not None:
            values["source"] = str(self.source)
        if self.license is not None:
            values["license"] = str(self.license)
        return values


@dataclass(frozen=True, slots=True)
class MediaMetadata:
    title: MediaText | None = None
    alt_texts: LocalizedTextMap = field(default_factory=LocalizedTextMap)
    captions: LocalizedTextMap = field(default_factory=LocalizedTextMap)
    attribution: MediaAttribution | None = None

    def as_mapping(self) -> dict[str, object]:
        return {
            "title": str(self.title) if self.title is not None else None,
            "alt_texts": self.alt_texts.as_mapping(),
            "captions": self.captions.as_mapping(),
            "attribution": self.attribution.as_mapping() if self.attribution is not None else None,
        }


def to_localized_text_map(value: Mapping[str, str] | LocalizedTextMap) -> LocalizedTextMap:
    if isinstance(value, LocalizedTextMap):
        return value
    unsupported = set(value) - SUPPORTED_LOCALES
    if unsupported:
        raise ValueError("localized text contains an unsupported locale")
    return LocalizedTextMap(
        fr=MediaText(value["fr"]) if "fr" in value else None,
        en=MediaText(value["en"]) if "en" in value else None,
    )


@dataclass(frozen=True, slots=True)
class PromotionEvidence:
    proof_id: UUID
    storage_key: StorageKey
    detected_mime: MimeType
    byte_size: ByteSize
    dimensions: MediaDimensions
    checksum: Checksum
    verified_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.proof_id, UUID):
            raise ValueError("promotion proof id must be a UUID")
        if not isinstance(self.storage_key, StorageKey):
            raise ValueError("promotion evidence requires a StorageKey")
        if not isinstance(self.detected_mime, MimeType):
            raise ValueError("promotion evidence requires a detected MimeType")
        if not isinstance(self.byte_size, ByteSize):
            raise ValueError("promotion evidence requires a measured ByteSize")
        if not isinstance(self.dimensions, MediaDimensions):
            raise ValueError("promotion evidence requires MediaDimensions")
        if not isinstance(self.checksum, Checksum):
            raise ValueError("promotion evidence requires a Checksum")
        if self.verified_at.tzinfo is None or self.verified_at.utcoffset() != timedelta(0):
            raise ValueError("verified_at must be aware UTC")
        object.__setattr__(self, "verified_at", self.verified_at.astimezone(UTC))
