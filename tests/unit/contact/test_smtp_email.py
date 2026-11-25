from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from uuid import uuid4

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
from fps_platform.modules.contact.infrastructure.smtp import (
    SmtpEmailDeliveryPort,
    SmtpLibSender,
    SmtpSender,
)


class FakeSmtpSender:
    def __init__(
        self,
        *,
        refused: dict[str, object] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.refused = refused or {}
        self.error = error
        self.calls: list[tuple[EmailMessage, str, list[str]]] = []
        self.closed = False

    def send(
        self, message: EmailMessage, *, from_addr: str, to_addrs: list[str]
    ) -> dict[str, object]:
        self.calls.append((message, from_addr, to_addrs))
        if self.error is not None:
            raise self.error
        return self.refused

    def close(self) -> None:
        self.closed = True


def _message() -> ContactEmailMessage:
    return ContactEmailMessage(
        submission_id=uuid4(),
        idempotency_key=f"smtp_test_{uuid4().hex}",
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


def _port(sender: SmtpSender) -> SmtpEmailDeliveryPort:
    def factory() -> SmtpSender:
        return sender

    return SmtpEmailDeliveryPort(
        host="smtp.example.test",
        port=465,
        user="placeholder-user",
        password="placeholder-password",
        sender_email="sender@example.test",
        recipient_email="ops@example.test",
        sender_factory=factory,
    )


def test_smtp_success_returns_sanitized_receipt() -> None:
    sender = FakeSmtpSender()
    receipt = _port(sender).send(_message())
    assert receipt.provider == "smtp"
    assert receipt.provider_reference.startswith("smtp_")
    assert "ada@example.test" not in receipt.provider_reference
    assert sender.calls[0][1] == "sender@example.test"
    assert sender.calls[0][2] == ["ops@example.test"]


def test_smtp_reuses_receipt_for_same_idempotency_key() -> None:
    sender = FakeSmtpSender()
    port = _port(sender)
    message = _message()
    assert port.send(message) == port.send(message)
    assert len(sender.calls) == 1


def test_smtp_refused_recipient_is_retryable() -> None:
    sender = FakeSmtpSender(refused={"ops@example.test": (550, b"refused")})
    with pytest.raises(RetryableContactDeliveryError, match="recipient refused"):
        _port(sender).send(_message())


def test_smtp_permanent_error_is_not_retried() -> None:
    sender = FakeSmtpSender(error=PermanentContactDeliveryError("smtp authentication failed"))
    with pytest.raises(PermanentContactDeliveryError):
        _port(sender).send(_message())


def test_smtp_retryable_error_is_propagated() -> None:
    sender = FakeSmtpSender(error=RetryableContactDeliveryError("smtp transport failure"))
    with pytest.raises(RetryableContactDeliveryError):
        _port(sender).send(_message())


def test_smtp_close_closes_sender() -> None:
    sender = FakeSmtpSender()
    port = _port(sender)
    port.close()
    assert sender.closed


def test_build_email_port_selects_smtp_without_network() -> None:
    settings = Settings(
        _env_file=None,
        contact_email_provider_mode=ContactEmailProviderMode.SMTP,
        contact_email_provider="smtp",
        smtp_host="smtp.example.test",
        smtp_user="placeholder-user",
        smtp_password="placeholder-password",
        imap_host="imap.example.test",
        imap_user="placeholder-user",
        imap_password="placeholder-password",
        sender_email="sender@example.test",
        notify_email="ops@example.test",
    )
    port = build_email_port(settings)
    assert isinstance(port, SmtpEmailDeliveryPort)
    port.close()


def test_smtp_production_requires_ssl() -> None:
    with pytest.raises(Exception, match="SMTP_USE_SSL"):
        Settings(
            _env_file=None,
            environment=Environment.PRODUCTION,
            allowed_origins=["https://example.test"],
            contact_email_provider_mode=ContactEmailProviderMode.SMTP,
            contact_email_provider="smtp",
            smtp_host="smtp.example.test",
            smtp_user="placeholder-user",
            smtp_password="placeholder-password",
            smtp_use_ssl=False,
            imap_host="imap.example.test",
            imap_user="placeholder-user",
            imap_password="placeholder-password",
            sender_email="sender@example.test",
            notify_email="ops@example.test",
        )


def test_smtp_ssl_uses_verified_context(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, ssl.SSLContext] = {}

    class FakeConnection:
        def __init__(
            self, host: str, port: int, *, timeout: float, context: ssl.SSLContext
        ) -> None:
            captured["context"] = context

        def login(self, user: str, password: str) -> None:
            return None

        def send_message(
            self, message: EmailMessage, *, from_addr: str, to_addrs: list[str]
        ) -> dict[str, object]:
            return {}

        def quit(self) -> None:
            return None

    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeConnection)
    sender = SmtpLibSender(
        host="smtp.example.test",
        port=465,
        user="placeholder-user",
        password="placeholder-password",
        use_ssl=True,
        timeout=10.0,
    )
    sender.send(EmailMessage(), from_addr="sender@example.test", to_addrs=["ops@example.test"])
    assert captured["context"].verify_mode == ssl.CERT_REQUIRED
    assert captured["context"].check_hostname is True


def test_smtp_starttls_uses_verified_context(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, ssl.SSLContext] = {}

    class FakeConnection:
        def __init__(self, host: str, port: int, *, timeout: float) -> None:
            return None

        def starttls(self, *, context: ssl.SSLContext) -> None:
            captured["context"] = context

        def login(self, user: str, password: str) -> None:
            return None

        def send_message(
            self, message: EmailMessage, *, from_addr: str, to_addrs: list[str]
        ) -> dict[str, object]:
            return {}

        def quit(self) -> None:
            return None

    monkeypatch.setattr(smtplib, "SMTP", FakeConnection)
    sender = SmtpLibSender(
        host="smtp.example.test",
        port=587,
        user="placeholder-user",
        password="placeholder-password",
        use_ssl=False,
        timeout=10.0,
    )
    sender.send(EmailMessage(), from_addr="sender@example.test", to_addrs=["ops@example.test"])
    assert captured["context"].verify_mode == ssl.CERT_REQUIRED
    assert captured["context"].check_hostname is True
