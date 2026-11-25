from __future__ import annotations

from collections.abc import Iterator
from typing import cast
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from fps_platform.modules.identity.application.ports import IdentityUnitOfWork
from fps_platform.modules.identity.domain.permissions import permissions_for
from fps_platform.modules.identity.domain.value_objects import (
    EmailAddress,
    ExternalIdentity,
    RoleCode,
    UserStatus,
)
from fps_platform.shared.auth.dependencies import (
    get_current_principal,
    get_uow_for_principal,
)
from fps_platform.shared.auth.principal import CurrentPrincipal


def make_principal(*, roles: tuple[RoleCode, ...]) -> CurrentPrincipal:
    return CurrentPrincipal(
        user_id=uuid4(),
        email=EmailAddress("admin@example.test"),
        display_name="Admin",
        status=UserStatus.ACTIVE,
        external_identity=ExternalIdentity("https://idp.example.test", "subject-1"),
        roles=roles,
        permissions=frozenset(permissions_for(roles)),
    )


@pytest.fixture
def admin_app(app: FastAPI) -> Iterator[FastAPI]:
    app.dependency_overrides[get_current_principal] = lambda: make_principal(
        roles=(RoleCode.SUPER_ADMIN,)
    )
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def viewer_app(app: FastAPI) -> Iterator[FastAPI]:
    def fake_uow() -> Iterator[IdentityUnitOfWork]:
        yield cast(IdentityUnitOfWork, object())

    app.dependency_overrides[get_current_principal] = lambda: make_principal(
        roles=(RoleCode.VIEWER,)
    )
    app.dependency_overrides[get_uow_for_principal] = fake_uow
    yield app
    app.dependency_overrides.clear()


def test_admin_requires_bearer_token(client: TestClient) -> None:
    response = client.get("/api/v1/admin/me")
    assert response.status_code == 401
    assert response.json()["code"] == "AUTHENTICATION_REQUIRED"
    assert response.headers["cache-control"] == "no-store"


def test_invalid_token_is_rejected(client: TestClient) -> None:
    response = client.get(
        "/api/v1/admin/me",
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_TOKEN"
    assert response.headers["cache-control"] == "no-store"


def test_authenticated_user_can_read_me(admin_app: FastAPI) -> None:
    with TestClient(admin_app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/admin/me")
    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == "admin@example.test"
    assert payload["roles"] == ["SUPER_ADMIN"]
    assert response.headers["cache-control"] == "no-store"


def test_permission_is_required(viewer_app: FastAPI) -> None:
    with TestClient(viewer_app, raise_server_exceptions=False) as client:
        response = client.get("/api/v1/admin/users")
    assert response.status_code == 403
    assert response.json()["code"] == "PERMISSION_DENIED"
    assert response.headers["cache-control"] == "no-store"
