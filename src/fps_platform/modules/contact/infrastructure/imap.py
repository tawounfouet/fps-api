from __future__ import annotations

import imaplib
import ssl
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from fps_platform.modules.contact.domain.exceptions import (
    PermanentContactDeliveryError,
    RetryableContactDeliveryError,
)


class ImapProbeClient(Protocol):
    def login(self, user: str, password: str) -> str: ...

    def select(self, mailbox: str, *, readonly: bool) -> str: ...

    def logout(self) -> None: ...


class ImapLibProbeClient:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        use_ssl: bool,
        timeout: float,
    ) -> None:
        context = ssl.create_default_context()
        self._client = (
            imaplib.IMAP4_SSL(host, port, timeout=timeout, ssl_context=context)
            if use_ssl
            else imaplib.IMAP4(host, port, timeout=timeout)
        )

    def login(self, user: str, password: str) -> str:
        try:
            status, _ = self._client.login(user, password)
        except imaplib.IMAP4.abort:
            raise RetryableContactDeliveryError("imap transport failure") from None
        except OSError:
            raise RetryableContactDeliveryError("imap transport failure") from None
        except imaplib.IMAP4.error:
            raise PermanentContactDeliveryError("imap login failed") from None
        if status != "OK":
            raise PermanentContactDeliveryError("imap login failed")
        return status

    def select(self, mailbox: str, *, readonly: bool) -> str:
        try:
            status, _ = self._client.select(mailbox, readonly=readonly)
        except imaplib.IMAP4.abort:
            raise RetryableContactDeliveryError("imap transport failure") from None
        except (imaplib.IMAP4.error, OSError, TimeoutError):
            raise RetryableContactDeliveryError("imap selection failure") from None
        if status != "OK":
            raise RetryableContactDeliveryError("imap selection failure")
        return status

    def logout(self) -> None:
        try:
            self._client.logout()
        except (imaplib.IMAP4.error, OSError):
            return None


@dataclass(frozen=True, slots=True)
class ImapProbeResult:
    provider: str
    mailbox: str
    status: str


class ImapInboxProbePort:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        use_ssl: bool = True,
        timeout_seconds: float = 10.0,
        client_factory: Callable[[], ImapProbeClient] | None = None,
    ) -> None:
        self._client_factory = client_factory or (
            lambda: ImapLibProbeClient(
                host=host,
                port=port,
                use_ssl=use_ssl,
                timeout=timeout_seconds,
            )
        )
        self._user = user
        self._password = password

    def probe(self, mailbox: str = "INBOX") -> ImapProbeResult:
        client = self._client_factory()
        try:
            login_status = client.login(self._user, self._password)
            if login_status != "OK":
                raise PermanentContactDeliveryError("imap login failed")
            select_status = client.select(mailbox, readonly=True)
            if select_status != "OK":
                raise RetryableContactDeliveryError("imap selection failure")
        finally:
            client.logout()
        return ImapProbeResult(
            provider="imap",
            mailbox=mailbox,
            status=f"{login_status}/{select_status}",
        )
