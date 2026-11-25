from __future__ import annotations

from hashlib import sha256

import httpx

from fps_platform.modules.contact.application.ports import (
    ContactEmailMessage,
    EmailDeliveryPort,
    EmailDeliveryReceipt,
)
from fps_platform.modules.contact.domain.exceptions import (
    PermanentContactDeliveryError,
    RetryableContactDeliveryError,
)
from fps_platform.modules.contact.domain.value_objects import normalize_provider_reference


class ResendEmailDeliveryPort(EmailDeliveryPort):
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        sender_email: str,
        recipient_email: str,
        timeout_seconds: float = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._client = client or httpx.Client(
            base_url=base_url,
            timeout=timeout_seconds,
        )
        self._client.headers["Authorization"] = f"Bearer {api_key}"
        self._owns_client = client is None
        self._sender_email = sender_email
        self._recipient_email = recipient_email
        self._receipts: dict[str, EmailDeliveryReceipt] = {}

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def send(self, message: ContactEmailMessage) -> EmailDeliveryReceipt:
        existing = self._receipts.get(message.idempotency_key)
        if existing is not None:
            return existing
        try:
            response = self._client.post("/emails", json=self._build_payload(message))
        except (httpx.TimeoutException, httpx.TransportError):
            raise RetryableContactDeliveryError("email provider transport failure") from None
        status = response.status_code
        status_message = f"email provider returned status {status}"
        if status >= 500 or status == 429:
            raise RetryableContactDeliveryError(status_message) from None
        if not 200 <= status < 300:
            raise PermanentContactDeliveryError(status_message) from None
        receipt = EmailDeliveryReceipt(
            provider="resend",
            provider_reference=self._provider_reference(message, response),
        )
        self._receipts[message.idempotency_key] = receipt
        return receipt

    def _build_payload(self, message: ContactEmailMessage) -> dict[str, object]:
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
        return {
            "from": self._sender_email,
            "to": [self._recipient_email],
            "subject": f"[FPS] {message.subject.value} ({message.locale.value})",
            "text": "\n".join(lines),
        }

    def _provider_reference(self, message: ContactEmailMessage, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        raw = str(payload.get("id") or "") if isinstance(payload, dict) else ""
        try:
            return normalize_provider_reference(raw)
        except ValueError:
            digest = sha256(message.idempotency_key.encode("utf-8")).hexdigest()[:16]
            return f"resend_{digest}"
