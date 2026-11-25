from __future__ import annotations

import imaplib
import ssl

import pytest

from fps_platform.bootstrap import build_imap_probe
from fps_platform.config import Settings
from fps_platform.modules.contact.domain.enums import ContactEmailProviderMode
from fps_platform.modules.contact.domain.exceptions import (
    PermanentContactDeliveryError,
    RetryableContactDeliveryError,
)
from fps_platform.modules.contact.infrastructure.imap import (
    ImapInboxProbePort,
    ImapLibProbeClient,
    ImapProbeClient,
)


class FakeImapClient:
    def __init__(
        self,
        *,
        login_status: str = "OK",
        select_status: str = "OK",
        login_error: Exception | None = None,
        select_error: Exception | None = None,
    ) -> None:
        self.login_status = login_status
        self.select_status = select_status
        self.login_error = login_error
        self.select_error = select_error
        self.logged_out = False

    def login(self, user: str, password: str) -> str:
        if self.login_error is not None:
            raise self.login_error
        return self.login_status

    def select(self, mailbox: str, *, readonly: bool) -> str:
        if self.select_error is not None:
            raise self.select_error
        return self.select_status

    def logout(self) -> None:
        self.logged_out = True


def _port(client: ImapProbeClient) -> ImapInboxProbePort:
    def factory() -> ImapProbeClient:
        return client

    return ImapInboxProbePort(
        host="imap.example.test",
        port=993,
        user="placeholder-user",
        password="placeholder-password",
        client_factory=factory,
    )


def test_imap_probe_success_is_sanitized() -> None:
    client = FakeImapClient()
    result = _port(client).probe()
    assert result.provider == "imap"
    assert result.mailbox == "INBOX"
    assert result.status == "OK/OK"
    assert client.logged_out


def test_imap_probe_login_failure_is_permanent() -> None:
    client = FakeImapClient(login_status="NO")
    with pytest.raises(PermanentContactDeliveryError, match="login failed"):
        _port(client).probe()
    assert client.logged_out


def test_imap_probe_select_failure_is_retryable() -> None:
    client = FakeImapClient(select_error=RetryableContactDeliveryError("imap selection failure"))
    with pytest.raises(RetryableContactDeliveryError):
        _port(client).probe()
    assert client.logged_out


def test_imap_probe_errors_never_reveal_password() -> None:
    client = FakeImapClient(
        login_error=PermanentContactDeliveryError("imap login failed"),
    )
    with pytest.raises(PermanentContactDeliveryError) as exc:
        _port(client).probe()
    assert "placeholder-password" not in str(exc.value)


def test_build_imap_probe_uses_config_without_network() -> None:
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
    assert isinstance(build_imap_probe(settings), ImapInboxProbePort)


def test_build_imap_probe_is_none_without_configuration() -> None:
    assert build_imap_probe(Settings(_env_file=None)) is None


def test_imap_ssl_uses_verified_context_and_network_errors_are_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, ssl.SSLContext] = {}

    class FakeConnection:
        def __init__(
            self, host: str, port: int, *, timeout: float, ssl_context: ssl.SSLContext
        ) -> None:
            captured["context"] = ssl_context

        def login(self, user: str, password: str) -> tuple[str, list[str]]:
            raise TimeoutError("network unavailable")

        def select(self, mailbox: str, *, readonly: bool) -> tuple[str, list[str]]:
            return "OK", []

        def logout(self) -> None:
            return None

    monkeypatch.setattr(imaplib, "IMAP4_SSL", FakeConnection)
    client = ImapLibProbeClient(
        host="imap.example.test",
        port=993,
        use_ssl=True,
        timeout=10.0,
    )
    with pytest.raises(RetryableContactDeliveryError, match="transport failure"):
        client.login("placeholder-user", "placeholder-password")
    assert captured["context"].verify_mode == ssl.CERT_REQUIRED
    assert captured["context"].check_hostname is True
