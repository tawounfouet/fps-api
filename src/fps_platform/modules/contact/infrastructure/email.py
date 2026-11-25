from __future__ import annotations

from hashlib import sha256

from fps_platform.modules.contact.application.ports import (
    ContactEmailMessage,
    EmailDeliveryPort,
    EmailDeliveryReceipt,
)
from fps_platform.modules.contact.domain.exceptions import PermanentContactDeliveryError


class MockEmailDeliveryPort(EmailDeliveryPort):
    def __init__(self, provider: str = "mock") -> None:
        self._provider = provider

    def send(self, message: ContactEmailMessage) -> EmailDeliveryReceipt:
        digest = sha256(
            f"{message.submission_id}:{message.template_code}:{message.locale.value}".encode()
        ).hexdigest()
        return EmailDeliveryReceipt(
            provider=self._provider, provider_reference=f"mock_{digest[:16]}"
        )


class DisabledEmailDeliveryPort(EmailDeliveryPort):
    def send(self, message: ContactEmailMessage) -> EmailDeliveryReceipt:
        raise PermanentContactDeliveryError("contact email provider is disabled")
