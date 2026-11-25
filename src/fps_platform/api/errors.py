from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from fps_platform.observability.request_context import get_correlation_id

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


def install_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, cast(Any, validation_handler))
    app.add_exception_handler(StarletteHTTPException, cast(Any, http_handler))
    app.add_exception_handler(Exception, cast(Any, unhandled_handler))
