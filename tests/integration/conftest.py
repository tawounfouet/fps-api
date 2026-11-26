from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, pool, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from fps_platform.modules.identity.domain.value_objects import UserStatus
from fps_platform.modules.identity.infrastructure.persistence.models import UserRecord
from fps_platform.shared.domain.actor import ActorContext, ActorType
from fps_platform.shared.domain.clock import SystemClock
from fps_platform.shared.domain.identifiers import Uuid4IdGenerator
from fps_platform.shared.infrastructure.persistence.base import Base
from fps_platform.shared.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from tests.fixtures.persistence_probe import ProbeBase

MakeUow = Callable[..., SqlAlchemyUnitOfWork]


@pytest.fixture(scope="session")
def database_url() -> str:
    value = os.getenv("FPS_TEST_DATABASE_URL")
    if value:
        probe = create_engine(value, poolclass=pool.NullPool)
        try:
            with probe.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            pytest.skip("PostgreSQL is not reachable at FPS_TEST_DATABASE_URL")
        finally:
            probe.dispose()
        return value
    if os.getenv("CI") == "true":
        pytest.fail("FPS_TEST_DATABASE_URL is required in CI")
    pytest.skip("FPS_TEST_DATABASE_URL is not set")


@pytest.fixture(scope="session")
def alembic_config(database_url: str) -> Config:
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


@pytest.fixture(scope="session")
def engine(database_url: str, alembic_config: Config) -> Iterator[Engine]:
    engine = create_engine(database_url, poolclass=pool.NullPool)
    Base.metadata.drop_all(engine)
    ProbeBase.metadata.drop_all(engine)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
    command.upgrade(alembic_config, "head")
    ProbeBase.metadata.create_all(engine)
    try:
        yield engine
    finally:
        ProbeBase.metadata.drop_all(engine)
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture(scope="session")
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


@pytest.fixture(autouse=True)
def clean_tables(engine: Engine) -> None:
    tables = (
        "outbox_events",
        "audit_events",
        "contact_deliveries",
        "contact_submissions",
        "contact_idempotency_keys",
        "user_roles",
        "users",
        "roles",
        "media_assets",
        "persistence_probes",
        "persistence_probe_parents",
    )
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE"))


@pytest.fixture
def uploader_user_id(session_factory: sessionmaker[Session], clean_tables: None) -> Iterator[UUID]:
    user_id = uuid4()
    now = datetime(2026, 11, 26, 12, tzinfo=UTC)
    with session_factory() as session:
        session.add(
            UserRecord(
                id=user_id,
                external_issuer="https://idp.example.test",
                external_subject=f"media-uploader-{user_id}",
                email=f"uploader-{user_id}@example.test",
                display_name="Media Uploader",
                status=UserStatus.ACTIVE.value,
                version=1,
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
    yield user_id


@pytest.fixture
def actor_context() -> ActorContext:
    return ActorContext(
        actor_type=ActorType.SYSTEM,
        correlation_id="m2-integration",
        request_id="request-001",
    )


@pytest.fixture
def make_uow(session_factory: sessionmaker[Session], actor_context: ActorContext) -> MakeUow:
    def factory(
        *,
        actor: ActorContext | None = None,
        clock: SystemClock | None = None,
        ids: Uuid4IdGenerator | None = None,
    ) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(
            session_factory=session_factory,
            clock=clock or SystemClock(),
            id_generator=ids or Uuid4IdGenerator(),
            actor_context=actor or actor_context,
        )

    return factory


def probe_id(value: str) -> UUID:
    return UUID(value)
