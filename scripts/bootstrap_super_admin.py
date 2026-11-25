from __future__ import annotations

import argparse
import json
import os
import sys

from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from fps_platform.modules.identity.application.commands import (
    BootstrapSuperAdminCommand,
    SeedRolesCommand,
)
from fps_platform.modules.identity.application.handlers import bootstrap_super_admin, seed_roles
from fps_platform.modules.identity.domain.exceptions import (
    DuplicateExternalIdentityError,
    IdentityError,
    InvalidUserTransitionError,
    LastSuperAdminViolationError,
    SuperAdminExistsError,
)
from fps_platform.shared.domain.actor import ActorContext, ActorType
from fps_platform.shared.domain.clock import SystemClock
from fps_platform.shared.domain.identifiers import Uuid4IdGenerator
from fps_platform.shared.infrastructure.persistence.engine import (
    DatabaseRuntimeSettings,
    create_db_engine,
)
from fps_platform.shared.infrastructure.persistence.uow import SqlAlchemyUnitOfWork

ERROR_CODES: dict[type[Exception], str] = {
    SuperAdminExistsError: "SUPER_ADMIN_EXISTS",
    LastSuperAdminViolationError: "LAST_SUPER_ADMIN_VIOLATION",
    InvalidUserTransitionError: "INVALID_USER_TRANSITION",
    DuplicateExternalIdentityError: "IDENTITY_CONFLICT",
}


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap the initial SUPER_ADMIN user")
    parser.add_argument("--issuer", required=True)
    parser.add_argument("--subject", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    raw_url = os.getenv("DATABASE_URL") or os.getenv("FPS_DATABASE_URL")
    if not raw_url:
        print(json.dumps({"status": "not_configured", "code": "DATABASE_NOT_CONFIGURED"}))
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
            correlation_id="bootstrap-super-admin",
            request_id="bootstrap-super-admin",
        )
        with SqlAlchemyUnitOfWork(
            session_factory=session_factory,
            clock=SystemClock(),
            id_generator=Uuid4IdGenerator(),
            actor_context=actor,
        ) as uow:
            seed_roles(uow, SeedRolesCommand())
            result = bootstrap_super_admin(
                uow,
                BootstrapSuperAdminCommand(
                    issuer=args.issuer,
                    subject=args.subject,
                    email=args.email,
                    display_name=args.display_name,
                ),
            )
            uow.commit()
        print(
            json.dumps(
                {
                    "status": "ok",
                    "created": result.created,
                    "changed": result.changed,
                    "version": result.version,
                }
            )
        )
        return 0
    except IdentityError as exc:
        code = ERROR_CODES.get(type(exc), "IDENTITY_REQUEST_FAILED")
        print(json.dumps({"status": "error", "code": code}))
        return 3
    except ValueError:
        print(json.dumps({"status": "error", "code": "INVALID_REQUEST"}))
        return 2
    except SQLAlchemyError:
        print(json.dumps({"status": "unavailable", "code": "DATABASE_UNAVAILABLE"}))
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
