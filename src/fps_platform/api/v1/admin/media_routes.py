from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from fps_platform.api.schemas import ErrorResponse
from fps_platform.modules.identity.domain.value_objects import PermissionCode
from fps_platform.modules.media.api.schemas import (
    MediaConfirmRequest,
    MediaConfirmResponse,
    MediaListResponse,
    MediaResponse,
    UploadIntentRequestSchema,
    UploadIntentResponse,
)
from fps_platform.modules.media.application.commands.archive_media import (
    ArchiveMediaCommand,
    ArchiveMediaHandler,
)
from fps_platform.modules.media.application.commands.confirm_upload import (
    ConfirmMediaUploadCommand,
    ConfirmMediaUploadHandler,
)
from fps_platform.modules.media.application.commands.request_upload import (
    RequestMediaUploadCommand,
    RequestMediaUploadHandler,
)
from fps_platform.modules.media.application.commands.restore_media import (
    RestoreMediaCommand,
    RestoreMediaHandler,
)
from fps_platform.modules.media.application.commands.update_metadata import (
    UpdateMediaMetadataCommand,
    UpdateMetadataHandler,
)
from fps_platform.modules.media.application.dto import (
    MediaConfirmResult,
    MediaListResult,
    MediaReadModel,
    MediaUsageResult,
)
from fps_platform.modules.media.application.queries.get_media import GetMediaQuery, get_media
from fps_platform.modules.media.application.queries.get_media_usage import (
    GetMediaUsageQuery,
    get_media_usage,
)
from fps_platform.modules.media.application.queries.list_media import ListMediaQuery, list_media
from fps_platform.modules.media.application.services.promotion import (
    MediaPromotionService,
    MediaUnitOfWork,
)
from fps_platform.modules.media.application.services.usage_sources import (
    MediaUsageLookup,
    MediaUsageSource,
    MediaUsageSourceRegistry,
)
from fps_platform.modules.media.domain.enums import MediaCoverageStatus, MediaStatus
from fps_platform.modules.media.infrastructure.image_inspection import PillowImageInspector
from fps_platform.observability.request_context import get_correlation_id, get_request_id
from fps_platform.shared.auth.dependencies import (
    SessionFactory,
    build_uow,
    get_current_principal,
    get_session_factory,
    get_uow_for_principal,
    require_permission,
)
from fps_platform.shared.auth.principal import CurrentPrincipal
from fps_platform.shared.domain.identifiers import Uuid4IdGenerator

router = APIRouter(prefix="/api/v1/admin/media", tags=["Admin Media"])

ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Authentication is required"},
    403: {"model": ErrorResponse, "description": "Permission is denied"},
    404: {"model": ErrorResponse, "description": "Media asset was not found"},
    409: {"model": ErrorResponse, "description": "Command conflicts with current state"},
    413: {"model": ErrorResponse, "description": "Media payload is too large"},
    415: {"model": ErrorResponse, "description": "Media type is not supported"},
    422: {"model": ErrorResponse, "description": "Validation error"},
    503: {"model": ErrorResponse, "description": "Media dependency is unavailable"},
}


class UpdateMediaMetadataRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)
    title: str | None = Field(default=None, max_length=512)
    alt_texts: dict[str, str] | None = None
    captions: dict[str, str] | None = None
    attribution: dict[str, str] | None = None


class MediaLifecycleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int | None = Field(default=None, ge=1)


class MediaUsageSourceResponse(BaseModel):
    source: str
    coverage_status: MediaCoverageStatus
    found: bool
    reference_count: int


class MediaUsageResponse(BaseModel):
    media_id: UUID
    coverage_status: MediaCoverageStatus
    found: bool
    sources: list[MediaUsageSourceResponse]


@dataclass(frozen=True, slots=True)
class MediaRouteServices:
    principal: CurrentPrincipal
    request_upload: RequestMediaUploadHandler
    confirm_upload: ConfirmMediaUploadHandler
    list_media: Callable[[ListMediaQuery], MediaListResult]
    get_media: Callable[[GetMediaQuery], MediaReadModel]
    update_metadata: UpdateMetadataHandler | None = None
    archive_media: ArchiveMediaHandler | None = None
    restore_media: RestoreMediaHandler | None = None
    usage_lookup: MediaUsageLookup | None = None


