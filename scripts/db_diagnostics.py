from __future__ import annotations

import json
import os
import sys

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from fps_platform.shared.infrastructure.persistence.engine import (
    DatabaseRuntimeSettings,
    create_db_engine,
)


def main() -> int:
    raw_url = os.getenv("DATABASE_URL") or os.getenv("FPS_DATABASE_URL")
    if not raw_url:
        print(json.dumps({"status": "not_configured"}))
        return 2
    parsed = make_url(raw_url)
    if parsed.password is None:
        parsed = parsed.set(password="fps")
    runtime = DatabaseRuntimeSettings()
    engine = create_db_engine(parsed.render_as_string(hide_password=False), runtime)
    try:
        with engine.connect() as connection:
            postgres_version = str(connection.execute(text("show server_version")).scalar_one())
            database = str(connection.execute(text("select current_database()")).scalar_one())
            schema = str(connection.execute(text("select current_schema()")).scalar_one())
            migration = connection.execute(text("select version_num from alembic_version")).scalar()
        print(
            json.dumps(
                {
                    "status": "ok",
                    "database": database,
                    "schema": schema,
                    "postgres_version": postgres_version,
                    "migration": migration,
                    "pool_size": runtime.pool_size,
                    "pool_timeout": runtime.pool_timeout,
                }
            )
        )
        return 0
    except SQLAlchemyError:
        print(json.dumps({"status": "unavailable"}))
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
