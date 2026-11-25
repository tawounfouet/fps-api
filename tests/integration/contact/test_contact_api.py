from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from fps_platform.bootstrap import create_app
from fps_platform.config import Environment, Settings
from fps_platform.modules.audit.infrastructure.persistence.models import AuditEventRecord
from fps_platform.modules.contact.infrastructure.persistence.models import (
    ContactDeliveryRecord,
    ContactIdempotencyKeyRecord,
    ContactSubmissionRecord,
)
from fps_platform.modules.outbox.domain.enums import OutboxEventType
from fps_platform.modules.outbox.infrastructure.persistence.models import OutboxEventRecord

pytestmark = pytest.mark.integration

IDEMPOTENCY_KEY = "contact_submission_20261125_001"


def payload(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "firstName": "Ada",
        "name": "Lovelace",
        "email": "ada@example.test",
        "phone": "+33 1 23 45 67 89",
        "organisation": "Analytical Engines",
        "fonction": "Ingenieure",
        "subject": "Partenariat",
        "message": "Bonjour",
        "rgpdConsent": True,
    }
    body.update(overrides)
    return body


def headers(key: str = IDEMPOTENCY_KEY, **overrides: str) -> dict[str, str]:
    values: dict[str, str] = {"Idempotency-Key": key}
    values.update(overrides)
    return values


@pytest.fixture
def contact_app() -> Iterator[FastAPI]:
    settings = Settings(
        _env_file=None,
        environment=Environment.TEST,
        docs_enabled=True,
        allowed_origins=["http://testserver"],
        log_level="INFO",
    )
    app = create_app(settings, include_test_routes=True)
    yield app


@pytest.fixture
def contact_client(
    contact_app: FastAPI, session_factory: sessionmaker[Session]
) -> Iterator[TestClient]:
    with TestClient(contact_app, raise_server_exceptions=False) as client:
        contact_app.state.session_factory = session_factory
        yield client


def test_submit_persists_submission_delivery_outbox_and_audit(
    contact_client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    response = contact_client.post(
        "/api/v1/contact",
        json=payload(),
        headers=headers(),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["workflow_status"] == "RECEIVED"
    assert body["delivery_status"] == "PENDING"
    assert body["replayed"] is False
    assert response.headers["cache-control"] == "no-store"
    assert "email" not in body

    with session_factory() as session:
        submissions = session.scalars(select(ContactSubmissionRecord)).all()
        deliveries = session.scalars(select(ContactDeliveryRecord)).all()
        keys = session.scalars(select(ContactIdempotencyKeyRecord)).all()
        events = session.scalars(select(OutboxEventRecord)).all()
        audits = session.scalars(select(AuditEventRecord)).all()
    assert len(submissions) == 1
    assert len(deliveries) == 1
    assert len(keys) == 1
    assert len(events) == 1
    assert events[0].event_type == OutboxEventType.CONTACT_DELIVERY_REQUESTED.value
    assert audits
    serialized = json.dumps(
        {
            "outbox": events[0].payload_,
            "audit": audits[0].metadata_,
        }
    )
    assert "ada@example.test" not in serialized
    assert "Bonjour" not in serialized


def test_same_key_and_payload_replays_without_new_submission(
    contact_client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    first = contact_client.post("/api/v1/contact", json=payload(), headers=headers())
    second = contact_client.post("/api/v1/contact", json=payload(), headers=headers())
    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["replayed"] is True
    assert second.json()["id"] == first.json()["id"]
    with session_factory() as session:
        assert len(session.scalars(select(ContactSubmissionRecord)).all()) == 1
        assert len(session.scalars(select(ContactDeliveryRecord)).all()) == 1


def test_same_key_with_different_payload_is_rejected(contact_client: TestClient) -> None:
    first = contact_client.post("/api/v1/contact", json=payload(), headers=headers())
    second = contact_client.post(
        "/api/v1/contact",
        json=payload(message="Message different"),
        headers=headers(),
    )
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["code"] == "IDEMPOTENCY_KEY_CONFLICT"


def test_sixth_submission_is_rate_limited(contact_client: TestClient) -> None:
    statuses: list[int] = []
    last_response: Any = None
    for index in range(6):
        last_response = contact_client.post(
            "/api/v1/contact",
            json=payload(),
            headers=headers(f"contact_submission_rate_limit_{index:02d}"),
        )
        statuses.append(last_response.status_code)
    assert statuses == [201, 201, 201, 201, 201, 429]
    assert last_response.json()["code"] == "RATE_LIMITED"
    assert int(last_response.headers["retry-after"]) > 0


def test_payload_limit_and_content_type_are_enforced(contact_client: TestClient) -> None:
    too_large = contact_client.post(
        "/api/v1/contact",
        json=payload(message="x" * 20000),
        headers=headers(),
    )
    assert too_large.status_code == 413
    assert too_large.json()["code"] == "PAYLOAD_TOO_LARGE"

    wrong_type = contact_client.post(
        "/api/v1/contact",
        content=json.dumps(payload()),
        headers=headers("contact_submission_content_type_01", **{"content-type": "text/plain"}),
    )
    assert wrong_type.status_code == 415
    assert wrong_type.json()["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_honeypot_is_rejected(contact_client: TestClient) -> None:
    response = contact_client.post(
        "/api/v1/contact",
        json=payload(website="https://spam.example.test"),
        headers=headers(),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
