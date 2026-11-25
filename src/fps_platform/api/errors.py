from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from fps_platform.modules.contact.domain.exceptions import (
    ContactDeliveryError,
    ContactNotFoundError,
    ContactPayloadTooLargeError,
    ContactRateLimitError,
    ContactUnsupportedMediaTypeError,
    IdempotencyConflictError,
    InvalidContactDataError,
    InvalidContactTransitionError,
    PermanentContactDeliveryError,
    RetryableContactDeliveryError,
)
from fps_platform.modules.identity.domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    DuplicateExternalIdentityError,
    IdentityError,
    InvalidUserTransitionError,
    LastSuperAdminViolationError,
    RoleNotFoundError,
    SuperAdminExistsError,
    TokenValidationError,
    UserNotFoundError,
)
from fps_platform.observability.request_context import get_correlation_id
from fps_platform.shared.domain.errors import ConflictError

logger = logging.getLogger("fps_platform.errors")

STATUS_CODES = {
    400: "INVALID_REQUEST",
    401: "AUTHENTICATION_REQUIRED",
    403: "PERMISSION_DENIED",
    404: "RESOURCE_NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONCURRENT_MODIFICATION",
    413: "PAYLOAD_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
    503: "DEPENDENCY_UNAVAILABLE",
}

STATUS_MESSAGES = {
    400: "The request could not be interpreted.",
    401: "Authentication is required.",
    403: "Access is denied.",
    404: "The requested resource was not found.",
    405: "The method is not allowed.",
    409: "The request conflicts with the current state.",
    413: "The request payload is too large.",
    415: "The media type is not supported.",
    422: "The request is invalid.",
    429: "The request was rate limited.",
    500: "An unexpected error occurred.",
    503: "A required dependency is unavailable.",
}


def error_payload(
    *, code: str, message: str, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "details": details or {},
        "correlation_id": get_correlation_id(),
    }


def safe_error_code(error: dict[str, Any]) -> str:
    raw = str(error.get("type", "INVALID"))
    if raw.startswith("value_error."):
        return "INVALID_VALUE"
    if "type" in raw:
        return "INVALID_TYPE"
    if raw.isascii() and raw.isupper() and len(raw) <= 64:
        return raw
    return "INVALID"


def validation_details(errors: Sequence[Any]) -> dict[str, Any]:
    details: dict[str, list[str]] = {}
    reserved = {"body", "query", "path", "header", "cookie"}
    for error in errors:
        location = [str(part) for part in error.get("loc", ()) if str(part) not in reserved]
        field = ".".join(location) or "request"
        details.setdefault(field, []).append(safe_error_code(error))
    return {"fields": details}


async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    malformed = any(error.get("type") == "json_invalid" for error in errors)
    status_code = 400 if malformed else 422
    code = "MALFORMED_JSON" if malformed else "VALIDATION_ERROR"
    message = "The JSON body is malformed." if malformed else "The request is invalid."
    details = {} if malformed else validation_details(errors)
    return JSONResponse(
        status_code=status_code,
        content=error_payload(code=code, message=message, details=details),
    )


async def http_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    status_code = exc.status_code
    code = STATUS_CODES.get(status_code, "HTTP_ERROR")
    message = STATUS_MESSAGES.get(status_code, "The request could not be completed.")
    return JSONResponse(
        status_code=status_code,
        content=error_payload(code=code, message=message),
        headers=getattr(exc, "headers", None),
    )


async def unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled_exception",
        extra={"exception_type": type(exc).__name__},
    )
    return JSONResponse(
        status_code=500,
        content=error_payload(
            code="INTERNAL_ERROR",
            message=STATUS_MESSAGES[500],
        ),
    )


AUTH_CODES = frozenset(
    {
        "AUTHENTICATION_REQUIRED",
        "INVALID_TOKEN",
        "USER_NOT_PROVISIONED",
        "USER_SUSPENDED",
        "USER_DISABLED",
        "PERMISSION_DENIED",
    }
)

IDENTITY_ERROR_RESPONSES: dict[type[Exception], tuple[int, str, str]] = {
    UserNotFoundError: (404, "USER_NOT_FOUND", "The requested user was not found."),
    RoleNotFoundError: (404, "ROLE_NOT_FOUND", "The requested role was not found."),
    LastSuperAdminViolationError: (
        409,
        "LAST_SUPER_ADMIN_VIOLATION",
        "The last active SUPER_ADMIN cannot be removed.",
    ),
    SuperAdminExistsError: (409, "SUPER_ADMIN_EXISTS", "An active SUPER_ADMIN already exists."),
    DuplicateExternalIdentityError: (
        409,
        "IDENTITY_CONFLICT",
        "The external identity is already linked to a user.",
    ),
    InvalidUserTransitionError: (
        409,
        "INVALID_USER_TRANSITION",
        "The requested user transition is not allowed.",
    ),
    ConflictError: (409, "CONCURRENT_MODIFICATION", "The request conflicts with current state."),
    TokenValidationError: (401, "INVALID_TOKEN", "Authentication is required."),
}

