from __future__ import annotations

import json
from dataclasses import asdict
from typing import cast
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from fps_platform.bootstrap import build_db_engine, build_email_port
from fps_platform.config import Settings
from fps_platform.modules.contact.application.ports import ContactUnitOfWork
from fps_platform.shared.domain.actor import ActorContext, ActorType
from fps_platform.shared.domain.clock import SystemClock
from fps_platform.shared.domain.identifiers import Uuid4IdGenerator
from fps_platform.shared.infrastructure.persistence.uow import SqlAlchemyUnitOfWork
from fps_platform.workers.contact_delivery import build_contact_delivery_worker


def main() -> None:
    settings = Settings()
    if settings.database_url is None:
        raise SystemExit("FPS_DATABASE_URL is required")
    engine = build_db_engine(settings.database_url.get_secret_value(), settings)
    session_factory = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False, class_=Session
    )
    clock = SystemClock()
    worker_id = f"contact-delivery-worker-{uuid4().hex[:8]}"
    actor = ActorContext(
        actor_type=ActorType.SYSTEM,
        correlation_id=worker_id,
        request_id=None,
    )

    def uow_factory() -> ContactUnitOfWork:
        return cast(
            ContactUnitOfWork,
            SqlAlchemyUnitOfWork(
                session_factory=session_factory,
                clock=clock,
                id_generator=Uuid4IdGenerator(),
                actor_context=actor,
            ),
        )

    email_port = build_email_port(settings)
    worker = build_contact_delivery_worker(
        uow_factory=uow_factory,
        email_port=email_port,
        clock=clock,
        provider=settings.contact_email_provider,
        retry_delays_seconds=settings.contact_delivery_retry_delays_seconds,
        lease_seconds=settings.contact_worker_lease_seconds,
        worker_id=worker_id,
    )
    try:
        stats = worker.run_once(limit=settings.contact_worker_batch_size)
        print(json.dumps(asdict(stats), sort_keys=True))
    finally:
        close = getattr(email_port, "close", None)
        if callable(close):
            close()
        engine.dispose()


if __name__ == "__main__":
    main()
