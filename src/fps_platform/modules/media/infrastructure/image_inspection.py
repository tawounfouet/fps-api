from __future__ import annotations

from hashlib import sha256
from io import BytesIO

from PIL import Image, UnidentifiedImageError

from fps_platform.modules.media.application.dto import InspectionEvidence, MediaErrorCode
from fps_platform.modules.media.application.services.promotion import (
    ImageInspectionPolicy,
    MediaInspectionError,
)
from fps_platform.modules.media.domain.enums import ChecksumAlgorithm, MediaMimeType
from fps_platform.modules.media.domain.value_objects import (
    ByteSize,
    Checksum,
    MediaDimensions,
    MimeType,
)
from fps_platform.shared.domain.clock import Clock

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SIGNATURE = b"\xff\xd8\xff"
WEBP_RIFF = b"RIFF"
WEBP_FORM = b"WEBP"
ISO_BMFF_FTYP = b"ftyp"
MARKUP_PREFIXES = (b"<svg", b"<!doctype html", b"<html", b"<?xml")
MEDIA_MIME_BY_FORMAT = {
    "JPEG": MediaMimeType.JPEG,
    "PNG": MediaMimeType.PNG,
    "WEBP": MediaMimeType.WEBP,
}
FORMAT_BY_MIME = {mime: fmt for fmt, mime in MEDIA_MIME_BY_FORMAT.items()}
SUPPORTED_MIME_VALUES = frozenset(mime.value for mime in MediaMimeType)


class PillowImageInspector:
    def __init__(self, clock: Clock, *, policy: ImageInspectionPolicy | None = None) -> None:
        self._clock = clock
        self._policy = policy if policy is not None else ImageInspectionPolicy()

    def inspect(self, body: bytes, *, content_type: str | None) -> InspectionEvidence:
        if not isinstance(body, bytes) or not body:
            raise MediaInspectionError(MediaErrorCode.MEDIA_CORRUPT)
        if len(body) > self._policy.max_bytes:
            raise MediaInspectionError(MediaErrorCode.MEDIA_TOO_LARGE)
        declared = content_type.strip().lower() if isinstance(content_type, str) else None
        if declared in self._policy.blocked_client_mime_types:
            raise MediaInspectionError(MediaErrorCode.UNSUPPORTED_MEDIA_TYPE)
        detected = _detect_mime(body)
        if declared in SUPPORTED_MIME_VALUES and declared != detected.value:
            raise MediaInspectionError(MediaErrorCode.UNSUPPORTED_MEDIA_TYPE)
        expected_format = FORMAT_BY_MIME[detected]
        checksum = Checksum(ChecksumAlgorithm.SHA256, sha256(body).hexdigest())
        try:
            with Image.open(BytesIO(body)) as probe:
                if probe.format != expected_format:
                    raise MediaInspectionError(MediaErrorCode.UNSUPPORTED_MEDIA_TYPE)
                size = self._check_dimensions(probe.size)
                probe.verify()
        except MediaInspectionError:
            raise
        except Image.DecompressionBombError:
            raise MediaInspectionError(MediaErrorCode.MEDIA_TOO_LARGE) from None
        except (UnidentifiedImageError, OSError, ValueError, SyntaxError, TypeError):
            raise MediaInspectionError(MediaErrorCode.MEDIA_CORRUPT) from None
        try:
            with Image.open(BytesIO(body)) as image:
                if image.format != expected_format:
                    raise MediaInspectionError(MediaErrorCode.UNSUPPORTED_MEDIA_TYPE)
                if self._check_dimensions(image.size) != size:
                    raise MediaInspectionError(MediaErrorCode.MEDIA_CORRUPT)
                if _has_metadata(image):
                    raise MediaInspectionError(MediaErrorCode.UNSUPPORTED_MEDIA_TYPE)
                image.load()
                if image.size != size:
                    raise MediaInspectionError(MediaErrorCode.MEDIA_CORRUPT)
        except MediaInspectionError:
            raise
        except Image.DecompressionBombError:
            raise MediaInspectionError(MediaErrorCode.MEDIA_TOO_LARGE) from None
        except (UnidentifiedImageError, OSError, ValueError, SyntaxError, TypeError):
            raise MediaInspectionError(MediaErrorCode.MEDIA_CORRUPT) from None
        return InspectionEvidence(
            detected_mime=MimeType(detected),
            byte_size=ByteSize(len(body)),
            dimensions=MediaDimensions(size[0], size[1]),
            checksum=checksum,
            inspected_at=self._clock.now(),
        )

    def _check_dimensions(self, size: tuple[int, int]) -> tuple[int, int]:
        width, height = size
        if not isinstance(width, int) or not isinstance(height, int) or width < 1 or height < 1:
            raise MediaInspectionError(MediaErrorCode.MEDIA_CORRUPT)
        if (
            width > self._policy.max_dimension
            or height > self._policy.max_dimension
            or width * height > self._policy.max_pixels
        ):
            raise MediaInspectionError(MediaErrorCode.MEDIA_TOO_LARGE)
        return width, height


def _detect_mime(body: bytes) -> MediaMimeType:
    if body.startswith(JPEG_SIGNATURE):
        return MediaMimeType.JPEG
    if body.startswith(PNG_SIGNATURE):
        return MediaMimeType.PNG
    if len(body) >= 12 and body[:4] == WEBP_RIFF and body[8:12] == WEBP_FORM:
        return MediaMimeType.WEBP
    if len(body) >= 12 and body[4:8] == ISO_BMFF_FTYP:
        raise MediaInspectionError(MediaErrorCode.UNSUPPORTED_MEDIA_TYPE)
    markup = body[:512].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if any(markup.startswith(prefix) for prefix in MARKUP_PREFIXES):
        raise MediaInspectionError(MediaErrorCode.UNSUPPORTED_MEDIA_TYPE)
    raise MediaInspectionError(MediaErrorCode.UNSUPPORTED_MEDIA_TYPE)


def _has_metadata(image: Image.Image) -> bool:
    if image.info.get("exif"):
        return True
    try:
        return bool(image.getexif())
    except (OSError, ValueError, SyntaxError, TypeError):
        raise MediaInspectionError(MediaErrorCode.MEDIA_CORRUPT) from None
