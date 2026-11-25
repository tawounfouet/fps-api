from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from fps_platform.bootstrap import create_app
from fps_platform.config import Environment, Settings
from fps_platform.modules.contact.infrastructure.persistence.models import ContactSubmissionRecord

pytestmark = pytest.mark.integration


def payload(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "firstName": "Ada",
        "name": "Lovelace",
        "email": "ada@example.test",
        "phone": None,
        "organisation": None,
        "fonction": None,
        "subject": "Partenariat",
        "message": "Bonjour",
        "rgpdConsent": True,
    }
    body.update(overrides)
    return body


def build_app(*, trusted_proxy_count: int) -> FastAPI:
    settings = Settings(
        _env_file=None,
        environment=Environment.TEST,
        docs_enabled=True,
        allowed_origins=["http://testserver"],
        contact_trusted_proxy_count=trusted_proxy_count,
        log_level="INFO",
    )
    return create_app(settings, include_test_routes=True)


@pytest.fixture
def contact_client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    app = build_app(trusted_proxy_count=1)
    with TestClient(app, raise_server_exceptions=False) as client:
        app.state.session_factory = session_factory
        yield client


def test_forwarded_for_cannot_bypass_rate_limit(contact_client: TestClient) -> None:
    statuses: list[int] = []
    for index in range(6):
        response = contact_client.post(
            "/api/v1/contact",
            json=payload(),
            headers={
                "Idempotency-Key": f"security_proxy_{index:02d}",
                "X-Forwarded-For": f"198.51.100.{index + 1}, 203.0.113.10",
            },
        )
        statuses.append(response.status_code)

    assert statuses == [201, 201, 201, 201, 201, 429]


def test_forwarded_for_is_ignored_without_trusted_proxy(
    session_factory: sessionmaker[Session],
) -> None:
    app = build_app(trusted_proxy_count=0)
    with TestClient(app, raise_server_exceptions=False) as client:
        app.state.session_factory = session_factory
        statuses = []
        for index in range(6):
            response = client.post(
                "/api/v1/contact",
                json=payload(),
                headers={
                    "Idempotency-Key": f"security_no_proxy_{index:02d}",
                    "X-Forwarded-For": f"198.51.100.{index + 1}",
                },
            )
            statuses.append(response.status_code)

    assert statuses == [201, 201, 201, 201, 201, 429]


def test_idempotency_conflict_does_not_create_second_submission(
    contact_client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    headers = {"Idempotency-Key": "security_conflict_key_0001"}
    first = contact_client.post("/api/v1/contact", json=payload(), headers=headers)
    conflict = contact_client.post(
        "/api/v1/contact",
        json=payload(message="Message different"),
        headers=headers,
    )

    assert first.status_code == 201
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "IDEMPOTENCY_KEY_CONFLICT"
    with session_factory() as session:
        assert len(session.scalars(select(ContactSubmissionRecord)).all()) == 1
