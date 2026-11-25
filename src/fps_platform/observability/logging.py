from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
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


class JsonFormatter(logging.Formatter):
    def __init__(self, *, service: str, environment: str) -> None:
        super().__init__()
        self.service = service
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "event": record.getMessage(),
            "service": self.service,
            "environment": self.environment,
        }
        for field in SAFE_FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info is not None:
            payload["exception_type"] = getattr(record.exc_info[0], "__name__", "Unknown")
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def configure_logging(settings: Settings) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter(service=settings.service_name, environment=settings.environment.value)
    )
    logger.handlers.clear()
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
