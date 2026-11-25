from __future__ import annotations

import json
from email.message import EmailMessage
from uuid import uuid4

import httpx

from fps_platform.modules.contact.application.ports import ContactEmailMessage
from fps_platform.modules.contact.domain.enums import ContactLocale, ContactSubject
from fps_platform.modules.contact.domain.value_objects import (
    ContactEmailAddress,
    ContactMessage,
    ContactOptionalText,
    PersonName,
)
from fps_platform.modules.contact.infrastructure.imap import (
    ImapInboxProbePort,
    ImapProbeClient,
)
from fps_platform.modules.contact.infrastructure.resend import ResendEmailDeliveryPort
from fps_platform.modules.contact.infrastructure.smtp import (
    SmtpEmailDeliveryPort,
    SmtpSender,
)


class SandboxSmtpSender:
    def send(
        self, message: EmailMessage, *, from_addr: str, to_addrs: list[str]
    ) -> dict[str, object]:
        return {}

    def close(self) -> None:
        return None


class SandboxImapClient:
    def login(self, user: str, password: str) -> str:
        return "OK"

    def select(self, mailbox: str, *, readonly: bool) -> str:
        return "OK"

    def logout(self) -> None:
        return None


def _message() -> ContactEmailMessage:
    return ContactEmailMessage(
        submission_id=uuid4(),
        idempotency_key="sandbox_fixed_key",
        template_code="contact_request",
        recipient_group_code="contact_team",
        locale=ContactLocale.FR,
        subject=ContactSubject.PARTENARIAT,
        first_name=PersonName("Sandbox"),
        last_name=PersonName("User"),
        email=ContactEmailAddress("sandbox@example.test"),
        phone=None,
        organisation=ContactOptionalText("FPS"),
        job_title=None,
        message=ContactMessage("Smoke sandbox local"),
        rgpd_consent=True,
        correlation_id="smoke-sandbox",
    )


def _run_resend(message: ContactEmailMessage) -> str:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "msg_sandbox_001"})

    with httpx.Client(
        base_url="https://api.example.test",
        transport=httpx.MockTransport(handler),
    ) as client:
        port = ResendEmailDeliveryPort(
            api_key="placeholder-key",
            base_url="https://api.example.test",
            sender_email="sender@example.test",
            recipient_email="ops@example.test",
            client=client,
        )
        receipt = port.send(message)
        port.close()
        return receipt.provider_reference


def _run_smtp(message: ContactEmailMessage) -> str:
    def factory() -> SmtpSender:
        return SandboxSmtpSender()

    port = SmtpEmailDeliveryPort(
        host="smtp.example.test",
        port=465,
        user="placeholder-user",
        password="placeholder-password",
        sender_email="sender@example.test",
        recipient_email="ops@example.test",
        sender_factory=factory,
    )
    receipt = port.send(message)
    port.close()
    return receipt.provider_reference


def _run_imap() -> str:
    def factory() -> ImapProbeClient:
        return SandboxImapClient()

    port = ImapInboxProbePort(
        host="imap.example.test",
        port=993,
        user="placeholder-user",
        password="placeholder-password",
        client_factory=factory,
    )
    return port.probe().status


def main() -> None:
    message = _message()
    report = {
        "resend_reference": _run_resend(message),
        "smtp_reference": _run_smtp(message),
        "imap_status": _run_imap(),
        "network_calls": 0,
    }
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
