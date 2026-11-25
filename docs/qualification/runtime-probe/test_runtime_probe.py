"""M0 BE-000-03 compatibility smoke, separate from FPS application.

Normal mode: four exploratory tests. Strict mode (FPS_COMPAT_STRICT=1):
enforce candidate package versions, psycopg 3, and live PostgreSQL transaction.
Without a DB URL, strict mode FAILS, not skips. No secrets should be logged.
"""
from __future__ import annotations

import importlib
import os
from importlib.metadata import version

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from packaging.version import Version
from pydantic import BaseModel, ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


def test_existing_package_imports() -> None:
    for name in (
        "fastapi", "pydantic", "pydantic_settings", "sqlalchemy",
        "alembic", "pytest", "httpx", "uvicorn",
    ):
        importlib.import_module(name)


def test_sync_fastapi_handler_smoke() -> None:
    app = FastAPI()

    @app.get("/health/live")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    with TestClient(app) as client:
        response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_pydantic_rejects_invalid_data() -> None:
    class Payload(BaseModel):
        count: int

    assert Payload.model_validate({"count": 7}).count == 7
    with pytest.raises(ValidationError):
        Payload.model_validate({"count": "not-an-integer"})


def test_sqlalchemy_local_transaction_commit_and_rollback() -> None:
    # SQLite exploratory only: not proof of psycopg/PostgreSQL isolation.
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE probe_items (id integer primary key, label text NOT NULL)"))
    with Session(engine) as session:
        session.execute(text("INSERT INTO probe_items VALUES (1, :label)"), {"label": "committed"})
        session.commit()
    with Session(engine) as session:
        session.execute(text("INSERT INTO probe_items VALUES (2, :label)"), {"label": "rolled-back"})
        session.rollback()
    with Session(engine) as session:
        rows = session.execute(text("SELECT id, label FROM probe_items ORDER BY id")).all()
    assert rows == [(1, "committed")]
    engine.dispose()


def test_strict_candidate_package_versions() -> None:
    if os.environ.get("FPS_COMPAT_STRICT") != "1":
        pytest.skip("Only run as M0 gate proof with FPS_COMPAT_STRICT=1")
    minima = {
        "fastapi": "0.165.0",
        "pydantic": "2.14.0",
        "SQLAlchemy": "2.1.0",
        "alembic": "1.17.0",
        "psycopg": "3.2.0",
        "pytest": "8.0.0",
        "httpx": "0.28.0",
    }
    for distribution, minimum in minima.items():
        actual = Version(version(distribution))
        assert actual >= Version(minimum), (distribution, str(actual), minimum)
    importlib.import_module("psycopg")


def test_strict_postgresql_commit_and_rollback() -> None:
    if os.environ.get("FPS_COMPAT_STRICT") != "1":
        pytest.skip("Only run as M0 gate proof with FPS_COMPAT_STRICT=1")
    raw_url = os.environ.get("FPS_COMPAT_DATABASE_URL")
    assert raw_url, "FPS_COMPAT_DATABASE_URL must point to an isolated PostgreSQL test DB"
    assert raw_url.startswith("postgresql+psycopg://"), "Use explicit psycopg3 SQLAlchemy dialect"
    engine = create_engine(raw_url, pool_pre_ping=True)
    try:
        with engine.begin() as connection:
            db_version = connection.execute(text("SHOW server_version_num")).scalar_one()
            assert int(db_version) // 10000 >= 17, "PostgreSQL 17+ compatibility target"
            connection.execute(text("CREATE TEMP TABLE fps_m0_probe (id integer primary key, label text NOT NULL) ON COMMIT PRESERVE ROWS"))
            connection.execute(text("INSERT INTO fps_m0_probe VALUES (1, 'committed')"))
        # A temp table is connection-scoped: test commit/rollback using SAME
        # connection in an explicit transaction, with no persistent DB writes.
        with engine.connect() as conn:
            with conn.begin():
                conn.execute(text("CREATE TEMP TABLE fps_m0_probe2 (id integer primary key, label text NOT NULL) ON COMMIT PRESERVE ROWS"))
                conn.execute(text("INSERT INTO fps_m0_probe2 VALUES (1, 'committed')"))
            tx = conn.begin()
            conn.execute(text("INSERT INTO fps_m0_probe2 VALUES (2, 'rolled-back')"))
            tx.rollback()
            values = conn.execute(text("SELECT id FROM fps_m0_probe2 ORDER BY id")).scalars().all()
            assert values == [1]
    finally:
        engine.dispose()
