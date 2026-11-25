from __future__ import annotations

import re
from typing import cast

from fastapi.testclient import TestClient
from httpx import Response

from fps_platform.api.schemas import ErrorResponse
from fps_platform.observability.request_context import CORRELATION_ID_PATTERN


def assert_envelope(response: Response) -> dict[str, object]:
    payload = ErrorResponse.model_validate(response.json()).model_dump()
    assert CORRELATION_ID_PATTERN.fullmatch(str(payload["correlation_id"]))
    assert payload["details"] is not None
    return payload


def test_validation_error_contract(client: TestClient) -> None:
    response = client.get("/_test/validation")
    assert response.status_code == 422
    payload = assert_envelope(response)
    assert payload["code"] == "VALIDATION_ERROR"
    assert payload["message"] == "The request is invalid."
    assert "fields" in cast(dict[str, object], payload["details"])
    assert "client@example.test" not in response.text


def test_malformed_json_returns_400(client: TestClient) -> None:
    response = client.post(
        "/_test/json",
        content=b'{"value": "secret@example.test",',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 400
    payload = assert_envelope(response)
    assert payload["code"] == "MALFORMED_JSON"
    assert "secret@example.test" not in response.text


def test_unknown_route_contract(client: TestClient) -> None:
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    payload = assert_envelope(response)
    assert payload["code"] == "RESOURCE_NOT_FOUND"


def test_unhandled_error_contract(client: TestClient) -> None:
    response = client.get("/_test/error")
    assert response.status_code == 500
    payload = assert_envelope(response)
    assert payload["code"] == "INTERNAL_ERROR"
    assert "probe failure" not in response.text
    assert "Traceback" not in response.text


def test_correlation_id_matches_documented_shape(client: TestClient) -> None:
    response = client.get("/health/live")
    assert re.fullmatch(r"[0-9a-f-]{36}", response.headers["X-Correlation-ID"])
