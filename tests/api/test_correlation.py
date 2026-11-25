from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from fps_platform.observability.request_context import CORRELATION_ID_PATTERN


def test_valid_correlation_id_is_echoed(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Correlation-ID": "trace_abc-123"})
    assert response.headers["X-Correlation-ID"] == "trace_abc-123"


def test_invalid_correlation_id_is_replaced(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Correlation-ID": "bad value!"})
    generated = response.headers["X-Correlation-ID"]
    assert generated != "bad value!"
    assert CORRELATION_ID_PATTERN.fullmatch(generated)


def test_request_id_is_present_and_distinct(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Correlation-ID": "flow-a"})
    assert response.headers["X-Request-ID"] != response.headers["X-Correlation-ID"]
    assert CORRELATION_ID_PATTERN.fullmatch(response.headers["X-Request-ID"])


def test_parallel_requests_keep_correlation_context(client: TestClient) -> None:
    ids = [f"flow-{index}" for index in range(8)]
    with ThreadPoolExecutor(max_workers=8) as executor:
        responses = list(
            executor.map(
                lambda value: client.get("/health/live", headers={"X-Correlation-ID": value}),
                ids,
            )
        )
    assert [response.headers["X-Correlation-ID"] for response in responses] == ids
