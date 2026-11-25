from __future__ import annotations

import logging
from typing import cast

from fastapi import APIRouter, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from fps_platform.api.schemas import ErrorResponse, LiveResponse, ReadyResponse, VersionResponse
from fps_platform.config import Settings

logger = logging.getLogger("fps_platform.health")

router = APIRouter(tags=["system"])


@router.get("/health/live", response_model=LiveResponse, summary="Liveness probe")
def liveness() -> LiveResponse:
    return LiveResponse()


@router.get(
    "/health/ready",
    response_model=ReadyResponse,
    summary="Readiness probe",
    responses={
        503: {
            "description": "A required dependency is unavailable",
            "model": ErrorResponse,
        }
    },
)
def readiness(request: Request) -> ReadyResponse:
    engine = getattr(request.app.state, "db_engine", None)
    if engine is None:
        raise StarletteHTTPException(status_code=503, detail="Dependency unavailable")
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.warning(
            "readiness_dependency_failed",
            extra={"dependency": "database", "exception_type": type(exc).__name__},
        )
        raise StarletteHTTPException(status_code=503, detail="Dependency unavailable") from None
    return ReadyResponse()


@router.get("/version", response_model=VersionResponse, summary="Build metadata")
def version(request: Request) -> VersionResponse:
    settings = cast(Settings, request.app.state.settings)
    return VersionResponse(
        service=settings.service_name,
        version=settings.api_version,
        environment=settings.environment.value,
        release_sha=settings.release_sha,
    )
