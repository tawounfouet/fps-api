from __future__ import annotations

import time
from typing import Any

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from fps_platform.config import Settings
from fps_platform.observability.logging import log_request
from fps_platform.observability.request_context import (
    is_valid_correlation_id,
    new_identifier,
    reset_request_context,
    set_request_context,
)


class CorrelationIdMiddleware:
    def __init__(self, app: ASGIApp, *, settings: Settings) -> None:
        self.app = app
        self.settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        incoming = headers.get("x-correlation-id")
        correlation_id = (
            incoming if incoming and is_valid_correlation_id(incoming) else new_identifier()
        )
        request_id = new_identifier()
        tokens = set_request_context(correlation_id=correlation_id, request_id=request_id)
        started_at = time.perf_counter()
        status_code = 500

        async def send_with_trace_headers(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                response_headers = MutableHeaders(scope=message)
                response_headers["X-Correlation-ID"] = correlation_id
                response_headers["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_trace_headers)
        finally:
            route = scope.get("route")
            route_path: Any = getattr(route, "path", None)
            log_request(
                settings=self.settings,
                request_id=request_id,
                correlation_id=correlation_id,
                method=str(scope.get("method", "UNKNOWN")),
                route=str(route_path or scope.get("path", "unknown")),
                status_code=status_code,
                duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
            )
            reset_request_context(tokens)