CONTACT_ERROR_RESPONSES: dict[type[Exception], tuple[int, str, str]] = {
    InvalidContactDataError: (
        400,
        "INVALID_CONTACT_DATA",
        "The contact request contains invalid data.",
    ),
    ContactNotFoundError: (404, "CONTACT_NOT_FOUND", "The contact submission was not found."),
    IdempotencyConflictError: (
        409,
        "IDEMPOTENCY_KEY_CONFLICT",
        "The idempotency key was reused with a different payload.",
    ),
    InvalidContactTransitionError: (
        409,
        "INVALID_CONTACT_TRANSITION",
        "The requested contact transition is not allowed.",
    ),
    ContactPayloadTooLargeError: (
        413,
        "PAYLOAD_TOO_LARGE",
        "The contact submission payload is too large.",
    ),
    ContactUnsupportedMediaTypeError: (
        415,
        "UNSUPPORTED_MEDIA_TYPE",
        "The contact submission requires application/json.",
    ),
    ContactRateLimitError: (
        429,
        "RATE_LIMITED",
        "Too many contact submissions were attempted.",
    ),
    ContactDeliveryError: (
        503,
        "CONTACT_DELIVERY_FAILED",
        "The contact delivery could not be completed.",
    ),
    RetryableContactDeliveryError: (
        503,
        "CONTACT_DELIVERY_RETRYABLE",
        "The contact delivery will be retried.",
    ),
    PermanentContactDeliveryError: (
        503,
        "CONTACT_DELIVERY_PERMANENT",
        "The contact delivery failed permanently.",
    ),
}


async def authentication_handler(_: Request, exc: AuthenticationError) -> JSONResponse:
    code = exc.code if exc.code in AUTH_CODES else "AUTHENTICATION_REQUIRED"
    logger.warning("authentication_failed", extra={"code": code})
    return JSONResponse(
        status_code=401,
        content=error_payload(code=code, message=STATUS_MESSAGES[401]),
        headers={"Cache-Control": "no-store"},
    )


async def authorization_handler(_: Request, exc: AuthorizationError) -> JSONResponse:
    code = exc.code if exc.code in AUTH_CODES else "PERMISSION_DENIED"
    logger.warning("authorization_failed", extra={"code": code})
    return JSONResponse(
        status_code=403,
        content=error_payload(code=code, message=STATUS_MESSAGES[403]),
        headers={"Cache-Control": "no-store"},
    )


async def identity_handler(_: Request, exc: Exception) -> JSONResponse:
    status_code, code, message = IDENTITY_ERROR_RESPONSES[type(exc)]
    logger.warning("identity_request_failed", extra={"code": code})
    return JSONResponse(
        status_code=status_code,
        content=error_payload(code=code, message=message),
        headers={"Cache-Control": "no-store"},
    )


async def identity_fallback_handler(_: Request, exc: IdentityError) -> JSONResponse:
    logger.warning("identity_request_failed", extra={"code": "INVALID_REQUEST"})
    return JSONResponse(
        status_code=400,
        content=error_payload(code="INVALID_REQUEST", message=STATUS_MESSAGES[400]),
        headers={"Cache-Control": "no-store"},
    )


async def contact_handler(_: Request, exc: Exception) -> JSONResponse:
    status_code, code, message = CONTACT_ERROR_RESPONSES[type(exc)]
    headers = {"Cache-Control": "no-store"}
    if isinstance(exc, ContactRateLimitError):
        headers["Retry-After"] = str(exc.retry_after)
    logger.warning("contact_request_failed", extra={"code": code, "status_code": status_code})
    return JSONResponse(
        status_code=status_code,
        content=error_payload(code=code, message=message),
        headers=headers,
    )


def install_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AuthenticationError, cast(Any, authentication_handler))
    app.add_exception_handler(AuthorizationError, cast(Any, authorization_handler))
    for error_type in IDENTITY_ERROR_RESPONSES:
        app.add_exception_handler(error_type, cast(Any, identity_handler))
    app.add_exception_handler(IdentityError, cast(Any, identity_fallback_handler))
    for error_type in CONTACT_ERROR_RESPONSES:
        app.add_exception_handler(error_type, cast(Any, contact_handler))
    app.add_exception_handler(RequestValidationError, cast(Any, validation_handler))
    app.add_exception_handler(StarletteHTTPException, cast(Any, http_handler))
    app.add_exception_handler(Exception, cast(Any, unhandled_handler))
