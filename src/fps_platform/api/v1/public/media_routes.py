from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from fps_platform.api.schemas import ErrorResponse
from fps_platform.modules.media.application.dto import (
    MediaStorageUnavailableError,
    PublicMediaUrlResult,
)
from fps_platform.modules.media.application.queries.resolve_public_url import (
    PublicUrlResolverPort,
    ResolvePublicMediaUrlQuery,
    resolve_public_media_url,
)
from fps_platform.observability.metrics import MetricsRegistry
from fps_platform.observability.request_context import get_correlation_id, get_request_id
from fps_platform.shared.auth.dependencies import SessionFactory, build_uow
from fps_platform.shared.domain.actor import ActorContext, ActorType

router = APIRouter(prefix="/api/v1/media", tags=["Public Media"])
CACHE_CONTROL = "public, max-age=60"
ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    404: {"model": ErrorResponse, "description": "Media asset was not found or is not ready"},
    503: {"model": ErrorResponse, "description": "Media dependency is unavailable"},
}
RESPONSES: dict[int | str, dict[str, object]] = {
    200: {
        "description": "Stable public URL for a ready media asset",
        "headers": {
            "Cache-Control": {
                "description": "Public cache policy for the stable URL",
                "schema": {"type": "string", "example": CACHE_CONTROL},
            }
        },
    },
    **ERROR_RESPONSES,
}


class PublicMediaUrlResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    media_id: UUID
    url: str = Field(max_length=2048)


@dataclass(frozen=True, slots=True)
class PublicMediaRouteServices:
    resolve: Callable[[ResolvePublicMediaUrlQuery], PublicMediaUrlResult]


def get_public_media_services(request: Request) -> PublicMediaRouteServices:
    session_factory: SessionFactory | None = getattr(request.app.state, "session_factory", None)
    resolver: PublicUrlResolverPort | None = getattr(request.app.state, "public_url_resolver", None)
    if session_factory is None or resolver is None:
        raise MediaStorageUnavailableError("media dependency is unavailable")
    metrics: MetricsRegistry | None = getattr(request.app.state, "metrics", None)

    def resolve(query: ResolvePublicMediaUrlQuery) -> PublicMediaUrlResult:
        actor = ActorContext(
            actor_type=ActorType.SERVICE,
            correlation_id=get_correlation_id(),
            request_id=get_request_id(),
        )
        with build_uow(session_factory, actor=actor) as uow:
            return resolve_public_media_url(
                query=query,
                assets=uow.media_assets,
                resolver=resolver,
                metrics=metrics,
            )

    return PublicMediaRouteServices(resolve=resolve)


@router.get(
    "/{media_id}",
    operation_id="resolvePublicMediaUrl",
    response_model=PublicMediaUrlResponse,
    responses=RESPONSES,
)
def resolve_public_media(
    media_id: UUID,
    response: Response,
    services: PublicMediaRouteServices = Depends(get_public_media_services),
) -> PublicMediaUrlResponse:
    result = services.resolve(ResolvePublicMediaUrlQuery(media_id=media_id))
    response.headers["Cache-Control"] = CACHE_CONTROL
    return PublicMediaUrlResponse(media_id=result.media_id, url=result.url)
