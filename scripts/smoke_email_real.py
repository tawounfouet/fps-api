from __future__ import annotations

import json
import os
from uuid import UUID, uuid4

from fps_platform.config import Settings
from fps_platform.modules.contact.application.ports import ContactEmailMessage
from fps_platform.modules.contact.domain.enums import ContactLocale, ContactSubject
from fps_platform.modules.contact.domain.value_objects import (
    ContactEmailAddress,
    ContactMessage,
    ContactOptionalText,
    PersonName,
)
from fps_platform.modules.contact.infrastructure.imap import ImapInboxProbePort
from fps_platform.modules.contact.infrastructure.resend import ResendEmailDeliveryPort
from fps_platform.modules.contact.infrastructure.smtp import SmtpEmailDeliveryPort

DEFAULT_RESEND_BASE_URL = "https://api.resend.com"


def _recipient() -> str:
    if os.environ.get("FPS_REAL_EMAIL_SMOKE_CONFIRMED") != "1":
        raise RuntimeError("real email smoke requires FPS_REAL_EMAIL_SMOKE_CONFIRMED=1")
    recipient = os.environ.get("FPS_EMAIL_SMOKE_TO")
    if not recipient or "@" not in recipient:
        raise RuntimeError("real email smoke requires FPS_EMAIL_SMOKE_TO")
    return recipient


def _mask(address: str) -> str:
    local, _, domain = address.partition("@")
    if not domain:
        return "***"
    return f"{local[:1]}***@{domain}"


def _message(run_id: str) -> ContactEmailMessage:
    return ContactEmailMessage(
        submission_id=UUID(uuid4().hex),
        idempotency_key=f"real_smoke_{run_id}",
        template_code="contact_request",
        recipient_group_code="contact_team",
        locale=ContactLocale.FR,
        subject=ContactSubject.PARTENARIAT,
        first_name=PersonName("Smoke"),
        last_name=PersonName("Reel"),
        email=ContactEmailAddress("smoke@example.test"),
        phone=None,
        organisation=ContactOptionalText("FPS"),
        job_title=None,
        message=ContactMessage("Smoke reel FPS sans donnee personnelle"),
        rgpd_consent=True,
        correlation_id=f"real-smoke-{run_id}",
    )


def main() -> None:
    recipient = _recipient()
    settings = Settings()
    run_id = uuid4().hex
    message = _message(run_id)

    if settings.resend_api_key is None or settings.sender_email is None:
        raise RuntimeError("resend configuration is incomplete")
    if settings.smtp_host is None or settings.smtp_user is None or settings.smtp_password is None:
        raise RuntimeError("smtp configuration is incomplete")
    if settings.imap_host is None or settings.imap_user is None or settings.imap_password is None:
        raise RuntimeError("imap configuration is incomplete")

    resend_port = ResendEmailDeliveryPort(
        api_key=settings.resend_api_key.get_secret_value(),
        base_url=settings.resend_base_url or DEFAULT_RESEND_BASE_URL,
        sender_email=settings.sender_email,
        recipient_email=recipient,
        timeout_seconds=settings.email_request_timeout_seconds,
    )
    smtp_port = SmtpEmailDeliveryPort(
        host=settings.smtp_host,
        port=settings.smtp_port,
        user=settings.smtp_user,
        password=settings.smtp_password.get_secret_value(),
        sender_email=settings.sender_email,
        recipient_email=recipient,
        use_ssl=settings.smtp_use_ssl,
        timeout_seconds=settings.email_request_timeout_seconds,
    )
    imap_port = ImapInboxProbePort(
        host=settings.imap_host,
        port=settings.imap_port,
        user=settings.imap_user,
        password=settings.imap_password.get_secret_value(),
        use_ssl=settings.imap_use_ssl,
        timeout_seconds=settings.email_request_timeout_seconds,
    )

    try:
        resend_receipt = resend_port.send(message)
        smtp_receipt = smtp_port.send(message)
        imap_result = imap_port.probe()
    finally:
        resend_port.close()
        smtp_port.close()

    report = {
        "imap_status": imap_result.status,
        "recipient_masked": _mask(recipient),
        "resend_provider": resend_receipt.provider,
        "resend_reference": resend_receipt.provider_reference,
        "smtp_provider": smtp_receipt.provider,
        "smtp_reference": smtp_receipt.provider_reference,
    }
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
