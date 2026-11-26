from __future__ import annotations

import logging

import pytest

from fps_platform.observability.logging import (
    JsonFormatter,
    RedactionFilter,
    redact_sensitive_text,
    safe_exception_message,
)

LEAK_PAYLOADS = (
    "https://storage.test/signed-upload?X-Amz-Signature=deadbeef",
    "https://storage.test/image?signature=deadbeef&bucket=synthetic",
    "https://storage.test/image?se=2030-01-01T00:00:00Z&sp=r&sig=deadbeef",
    "prefix X-Amz-Signature=deadbeef suffix",
)
FORBIDDEN = ("deadbeef", "X-Amz-Signature", "signature=", "se=", "sp=", "sig=")


@pytest.mark.parametrize("payload", LEAK_PAYLOADS)
def test_signed_url_markers_are_redacted(payload: str) -> None:
    redacted = redact_sensitive_text(payload)

    for token in FORBIDDEN:
        assert token.lower() not in redacted.lower()


def test_redaction_preserves_safe_log_fields() -> None:
    redacted = redact_sensitive_text("request_completed status=200 duration_ms=12.5")

    assert redacted == "request_completed status=200 duration_ms=12.5"


def test_exception_messages_are_redacted() -> None:
    error = RuntimeError(LEAK_PAYLOADS[0])

    message = safe_exception_message(error)

    for token in FORBIDDEN:
        assert token.lower() not in message.lower()
    assert "RuntimeError" not in message


def test_log_record_filter_redacts_message_and_extra_fields() -> None:
    record = logging.LogRecord(
        name="fps_platform.request",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="failed for %s",
        args=(LEAK_PAYLOADS[0],),
        exc_info=None,
    )
    record.route = LEAK_PAYLOADS[1]

    assert RedactionFilter().filter(record) is True
    assert all(token.lower() not in record.getMessage().lower() for token in FORBIDDEN)
    assert all(
        token.lower() not in str(record.route).lower()  # type: ignore[attr-defined]
        for token in FORBIDDEN
    )


def test_json_formatter_redacts_signed_urls() -> None:
    formatter = JsonFormatter(service="fps-platform-api", environment="test")
    record = logging.LogRecord(
        name="fps_platform.request",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=LEAK_PAYLOADS[0],
        args=(),
        exc_info=None,
    )
    record.correlation_id = "safe-correlation"

    formatted = formatter.format(record)

    for token in FORBIDDEN:
        assert token.lower() not in formatted.lower()
    assert "safe-correlation" in formatted


def test_long_payload_is_bounded() -> None:
    redacted = redact_sensitive_text("a" * 2000, limit=128)

    assert len(redacted) <= 128 + len("...[TRUNCATED]")
    assert redacted.endswith("...[TRUNCATED]")
