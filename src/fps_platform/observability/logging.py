from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from re import Match, Pattern, compile
from typing import Any

from fps_platform.config import Settings

logger = logging.getLogger("fps_platform.request")
SAFE_FIELDS = (
    "request_id",
    "correlation_id",
    "method",
    "route",
    "status_code",
    "duration_ms",
    "environment",
    "release_sha",
)
REDACTED = "[REDACTED]"
SIGNED_MARKERS: tuple[str, ...] = (
    "x-amz-signature",
    "signature=",
    "se=",
    "sp=",
    "sig=",
)
SIGNED_URL_PATTERN: Pattern[str] = compile(r"(?i)\b(?:https?|s3)://[^\s\"'<>]+")
SIGNED_PARAM_PATTERN: Pattern[str] = compile(
    r"(?i)(?:[?&]|\b)(?:X-Amz-Signature|signature|sig|se|sp)=[^\s&\"']*"
)
BARE_SIGNATURE_PATTERN: Pattern[str] = compile(r"(?i)\bX-Amz-Signature\b")
MAX_REDACTED_LENGTH = 512


def redact_sensitive_text(value: object, *, limit: int = MAX_REDACTED_LENGTH) -> str:
    text = str(value)

    def replace_url(match: Match[str]) -> str:
        candidate = str(match.group(0)).lower()
        if any(marker in candidate for marker in SIGNED_MARKERS):
            return REDACTED
        return str(match.group(0))

    text = SIGNED_URL_PATTERN.sub(replace_url, text)
    text = SIGNED_PARAM_PATTERN.sub(REDACTED, text)
    text = BARE_SIGNATURE_PATTERN.sub(REDACTED, text)
    if len(text) > limit:
        return text[:limit] + "...[TRUNCATED]"
    return text


def safe_exception_message(exc: BaseException) -> str:
    return redact_sensitive_text(str(exc))


class RedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_sensitive_text(record.getMessage())
        record.args = ()
        for field in SAFE_FIELDS:
            if hasattr(record, field) and isinstance(getattr(record, field), str):
                setattr(record, field, redact_sensitive_text(getattr(record, field)))
        return True


class JsonFormatter(logging.Formatter):
    def __init__(self, *, service: str, environment: str) -> None:
        super().__init__()
        self.service = service
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "event": redact_sensitive_text(record.getMessage()),
            "service": self.service,
            "environment": self.environment,
        }
        for field in SAFE_FIELDS:
            if hasattr(record, field):
                value: Any = getattr(record, field)
                payload[field] = redact_sensitive_text(value) if isinstance(value, str) else value
        if record.exc_info is not None:
            payload["exception_type"] = getattr(record.exc_info[0], "__name__", "Unknown")
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def configure_logging(settings: Settings) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter(service=settings.service_name, environment=settings.environment.value)
    )
    logger.handlers.clear()
    logger.addFilter(RedactionFilter())
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, settings.log_level))
    logger.propagate = False


def log_request(
    *,
    settings: Settings,
    request_id: str,
    correlation_id: str,
    method: str,
    route: str,
    status_code: int,
    duration_ms: float,
) -> None:
    logger.info(
        "request_completed",
        extra={
            "request_id": request_id,
            "correlation_id": correlation_id,
            "method": method,
            "route": route,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "environment": settings.environment.value,
            "release_sha": settings.release_sha,
        },
    )
