from __future__ import annotations

import pytest
from pydantic import ValidationError

from fps_platform.config import Environment, Settings
from fps_platform.modules.contact.domain.enums import ContactEmailProviderMode


def test_default_settings_are_locally_safe() -> None:
    settings = Settings(_env_file=None)
    assert settings.environment is Environment.DEVELOPMENT
    assert settings.docs_enabled is True
    assert settings.allowed_origins == ["http://localhost:3000"]
    assert settings.database_url is None
    assert settings.log_level == "INFO"


def test_production_disables_docs() -> None:
    settings = Settings(
        _env_file=None,
        environment=Environment.PRODUCTION,
        docs_enabled=True,
        allowed_origins=["https://example.test"],
    )
    assert settings.docs_enabled is False


def test_production_rejects_debug() -> None:
    with pytest.raises(ValidationError, match="DEBUG"):
        Settings(
            _env_file=None,
            environment=Environment.PRODUCTION,
            debug=True,
            allowed_origins=["https://example.test"],
        )


def test_production_rejects_debug_log_level() -> None:
    with pytest.raises(ValidationError, match="LOG_LEVEL"):
        Settings(
            _env_file=None,
            environment=Environment.PRODUCTION,
            log_level="DEBUG",
            allowed_origins=["https://example.test"],
        )


def test_wildcard_origin_is_rejected() -> None:
    with pytest.raises(ValidationError, match="ALLOWED_ORIGINS"):
        Settings(_env_file=None, allowed_origins=["*"])


def test_database_url_is_masked() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://fps:super-secret-value@localhost:5432/fps",
    )
    assert "super-secret-value" not in repr(settings)
    assert settings.database_url is not None
    assert settings.database_url.get_secret_value().endswith("/fps")


def test_invalid_database_url_is_rejected() -> None:
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(_env_file=None, database_url="sqlite:///local.db")


def test_oidc_is_disabled_by_default() -> None:
    settings = Settings(_env_file=None)
    assert settings.oidc_enabled is False
    assert settings.oidc_algorithms == ["RS256"]


def test_oidc_requires_issuer_audience_and_jwks() -> None:
    with pytest.raises(ValidationError, match="OIDC_ISSUER"):
        Settings(_env_file=None, oidc_enabled=True)


def test_oidc_rejects_unsupported_algorithm() -> None:
    with pytest.raises(ValidationError, match="OIDC_ALGORITHMS"):
        Settings(_env_file=None, oidc_algorithms=["HS256"])


def test_production_oidc_requires_https() -> None:
    with pytest.raises(ValidationError, match="OIDC_JWKS_URL"):
        Settings(
            _env_file=None,
            environment=Environment.PRODUCTION,
            allowed_origins=["https://example.test"],
            oidc_enabled=True,
            oidc_issuer="https://idp.example.test",
            oidc_audience="fps-api",
            oidc_jwks_url="http://idp.example.test/jwks",
        )


def test_resend_mode_requires_isolated_configuration() -> None:
    with pytest.raises(ValidationError, match="RESEND_API_KEY"):
        Settings(
            _env_file=None,
            contact_email_provider_mode=ContactEmailProviderMode.RESEND,
            contact_email_provider="resend",
        )


def test_resend_configuration_is_masked() -> None:
    settings = Settings(
        _env_file=None,
        contact_email_provider_mode=ContactEmailProviderMode.RESEND,
        contact_email_provider="resend",
        resend_api_key="placeholder-key",
        resend_base_url="https://api.example.test",
        sender_email="sender@example.test",
        notify_email="ops@example.test",
    )
    assert settings.resend_api_key is not None
    assert "placeholder-key" not in repr(settings)
    assert settings.resend_base_url == "https://api.example.test"


def test_resend_mode_rejects_inconsistent_provider() -> None:
    with pytest.raises(ValidationError, match="inconsistent"):
        Settings(
            _env_file=None,
            contact_email_provider_mode=ContactEmailProviderMode.RESEND,
            contact_email_provider="mock",
            resend_api_key="placeholder-key",
            resend_base_url="https://api.example.test",
            sender_email="sender@example.test",
            notify_email="ops@example.test",
        )


def test_resend_base_url_must_be_absolute() -> None:
    with pytest.raises(ValidationError, match="RESEND_BASE_URL"):
        Settings(
            _env_file=None,
            contact_email_provider_mode=ContactEmailProviderMode.RESEND,
            contact_email_provider="resend",
            resend_api_key="placeholder-key",
            resend_base_url="api.example.test",
            sender_email="sender@example.test",
            notify_email="ops@example.test",
        )


@pytest.mark.parametrize(
    "base_url",
    [
        "https://user:pass@api.example.test",
        "https://api.example.test?key=placeholder",
        "https://api.example.test#fragment",
    ],
)
def test_resend_base_url_rejects_sensitive_components(base_url: str) -> None:
    with pytest.raises(ValidationError, match="credentials, query or fragment"):
        Settings(_env_file=None, resend_base_url=base_url)


@pytest.mark.parametrize("timeout", [0, float("nan"), 61])
def test_email_timeout_is_bounded(timeout: float) -> None:
    with pytest.raises(ValidationError, match="EMAIL_REQUEST_TIMEOUT_SECONDS"):
        Settings(_env_file=None, email_request_timeout_seconds=timeout)


def test_smtp_mode_requires_isolated_configuration() -> None:
    with pytest.raises(ValidationError, match="SMTP_HOST"):
        Settings(
            _env_file=None,
            contact_email_provider_mode=ContactEmailProviderMode.SMTP,
            contact_email_provider="smtp",
        )


def test_smtp_mode_does_not_require_imap_configuration() -> None:
    settings = Settings(
        _env_file=None,
        contact_email_provider_mode=ContactEmailProviderMode.SMTP,
        contact_email_provider="smtp",
        smtp_host="smtp.example.test",
        smtp_user="placeholder-user",
        smtp_password="placeholder-password",
        sender_email="sender@example.test",
        notify_email="ops@example.test",
    )
    assert settings.imap_host is None


def test_mail_ports_are_bounded() -> None:
    with pytest.raises(ValidationError, match="mail port"):
        Settings(_env_file=None, smtp_port=0)


def test_mail_passwords_are_masked() -> None:
    settings = Settings(
        _env_file=None,
        smtp_password="placeholder-password",
        imap_host="imap.example.test",
        imap_user="placeholder-user",
        imap_password="placeholder-password",
    )
    assert "placeholder-password" not in repr(settings)