def get_media_route_services(
    request: Request,
    principal: CurrentPrincipal = Depends(get_current_principal),
    uow: MediaUnitOfWork = Depends(get_uow_for_principal),
    session_factory: SessionFactory = Depends(get_session_factory),
) -> MediaRouteServices:
    settings = request.app.state.settings
    clock = request.app.state.clock
    storage = request.app.state.media_storage_port
    idempotency = request.app.state.media_intent_idempotency

    def uow_factory() -> MediaUnitOfWork:
        return build_uow(
            session_factory,
            actor=principal.actor_context(
                correlation_id=get_correlation_id(),
                request_id=get_request_id(),
            ),
        )

    promotion = MediaPromotionService(
        storage=storage,
        inspector=PillowImageInspector(clock),
        uow_factory=uow_factory,
        clock=clock,
        id_generator=Uuid4IdGenerator(),
        max_bytes=settings.media_max_bytes,
    )
    registry = MediaUsageSourceRegistry()
    registered = cast(
        Sequence[MediaUsageSource], getattr(request.app.state, "media_usage_sources", ())
    )
    for source in registered:
        registry.register(source)
    return MediaRouteServices(
        principal=principal,
        request_upload=RequestMediaUploadHandler(
            uow=uow,
            storage=storage,
            clock=clock,
            id_generator=Uuid4IdGenerator(),
            idempotency=idempotency,
            max_bytes=settings.media_max_bytes,
            ttl_seconds=settings.media_signed_url_ttl_seconds,
        ),
        confirm_upload=ConfirmMediaUploadHandler(
            uow=uow,
            promotion=promotion,
            clock=clock,
            principal=principal,
        ),
        list_media=lambda query: list_media(uow=uow.media_assets, principal=principal, query=query),
        get_media=lambda query: get_media(uow=uow.media_assets, principal=principal, query=query),
        update_metadata=UpdateMetadataHandler(uow=uow, clock=clock, principal=principal),
        archive_media=ArchiveMediaHandler(uow=uow, clock=clock, principal=principal),
        restore_media=RestoreMediaHandler(
            uow=uow,
            storage=storage,
            clock=clock,
            principal=principal,
            max_bytes=settings.media_max_bytes,
        ),
        usage_lookup=MediaUsageLookup(assets=uow.media_assets, registry=registry),
    )


def _media_response(model: MediaReadModel) -> MediaResponse:
    return MediaResponse(
        id=model.id,
        status=model.status,
        version=model.version,
        original_filename=model.original_filename,
        mime_type=model.mime_type,
        byte_size=model.byte_size,
        width=model.width,
        height=model.height,
        checksum_sha256=model.checksum_sha256,
        failure_code=model.failure_code,
        created_at=model.created_at,
        updated_at=model.updated_at,
        ready_at=model.ready_at,
    )


def _confirm_response(result: MediaConfirmResult) -> MediaConfirmResponse:
    return MediaConfirmResponse(
        media_asset_id=result.media_asset_id,
        status=result.status,
        version=result.version,
        checksum_sha256=result.checksum_sha256,
        failure_code=result.failure_code,
    )


def _usage_response(result: MediaUsageResult) -> MediaUsageResponse:
    return MediaUsageResponse(
        media_id=result.media_id,
        coverage_status=result.coverage_status,
        found=result.found,
        sources=[
            MediaUsageSourceResponse(
                source=item.source,
                coverage_status=item.coverage_status,
                found=item.found,
                reference_count=item.reference_count,
            )
            for item in result.sources
        ],
    )


def _update_handler(services: MediaRouteServices) -> UpdateMetadataHandler:
    if services.update_metadata is None:
        raise RuntimeError("media metadata service is not configured")
    return services.update_metadata


def _archive_handler(services: MediaRouteServices) -> ArchiveMediaHandler:
    if services.archive_media is None:
        raise RuntimeError("media archive service is not configured")
    return services.archive_media


def _restore_handler(services: MediaRouteServices) -> RestoreMediaHandler:
    if services.restore_media is None:
        raise RuntimeError("media restore service is not configured")
    return services.restore_media


def _usage_lookup(services: MediaRouteServices) -> MediaUsageLookup:
    if services.usage_lookup is None:
        raise RuntimeError("media usage service is not configured")
    return services.usage_lookup


@router.post(
    "/upload-intents",
    status_code=201,
    operation_id="createMediaUploadIntent",
    response_model=UploadIntentResponse,
    responses=ERROR_RESPONSES,
)
def create_upload_intent(
    payload: UploadIntentRequestSchema,
    _: object = Depends(require_permission(PermissionCode.MANAGE_MEDIA)),
    services: MediaRouteServices = Depends(get_media_route_services),
) -> UploadIntentResponse:
    result = services.request_upload.handle(
        RequestMediaUploadCommand(
            filename_safe=payload.filename_safe,
            declared_mime=payload.declared_mime,
            declared_size_bytes=payload.declared_size_bytes,
        ),
        principal=services.principal,
    )
    return UploadIntentResponse(
        media_asset_id=result.media_asset_id,
        intent_id=result.intent_id,
        method=result.method,
        upload_url=result.upload_url,
        required_headers=result.required_headers,
        expires_at=result.expires_at,
        version=result.version,
    )


