from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from fps_platform.config import Environment, Settings
from fps_platform.observability.request_context import CORRELATION_ID_PATTERN


def test_request_log_is_structured_and_pii_safe(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="fps_platform.request")
    response = client.get(
        "/_test/validation",
        params={"value": "secret@example.test"},
        headers={"X-Secret": "never-log-this-token", "X-Correlation-ID": "flow-log"},
    )
    assert response.status_code == 422
    records = [
        record
        for record in caplog.records
        if record.message == "request_completed"
        and getattr(record, "correlation_id", None) == "flow-log"
    ]
    assert len(records) == 1
    serialized = str(vars(records[0]))
    assert "secret@example.test" not in serialized
    assert "never-log-this-token" not in serialized
    assert getattr(records[0], "status_code", None) == 422
    assert CORRELATION_ID_PATTERN.fullmatch(str(response.headers["X-Correlation-ID"]))


def test_production_app_disables_docs() -> None:
    from fps_platform.bootstrap import create_app

    settings = Settings(
        _env_file=None,
        environment=Environment.PRODUCTION,
        allowed_origins=["https://example.test"],
        docs_enabled=True,
    )
    app = create_app(settings)
    assert app.docs_url is None
    assert app.openapi_url is None
    assert app.redoc_url is None
