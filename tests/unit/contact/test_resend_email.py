from __future__ import annotations

import json
from collections.abc import Callable
from uuid import uuid4

import httpx
import pytest

from fps_platform.bootstrap import build_email_port
from fps_platform.config import Environment, Settings
from fps_platform.modules.contact.application.ports import ContactEmailMessage
from fps_platform.modules.contact.domain.enums import (
    ContactEmailProviderMode,
    ContactLocale,
    ContactSubject,
)
from fps_platform.modules.contact.domain.exceptions import (
    PermanentContactDeliveryError,
    RetryableContactDeliveryError,
)
from fps_platform.modules.contact.domain.value_objects import (
    ContactEmailAddress,
    ContactMessage,
    ContactOptionalText,
    PersonName,
)
from fps_platform.modules.contact.infrastructure.resend import ResendEmailDeliveryPort

BASE_URL = "https://api.example.test"


def _message() -> ContactEmailMessage:
    return ContactEmailMessage(
        submission_id=uuid4(),
        idempotency_key=f"resend_test_{uuid4().hex}",
        template_code="contact_request",
        recipient_group_code="contact_team",
        locale=ContactLocale.FR,
        subject=ContactSubject.PARTENARIAT,
        first_name=PersonName("Ada"),
        last_name=PersonName("Lovelace"),
        email=ContactEmailAddress("ada@example.test"),
        phone=None,
        organisation=ContactOptionalText("Analytical Engines"),
        job_title=None,
        message=ContactMessage("Bonjour"),
        rgpd_consent=True,
        correlation_id="correlation-123",
    )


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        contact_email_provider_mode=ContactEmailProviderMode.RESEND,
        contact_email_provider="resend",
        resend_api_key="placeholder-key",
        resend_base_url=BASE_URL,
        sender_email="sender@example.test",
        notify_email="ops@example.test",
    )


def _port(handler: Callable[[httpx.Request], httpx.Response]) -> ResendEmailDeliveryPort:
    client = httpx.Client(base_url=BASE_URL, transport=httpx.MockTransport(handler))
    return ResendEmailDeliveryPort(
        api_key="placeholder-key",
        base_url=BASE_URL,
        sender_email="sender@example.test",
        recipient_email="ops@example.test",
        client=client,
    )


def test_resend_success_returns_sanitized_receipt() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"id": "msg_123"})

    port = _port(handler)
    receipt = port.send(_message())
    assert receipt.provider == "resend"
    assert receipt.provider_reference == "msg_123"
    assert requests[0].headers["Authorization"] == "Bearer placeholder-key"
    payload = json.loads(requests[0].content)
    assert payload["from"] == "sender@example.test"
    assert payload["to"] == ["ops@example.test"]


def test_resend_reuses_receipt_for_same_idempotency_key() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"id": "msg_456"})

    port = _port(handler)
    message = _message()
    first = port.send(message)
    second = port.send(message)
    assert first == second
    assert len(calls) == 1


def test_resend_server_error_is_retryable_without_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="sensitive provider body")

    port = _port(handler)
    with pytest.raises(RetryableContactDeliveryError) as exc:
        port.send(_message())
    assert "status 503" in str(exc.value)
    assert "sensitive provider body" not in str(exc.value)
    assert "ada@example.test" not in str(exc.value)


def test_resend_client_error_is_permanent_without_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="invalid request with private data")

    port = _port(handler)
    with pytest.raises(PermanentContactDeliveryError) as exc:
        port.send(_message())
    assert "status 400" in str(exc.value)
    assert "private data" not in str(exc.value)


def test_resend_redirect_is_not_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"Location": "https://example.test/redirect"})

    port = _port(handler)
    with pytest.raises(PermanentContactDeliveryError, match="status 302"):
        port.send(_message())


def test_resend_timeout_is_retryable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out with details", request=request)

    port = _port(handler)
    with pytest.raises(RetryableContactDeliveryError) as exc:
        port.send(_message())
    assert "transport failure" in str(exc.value)
    assert "details" not in str(exc.value)


def test_resend_unsafe_provider_id_falls_back_to_digest() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "unsafe id with spaces"})

    port = _port(handler)
    receipt = port.send(_message())
    assert receipt.provider_reference.startswith("resend_")
    assert " " not in receipt.provider_reference


def test_build_email_port_selects_resend_without_network() -> None:
    port = build_email_port(_settings())
    assert isinstance(port, ResendEmailDeliveryPort)
    port.close()


def test_mock_mode_requires_no_resend_configuration() -> None:
    settings = Settings(_env_file=None)
    port = build_email_port(settings)
    assert not isinstance(port, ResendEmailDeliveryPort)


def test_production_rejects_insecure_resend_base_url() -> None:
    with pytest.raises(Exception, match="RESEND_BASE_URL"):
        Settings(
            _env_file=None,
            environment=Environment.PRODUCTION,
            allowed_origins=["https://example.test"],
            contact_email_provider_mode=ContactEmailProviderMode.RESEND,
            contact_email_provider="resend",
            resend_api_key="placeholder-key",
            resend_base_url="http://api.example.test",
            sender_email="sender@example.test",
            notify_email="ops@example.test",
        )
