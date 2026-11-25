from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fps_platform.bootstrap import create_app
from fps_platform.config import Environment, Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment=Environment.TEST,
        docs_enabled=True,
        allowed_origins=["http://testserver"],
        database_url=None,
        log_level="INFO",
        release_sha="test-sha",
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings, include_test_routes=True)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
