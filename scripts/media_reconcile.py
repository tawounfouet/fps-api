from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from collections.abc import Sequence

from sqlalchemy.orm import Session, sessionmaker

from fps_platform.bootstrap import build_db_engine, build_media_storage_port
from fps_platform.config import Settings
from fps_platform.modules.media.application.services.reconciliation import (
    FakeStorageObjectCatalog,
    ReconciliationService,
    report_to_mapping,
)
from fps_platform.modules.media.domain.enums import MediaStorageMode
from fps_platform.shared.domain.actor import ActorContext, ActorType
from fps_platform.shared.domain.clock import SystemClock
from fps_platform.shared.domain.identifiers import Uuid4IdGenerator
from fps_platform.shared.infrastructure.persistence.uow import SqlAlchemyUnitOfWork


def main(argv: Sequence[str] | None = None) -> int:
    parser = ArgumentParser(description="Read-only media storage reconciliation")
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args(argv)
    settings = Settings(_env_file=None)
    database_url = args.database_url or (
        settings.database_url.get_secret_value() if settings.database_url is not None else None
    )
    if database_url is None:
        print("reconciliation_not_executed: database URL is missing")
        return 2
    if settings.media_storage_mode is not MediaStorageMode.FAKE:
        print("reconciliation_not_executed: object catalog is unavailable without provider access")
        return 2

    clock = SystemClock()
    storage = build_media_storage_port(settings, clock)
    engine = build_db_engine(database_url, settings)
    session_factory = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False, class_=Session
    )
    try:
        actor = ActorContext(actor_type=ActorType.SYSTEM, correlation_id="media-reconcile")
        with SqlAlchemyUnitOfWork(
            session_factory=session_factory,
            clock=clock,
            id_generator=Uuid4IdGenerator(),
            actor_context=actor,
        ) as uow:
            service = ReconciliationService(
                assets=uow.media_assets,
                storage=storage,
                catalog=FakeStorageObjectCatalog(storage),
                clock=clock,
            )
            report = service.run()
        print(json.dumps(report_to_mapping(report), sort_keys=True, ensure_ascii=False))
        close = getattr(storage, "close", None)
        if callable(close):
            close()
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
