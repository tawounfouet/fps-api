from __future__ import annotations

import pytest
from pydantic import ValidationError

from fps_platform.config import Environment, Settings


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
