from __future__ import annotations

import os

from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection, Engine

from alembic import context
from fps_platform.modules.audit.infrastructure.persistence import models as audit_models
from fps_platform.modules.outbox.infrastructure.persistence import models as outbox_models
from fps_platform.shared.infrastructure.persistence.base import Base

config = context.config
url = os.getenv("DATABASE_URL") or os.getenv("FPS_DATABASE_URL")
if url:
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
elif not config.get_main_option("sqlalchemy.url"):
    raise RuntimeError("DATABASE_URL or FPS_DATABASE_URL is required")

target_metadata = Base.metadata
_registered_models = (audit_models.AuditEventRecord, outbox_models.OutboxEventRecord)


def get_url() -> str:
    configured_url = config.get_main_option("sqlalchemy.url")
    if not configured_url:
        raise RuntimeError("DATABASE_URL or FPS_DATABASE_URL is required")
    return configured_url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def create_migration_engine() -> Engine:
    return create_engine(get_url(), poolclass=pool.NullPool)


def run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_migration_engine()
    try:
        with engine.connect() as connection:
            run_migrations(connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
