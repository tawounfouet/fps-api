from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Request, Response

from fps_platform.api.schemas import ErrorResponse
from fps_platform.config import Settings
from fps_platform.modules.contact.api.dependencies import (
    get_contact_rate_limiter,
    get_contact_settings,
    get_public_contact_uow,
    resolve_client_ip,
)
from fps_platform.modules.contact.api.schemas import ContactSubmitRequest, ContactSubmitResponse
from fps_platform.modules.contact.application import handlers
from fps_platform.modules.contact.application.commands import SubmitContactCommand
from fps_platform.modules.contact.application.ports import ContactRateLimiter, ContactUnitOfWork
from fps_platform.modules.contact.domain.enums import ContactLocale
from fps_platform.modules.contact.domain.exceptions import (
    ContactRateLimitError,
    ContactUnsupportedMediaTypeError,
)
from fps_platform.modules.contact.domain.value_objects import (
    ContactEmailAddress,
    ContactIdempotencyKey,
    ContactMessage,
    ContactOptionalText,
    PersonName,
    PhoneNumber,
)

router = APIRouter(prefix="/api/v1", tags=["contact"])

CONTACT_RESPONSES: dict[int | str, dict[str, object]] = {
    400: {"model": ErrorResponse, "description": "The request is invalid"},
    409: {"model": ErrorResponse, "description": "The idempotency key conflicts with the payload"},
    413: {"model": ErrorResponse, "description": "The payload is too large"},
    415: {"model": ErrorResponse, "description": "application/json is required"},
    422: {"model": ErrorResponse, "description": "Validation error"},
    429: {"model": ErrorResponse, "description": "The submission was rate limited"},
    503: {"model": ErrorResponse, "description": "A required dependency is unavailable"},
}

IDEMPOTENCY_PATTERN = r"^[A-Za-z0-9_-]{16,128}$"


def _locale(request: Request, requested: ContactLocale | None) -> ContactLocale:
    if requested is not None:
        return requested
    header = request.headers.get("accept-language", "").lower()
    return ContactLocale.EN if header.startswith("en") else ContactLocale.FR


def _require_json(request: Request) -> None:
    content_type = request.headers.get("content-type", "")
    if not content_type.lower().startswith("application/json"):
        raise ContactUnsupportedMediaTypeError("application/json is required")


@router.post(
    "/contact",
    operation_id="contactSubmit",
    response_model=ContactSubmitResponse,
    status_code=201,
    responses=CONTACT_RESPONSES,
)
def submit_contact(
    request: Request,
    response: Response,
    payload: ContactSubmitRequest,
    idempotency_key: str = Header(
        alias="Idempotency-Key",
        min_length=16,
        max_length=128,
        pattern=IDEMPOTENCY_PATTERN,
    ),
    settings: Settings = Depends(get_contact_settings),
    rate_limiter: ContactRateLimiter = Depends(get_contact_rate_limiter),
    uow: ContactUnitOfWork = Depends(get_public_contact_uow),
) -> ContactSubmitResponse:
    _require_json(request)
    retry_after = rate_limiter.retry_after(
        resolve_client_ip(request, settings),
        limit=settings.contact_rate_limit_per_window,
        window_seconds=settings.contact_rate_limit_window_seconds,
    )
    if retry_after:
        raise ContactRateLimitError(retry_after)

    result = handlers.submit_contact(
        uow,
        SubmitContactCommand(
            idempotency_key=ContactIdempotencyKey(idempotency_key),
            first_name=PersonName(payload.first_name),
            last_name=PersonName(payload.last_name),
            email=ContactEmailAddress(payload.email),
            phone=PhoneNumber(payload.phone) if payload.phone is not None else None,
            organisation=ContactOptionalText(payload.organisation)
            if payload.organisation is not None
            else None,
            job_title=ContactOptionalText(payload.job_title)
            if payload.job_title is not None
            else None,
            subject=payload.subject,
            message=ContactMessage(payload.message),
            locale=_locale(request, payload.locale),
            rgpd_consent=payload.rgpd_consent,
            provider=settings.contact_email_provider,
            template_code=settings.contact_email_template_code,
            recipient_group_code=settings.contact_email_recipient_group_code,
            max_attempts=settings.contact_delivery_max_attempts,
        ),
    )
    uow.commit()
    response.headers["Cache-Control"] = "no-store"
    return ContactSubmitResponse(
        id=result.submission_id,
        workflow_status=result.workflow_status,
        delivery_status=result.delivery_status,
        replayed=result.replayed,
    )
