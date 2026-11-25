from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from fps_platform.api.schemas import ErrorResponse


def test_liveness_is_available(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version_never_exposes_secrets(client: TestClient) -> None:
    response = client.get("/version")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "fps-platform-api"
    assert payload["version"] == "1.0.0"
    assert payload["environment"] == "test"
    assert payload["release_sha"] == "test-sha"
    assert "database" not in payload


def test_readiness_fails_without_database(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 503
    ErrorResponse.model_validate(response.json())


def test_readiness_succeeds_with_working_connection(client: TestClient, app: FastAPI) -> None:
    engine = create_engine("sqlite://")
    app.state.db_engine = engine
    try:
        response = client.get("/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready", "database": "ok"}
    finally:
        engine.dispose()


def test_readiness_never_exposes_dependency_details(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert "postgres" not in response.text.lower()
    assert "password" not in response.text.lower()
