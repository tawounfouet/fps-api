from __future__ import annotations

import contextlib
import smtplib
import ssl
from collections.abc import Callable
from email.message import EmailMessage
from hashlib import sha256
from typing import Protocol

from fps_platform.modules.contact.application.ports import (
    ContactEmailMessage,
    EmailDeliveryPort,
    EmailDeliveryReceipt,
)
from fps_platform.modules.contact.domain.exceptions import (
    PermanentContactDeliveryError,
    RetryableContactDeliveryError,
)


class SmtpSender(Protocol):
    def send(
        self, message: EmailMessage, *, from_addr: str, to_addrs: list[str]
    ) -> dict[str, object]: ...

    def close(self) -> None: ...


class SmtpLibSender:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        use_ssl: bool,
        timeout: float,
    ) -> None:
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._use_ssl = use_ssl
        self._timeout = timeout

    def _create_client(self) -> smtplib.SMTP:
        context = ssl.create_default_context()
        if self._use_ssl:
            return smtplib.SMTP_SSL(self._host, self._port, timeout=self._timeout, context=context)
        client = smtplib.SMTP(self._host, self._port, timeout=self._timeout)
        try:
            client.starttls(context=context)
        except Exception:
            client.close()
            raise
        return client

    def send(
        self, message: EmailMessage, *, from_addr: str, to_addrs: list[str]
    ) -> dict[str, object]:
        client: smtplib.SMTP | None = None
        try:
            client = self._create_client()
            client.login(self._user, self._password)
            refused = client.send_message(message, from_addr=from_addr, to_addrs=to_addrs)
            return dict(refused)
        except smtplib.SMTPAuthenticationError:
            raise PermanentContactDeliveryError("smtp authentication failed") from None
        except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused):
            raise PermanentContactDeliveryError("smtp address refused") from None
        except smtplib.SMTPDataError as exc:
            if exc.smtp_code >= 500:
                raise PermanentContactDeliveryError("smtp server rejected message") from None
            raise RetryableContactDeliveryError("smtp server deferred message") from None
        except (smtplib.SMTPException, OSError, TimeoutError):
            raise RetryableContactDeliveryError("smtp transport failure") from None
        finally:
            if client is not None:
                with contextlib.suppress(smtplib.SMTPException):
                    client.quit()

    def close(self) -> None:
        return None


class SmtpEmailDeliveryPort(EmailDeliveryPort):
    def __init__(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        sender_email: str,
        recipient_email: str,
        use_ssl: bool = True,
        timeout_seconds: float = 10.0,
        sender_factory: Callable[[], SmtpSender] | None = None,
    ) -> None:
        self._sender = sender_factory or (
            lambda: SmtpLibSender(
                host=host,
                port=port,
                user=user,
                password=password,
                use_ssl=use_ssl,
                timeout=timeout_seconds,
            )
        )
        self._sender_instance = self._sender()
        self._sender_email = sender_email
        self._recipient_email = recipient_email
        self._receipts: dict[str, EmailDeliveryReceipt] = {}

    def close(self) -> None:
        self._sender_instance.close()

    def send(self, message: ContactEmailMessage) -> EmailDeliveryReceipt:
        existing = self._receipts.get(message.idempotency_key)
        if existing is not None:
            return existing
        refused = self._sender_instance.send(
            self._build_message(message),
            from_addr=self._sender_email,
            to_addrs=[self._recipient_email],
        )
        if refused:
            raise RetryableContactDeliveryError("smtp recipient refused")
        receipt = EmailDeliveryReceipt(
            provider="smtp",
            provider_reference=self._provider_reference(message),
        )
        self._receipts[message.idempotency_key] = receipt
        return receipt

    def _build_message(self, message: ContactEmailMessage) -> EmailMessage:
        email_message = EmailMessage()
        email_message["From"] = self._sender_email
        email_message["To"] = self._recipient_email
        email_message["Subject"] = f"[FPS] {message.subject.value} ({message.locale.value})"
        lines = [
            f"Nom: {message.first_name.value} {message.last_name.value}",
            f"Email: {message.email.value}",
            f"Subject: {message.subject.value}",
            f"Locale: {message.locale.value}",
            f"Organisation: {message.organisation.value if message.organisation else '-'}",
            f"Fonction: {message.job_title.value if message.job_title else '-'}",
            f"Telephone: {message.phone.value if message.phone else '-'}",
            f"Consentement RGPD: {'oui' if message.rgpd_consent else 'non'}",
            f"Correlation ID: {message.correlation_id}",
            "",
            message.message.value,
        ]
        email_message.set_content("\n".join(lines))
        return email_message

    def _provider_reference(self, message: ContactEmailMessage) -> str:
        digest = sha256(message.idempotency_key.encode("utf-8")).hexdigest()[:16]
        return f"smtp_{digest}"
