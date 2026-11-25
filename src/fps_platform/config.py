from __future__ import annotations

from enum import StrEnum
from urllib.parse import urlparse

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ALLOWED_LOG_LEVELS = frozenset({"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"})
DATABASE_SCHEMES = frozenset({"postgresql", "postgresql+psycopg"})


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
