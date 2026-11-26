from __future__ import annotations

from enum import StrEnum


class MediaStorageMode(StrEnum):
    FAKE = "fake"
    S3 = "s3"


class MediaStatus(StrEnum):
    UPLOADING = "UPLOADING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class MediaMimeType(StrEnum):
    JPEG = "image/jpeg"
    PNG = "image/png"
    WEBP = "image/webp"


class MediaCoverageStatus(StrEnum):
    PARTIAL = "PARTIAL"
    FULL = "FULL"


class ChecksumAlgorithm(StrEnum):
    SHA256 = "sha256"


class MediaLocale(StrEnum):
    FR = "fr"
    EN = "en"
