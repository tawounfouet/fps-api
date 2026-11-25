from __future__ import annotations

from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

pytestmark = pytest.mark.integration

IDEMPOTENCY_KEY = "contract_contact_key_0001"


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


def test_contact_public_contract_matches_vite_field_names(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    cast(FastAPI, client.app).state.session_factory = session_factory
    response = client.post(
        "/api/v1/contact",
        json=payload(),
        headers={"Idempotency-Key": IDEMPOTENCY_KEY},
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "workflow_status", "delivery_status", "replayed"}
    assert body["workflow_status"] == "RECEIVED"
    assert body["delivery_status"] == "PENDING"
    assert body["replayed"] is False
    assert response.headers["cache-control"] == "no-store"


def test_openapi_declares_idempotency_key_as_required(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema: dict[str, Any] = response.json()
    operation = schema["paths"]["/api/v1/contact"]["post"]
    parameters = operation["parameters"]
    idempotency = next(item for item in parameters if item["name"] == "Idempotency-Key")
    assert idempotency["required"] is True
    assert idempotency["in"] == "header"
