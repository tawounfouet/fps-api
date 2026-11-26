from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError
from pydantic_settings import SettingsConfigDict

from fps_platform.config import (
    MAX_MEDIA_MAX_BYTES,
    MAX_MEDIA_SIGNED_URL_TTL_SECONDS,
    Environment,
    Settings,
)
from fps_platform.modules.media.domain.enums import MediaStorageMode


def test_fake_storage_is_the_safe_default() -> None:
    settings = Settings(_env_file=None)
    assert settings.media_storage_mode is MediaStorageMode.FAKE
    assert settings.media_signed_url_ttl_seconds == 300
    assert settings.media_max_bytes == 10485760


def test_media_limits_are_hardened_to_conservative_defaults() -> None:
    assert MAX_MEDIA_SIGNED_URL_TTL_SECONDS == 300
    assert MAX_MEDIA_MAX_BYTES == 10485760
    with pytest.raises(ValidationError):
        Settings(_env_file=None, media_signed_url_ttl_seconds=301)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, media_max_bytes=10485761)


def test_production_may_use_fake_storage_without_real_credentials() -> None:
    settings = Settings(_env_file=None, environment=Environment.PRODUCTION)
    assert settings.environment is Environment.PRODUCTION
    assert settings.media_storage_mode is MediaStorageMode.FAKE


def test_s3_mode_requires_explicit_configuration() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, media_storage_mode=MediaStorageMode.S3)


def test_s3_mode_accepts_minio_configuration() -> None:
    settings = Settings(
        _env_file=None,
        media_storage_mode=MediaStorageMode.S3,
        media_bucket="fps-media-test",
        media_region="local",
        media_endpoint_url="http://minio:9000",
        media_access_key_id=str(uuid4()),
        media_secret_access_key=str(uuid4()),
        media_public_base_url="http://localhost:9000/media",
        media_force_path_style=True,
    )
    assert settings.media_storage_mode is MediaStorageMode.S3
    assert settings.media_endpoint_url == "http://minio:9000"


def test_media_urls_reject_credentials_and_queries() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            media_endpoint_url="https://user:password@storage.example.test/?x=1",
        )


def test_settings_model_config_remains_env_backed() -> None:
    assert Settings.model_config.get("env_file") == ".env"
    assert SettingsConfigDict(case_sensitive=False)["case_sensitive"] is False
