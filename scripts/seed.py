from __future__ import annotations

import json
import os
import sys

from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from fps_platform.modules.identity.application.commands import SeedRolesCommand
from fps_platform.modules.identity.application.handlers import seed_roles
from fps_platform.modules.identity.domain.value_objects import RoleCode
from fps_platform.shared.domain.actor import ActorContext, ActorType
from fps_platform.shared.domain.clock import SystemClock
from fps_platform.shared.domain.identifiers import Uuid4IdGenerator
from fps_platform.shared.infrastructure.persistence.engine import (
    DatabaseRuntimeSettings,
    create_db_engine,
)
from fps_platform.shared.infrastructure.persistence.uow import SqlAlchemyUnitOfWork


def main() -> int:
    raw_url = os.getenv("DATABASE_URL") or os.getenv("FPS_DATABASE_URL")
    if not raw_url:
        print(
            json.dumps(
                {
                    "status": "not_configured",
                    "seedable_foundation_configurations": len(RoleCode),
                    "inserted": 0,
                    "duplicates_skipped": 0,
                }
            )
        )
        return 2
    url = make_url(raw_url)
    if url.password is None:
        url = url.set(password="fps")
    engine = create_db_engine(
        url.render_as_string(hide_password=False),
        DatabaseRuntimeSettings(),
    )
    session_factory = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False, class_=Session
    )
    try:
        actor = ActorContext(
            actor_type=ActorType.SYSTEM,
            correlation_id="seed-roles",
            request_id="seed-roles",
        )
        with SqlAlchemyUnitOfWork(
            session_factory=session_factory,
            clock=SystemClock(),
            id_generator=Uuid4IdGenerator(),
            actor_context=actor,
        ) as uow:
            inserted = seed_roles(uow, SeedRolesCommand())
            uow.commit()
        print(
            json.dumps(
                {
                    "status": "ok",
                    "seedable_foundation_configurations": len(RoleCode),
                    "inserted": inserted,
                    "duplicates_skipped": len(RoleCode) - inserted,
                }
            )
        )
        return 0
    except SQLAlchemyError:
        print(
            json.dumps(
                {
                    "status": "unavailable",
                    "seedable_foundation_configurations": len(RoleCode),
                    "inserted": 0,
                    "duplicates_skipped": 0,
                }
            )
        )
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
