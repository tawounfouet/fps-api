from __future__ import annotations

from enum import StrEnum
from urllib.parse import urlparse

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from fps_platform.modules.contact.domain.enums import ContactEmailProviderMode

ALLOWED_LOG_LEVELS = frozenset({"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"})
DATABASE_SCHEMES = frozenset({"postgresql", "postgresql+psycopg"})
OIDC_ALGORITHMS = frozenset({"RS256", "ES256", "PS256"})
MIN_CONTACT_RATE_LIMIT = 1
MAX_CONTACT_RATE_LIMIT = 1000
MIN_CONTACT_BODY_BYTES = 1024
MAX_CONTACT_BODY_BYTES = 65536
MAX_CONTACT_PROXY_COUNT = 10
MAX_CONTACT_RETRY_DELAY_SECONDS = 86400


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    service_name: str = "fps-platform-api"
    api_name: str = "FPS Content Platform API"
    api_version: str = "1.0.0"
    environment: Environment = Environment.DEVELOPMENT
    release_sha: str | None = None
    debug: bool = False
    docs_enabled: bool = True
    log_level: str = "INFO"
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    database_url: SecretStr | None = None
    db_pool_size: int = 5
    db_max_overflow: int = 5
    db_pool_timeout: int = 5
    db_pool_recycle: int = 1800
    db_connect_timeout: int = 2
    oidc_enabled: bool = False
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    oidc_algorithms: list[str] = Field(default_factory=lambda: ["RS256"])
    oidc_jwks_cache_ttl_seconds: int = 300
    oidc_clock_leeway_seconds: int = 30
    contact_rate_limit_per_window: int = 5
    contact_rate_limit_window_seconds: int = 600
    contact_max_body_bytes: int = 16384
    contact_trusted_proxy_count: int = 0
    contact_email_provider_mode: ContactEmailProviderMode = ContactEmailProviderMode.MOCK
    contact_email_provider: str = "mock"
    contact_email_template_code: str = "contact_request"
    contact_email_recipient_group_code: str = "contact_team"
    contact_delivery_max_attempts: int = 5
    contact_delivery_retry_delays_seconds: list[int] = Field(
        default_factory=lambda: [60, 300, 1500, 7200]
    )
    contact_worker_lease_seconds: int = 60
    contact_worker_batch_size: int = 20

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in ALLOWED_LOG_LEVELS:
            raise ValueError("LOG_LEVEL must be one of CRITICAL, ERROR, WARNING, INFO, DEBUG")
        return normalized

    @field_validator("allowed_origins")
    @classmethod
    def validate_allowed_origins(cls, values: list[str]) -> list[str]:
        if not values:
            raise ValueError("ALLOWED_ORIGINS must contain at least one origin")
        for value in values:
            if value == "*" or any(character.isspace() for character in value):
                raise ValueError("ALLOWED_ORIGINS must not contain wildcard or whitespace")
            try:
                AnyHttpUrl(value)
            except ValueError as exc:
                raise ValueError("ALLOWED_ORIGINS contains an invalid URL") from exc
        return values

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr | None) -> SecretStr | None:
        if value is None:
            return None
        raw = value.get_secret_value()
        parsed = urlparse(raw)
        if parsed.scheme not in DATABASE_SCHEMES:
            raise ValueError("DATABASE_URL must use postgresql or postgresql+psycopg")
        if parsed.hostname is None or parsed.username is None or parsed.password is None:
            raise ValueError("DATABASE_URL must include host, username and password")
        return value

    @field_validator("db_pool_size")
    @classmethod
    def validate_db_pool_size(cls, value: int) -> int:
        if value < 1 or value > 50:
            raise ValueError("DB_POOL_SIZE must be between 1 and 50")
        return value

    @field_validator("db_max_overflow")
    @classmethod
    def validate_db_max_overflow(cls, value: int) -> int:
        if value < 0 or value > 50:
            raise ValueError("DB_MAX_OVERFLOW must be between 0 and 50")
        return value

    @field_validator("db_pool_timeout")
    @classmethod
    def validate_db_pool_timeout(cls, value: int) -> int:
        if value < 1 or value > 60:
            raise ValueError("DB_POOL_TIMEOUT must be between 1 and 60")
        return value

    @field_validator("db_pool_recycle")
    @classmethod
    def validate_db_pool_recycle(cls, value: int) -> int:
        if value < 30 or value > 86400:
            raise ValueError("DB_POOL_RECYCLE must be between 30 and 86400")
        return value

    @field_validator("db_connect_timeout")
    @classmethod
    def validate_db_connect_timeout(cls, value: int) -> int:
        if value < 1 or value > 30:
            raise ValueError("DB_CONNECT_TIMEOUT must be between 1 and 30")
        return value

    @field_validator("oidc_algorithms")
    @classmethod
    def validate_oidc_algorithms(cls, values: list[str]) -> list[str]:
        if not values:
            raise ValueError("OIDC_ALGORITHMS must contain at least one algorithm")
        normalized = [value.strip().upper() for value in values]
        unsupported = [value for value in normalized if value not in OIDC_ALGORITHMS]
        if unsupported or len(set(normalized)) != len(normalized):
            raise ValueError("OIDC_ALGORITHMS contains unsupported or duplicate algorithms")
        return normalized

    @field_validator("oidc_jwks_cache_ttl_seconds")
    @classmethod
    def validate_oidc_jwks_cache_ttl(cls, value: int) -> int:
        if value < 30 or value > 86400:
            raise ValueError("OIDC_JWKS_CACHE_TTL_SECONDS must be between 30 and 86400")
        return value

    @field_validator("oidc_clock_leeway_seconds")
    @classmethod
    def validate_oidc_clock_leeway(cls, value: int) -> int:
        if value < 0 or value > 120:
            raise ValueError("OIDC_CLOCK_LEEWAY_SECONDS must be between 0 and 120")
        return value

    @field_validator("contact_rate_limit_per_window")
    @classmethod
    def validate_contact_rate_limit(cls, value: int) -> int:
        if value < MIN_CONTACT_RATE_LIMIT or value > MAX_CONTACT_RATE_LIMIT:
            raise ValueError("CONTACT_RATE_LIMIT_PER_WINDOW is out of range")
        return value

    @field_validator("contact_rate_limit_window_seconds", "contact_worker_lease_seconds")
    @classmethod
    def validate_contact_seconds(cls, value: int) -> int:
        if value < 1 or value > 86400:
            raise ValueError("contact duration settings must be between 1 and 86400 seconds")
        return value

    @field_validator("contact_max_body_bytes")
    @classmethod
    def validate_contact_max_body_bytes(cls, value: int) -> int:
        if value < MIN_CONTACT_BODY_BYTES or value > MAX_CONTACT_BODY_BYTES:
            raise ValueError("CONTACT_MAX_BODY_BYTES is out of range")
        return value

    @field_validator("contact_trusted_proxy_count")
    @classmethod
    def validate_contact_trusted_proxy_count(cls, value: int) -> int:
        if value < 0 or value > MAX_CONTACT_PROXY_COUNT:
            raise ValueError("CONTACT_TRUSTED_PROXY_COUNT is out of range")
        return value

    @field_validator("contact_delivery_max_attempts")
    @classmethod
    def validate_contact_delivery_max_attempts(cls, value: int) -> int:
        if value < 1 or value > 100:
            raise ValueError("CONTACT_DELIVERY_MAX_ATTEMPTS is out of range")
        return value

    @field_validator("contact_delivery_retry_delays_seconds")
    @classmethod
    def validate_contact_retry_delays(cls, values: list[int]) -> list[int]:
        if len(values) > 99:
            raise ValueError("CONTACT_DELIVERY_RETRY_DELAYS_SECONDS is too long")
        for value in values:
            if value < 1 or value > MAX_CONTACT_RETRY_DELAY_SECONDS:
                raise ValueError("CONTACT_DELIVERY_RETRY_DELAYS_SECONDS contains an invalid value")
        return values

    @field_validator("contact_worker_batch_size")
    @classmethod
    def validate_contact_worker_batch_size(cls, value: int) -> int:
        if value < 1 or value > 100:
            raise ValueError("CONTACT_WORKER_BATCH_SIZE must be between 1 and 100")
        return value

    @model_validator(mode="after")
    def enforce_contact_policy(self) -> Settings:
        expected_provider = {
            ContactEmailProviderMode.MOCK: "mock",
            ContactEmailProviderMode.DISABLED: "disabled",
        }[self.contact_email_provider_mode]
        if self.contact_email_provider != expected_provider:
            raise ValueError("contact email provider is inconsistent with the selected mode")
        expected_delays = self.contact_delivery_max_attempts - 1
        if len(self.contact_delivery_retry_delays_seconds) < expected_delays:
            raise ValueError("CONTACT_DELIVERY_RETRY_DELAYS_SECONDS is missing retry delays")
        return self

    @model_validator(mode="after")
    def enforce_oidc_policy(self) -> Settings:
        if not self.oidc_enabled:
            return self
        if not self.oidc_issuer or not self.oidc_audience or not self.oidc_jwks_url:
            raise ValueError(
                "OIDC_ISSUER, OIDC_AUDIENCE and OIDC_JWKS_URL are required when OIDC is enabled"
            )
        for value, label in (
            (self.oidc_issuer, "OIDC_ISSUER"),
            (self.oidc_jwks_url, "OIDC_JWKS_URL"),
        ):
            parsed = urlparse(value)
            if parsed.scheme not in {"http", "https"} or parsed.netloc == "":
                raise ValueError(f"{label} must be an absolute http or https URL")
            if self.environment is Environment.PRODUCTION and parsed.scheme != "https":
                raise ValueError(f"{label} must use https in production")
        if not self.oidc_audience or len(self.oidc_audience) > 256:
            raise ValueError("OIDC_AUDIENCE must contain between 1 and 256 characters")
        return self

    @model_validator(mode="after")
    def enforce_production_policy(self) -> Settings:
        if self.environment is not Environment.PRODUCTION:
            return self
        if self.debug:
            raise ValueError("DEBUG cannot be enabled in production")
        if self.log_level == "DEBUG":
            raise ValueError("LOG_LEVEL=DEBUG cannot be enabled in production")
        if self.docs_enabled:
            object.__setattr__(self, "docs_enabled", False)
        return self