@router.post(
    "/{media_id}/confirm",
    operation_id="confirmMediaUpload",
    response_model=MediaConfirmResponse,
    responses=ERROR_RESPONSES,
)
def confirm_upload(
    media_id: UUID,
    payload: MediaConfirmRequest,
    _: object = Depends(require_permission(PermissionCode.MANAGE_MEDIA)),
    services: MediaRouteServices = Depends(get_media_route_services),
) -> MediaConfirmResponse:
    result = services.confirm_upload.handle(
        ConfirmMediaUploadCommand(media_id=media_id, expected_version=payload.expected_version)
    )
    return _confirm_response(result)


@router.get(
    "",
    operation_id="adminListMedia",
    response_model=MediaListResponse,
    responses=ERROR_RESPONSES,
)
def list_admin_media(
    response: Response,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: MediaStatus | None = Query(default=None, alias="status"),
    _: object = Depends(require_permission(PermissionCode.VIEW_MEDIA)),
    services: MediaRouteServices = Depends(get_media_route_services),
) -> MediaListResponse:
    result = services.list_media(ListMediaQuery(limit=limit, offset=offset, status=status))
    response.headers["Cache-Control"] = "no-store"
    return MediaListResponse(
        items=[_media_response(item) for item in result.items],
        total=result.total,
        limit=result.limit,
        offset=result.offset,
    )


@router.get(
    "/{media_id}",
    operation_id="adminGetMedia",
    response_model=MediaResponse,
    responses=ERROR_RESPONSES,
)
def get_admin_media(
    media_id: UUID,
    _: object = Depends(require_permission(PermissionCode.VIEW_MEDIA)),
    services: MediaRouteServices = Depends(get_media_route_services),
) -> MediaResponse:
    return _media_response(services.get_media(GetMediaQuery(media_id=media_id)))


@router.patch(
    "/{media_id}",
    operation_id="adminUpdateMediaMetadata",
    response_model=MediaResponse,
    responses=ERROR_RESPONSES,
)
def update_admin_media(
    media_id: UUID,
    payload: UpdateMediaMetadataRequest,
    _: object = Depends(require_permission(PermissionCode.MANAGE_MEDIA)),
    services: MediaRouteServices = Depends(get_media_route_services),
) -> MediaResponse:
    updated = _update_handler(services).handle(
        UpdateMediaMetadataCommand(
            media_id=media_id,
            expected_version=payload.expected_version,
            title=payload.title,
            alt_texts=payload.alt_texts,
            captions=payload.captions,
            attribution=payload.attribution,
        )
    )
    return _media_response(updated)


@router.post(
    "/{media_id}/archive",
    operation_id="adminArchiveMedia",
    response_model=MediaResponse,
    responses=ERROR_RESPONSES,
)
def archive_admin_media(
    media_id: UUID,
    payload: MediaLifecycleRequest | None = None,
    _: object = Depends(require_permission(PermissionCode.MANAGE_MEDIA)),
    services: MediaRouteServices = Depends(get_media_route_services),
) -> MediaResponse:
    expected_version = payload.expected_version if payload is not None else None
    archived = _archive_handler(services).handle(
        ArchiveMediaCommand(media_id=media_id, expected_version=expected_version)
    )
    return _media_response(archived)


@router.post(
    "/{media_id}/restore",
    operation_id="adminRestoreMedia",
    response_model=MediaResponse,
    responses=ERROR_RESPONSES,
)
def restore_admin_media(
    media_id: UUID,
    payload: MediaLifecycleRequest | None = None,
    _: object = Depends(require_permission(PermissionCode.MANAGE_MEDIA)),
    services: MediaRouteServices = Depends(get_media_route_services),
) -> MediaResponse:
    expected_version = payload.expected_version if payload is not None else None
    restored = _restore_handler(services).handle(
        RestoreMediaCommand(media_id=media_id, expected_version=expected_version)
    )
    return _media_response(restored)


@router.get(
    "/{media_id}/usage",
    operation_id="adminGetMediaUsage",
    response_model=MediaUsageResponse,
    responses=ERROR_RESPONSES,
)
def get_admin_media_usage(
    media_id: UUID,
    _: object = Depends(require_permission(PermissionCode.VIEW_MEDIA)),
    services: MediaRouteServices = Depends(get_media_route_services),
) -> MediaUsageResponse:
    result = get_media_usage(
        lookup=_usage_lookup(services),
        principal=services.principal,
        query=GetMediaUsageQuery(media_id=media_id),
    )
    return _usage_response(result)
