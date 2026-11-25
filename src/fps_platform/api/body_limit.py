from __future__ import annotations

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from fps_platform.observability.request_context import get_correlation_id


class BodySizeLimitMiddleware:
    def __init__(self, app: ASGIApp, *, path: str, max_bytes: int) -> None:
        self._app = app
        self._path = path
        self._max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") != self._path:
            await self._app(scope, receive, send)
            return
        if scope.get("method") != "POST":
            await self._app(scope, receive, send)
            return
        headers = scope.get("headers", ())
        if not self._is_json(headers):
            await self._unsupported_media_type(send)
            return
        declared = self._declared_length(headers)
        if declared is not None and declared > self._max_bytes:
            await self._too_large(send)
            return
        body = bytearray()
        while True:
            message: Message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            body.extend(chunk)
            if len(body) > self._max_bytes:
                await self._too_large(send)
                return
            if not message.get("more_body", False):
                break

        sent = False

        async def replay_receive() -> Message:
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self._app(scope, replay_receive, send)

    def _is_json(self, headers: object) -> bool:
        if not isinstance(headers, (list, tuple)):
            return False
        for raw_name, raw_value in headers:
            if isinstance(raw_name, bytes) and raw_name.lower() == b"content-type":
                value = raw_value.decode("latin-1").split(";", 1)[0].strip().lower()
                return bool(value == "application/json")
        return False

    def _declared_length(self, headers: object) -> int | None:
        if not isinstance(headers, (list, tuple)):
            return None
        for raw_name, raw_value in headers:
            if isinstance(raw_name, bytes) and raw_name.lower() == b"content-length":
                try:
                    return int(raw_value.decode("latin-1"))
                except ValueError:
                    return None
        return None

    async def _too_large(self, send: Send) -> None:
        payload = json.dumps(
            {
                "code": "PAYLOAD_TOO_LARGE",
                "message": "The contact submission payload is too large.",
                "details": {},
                "correlation_id": get_correlation_id(),
            }
        ).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"cache-control", b"no-store"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": payload})

    async def _unsupported_media_type(self, send: Send) -> None:
        payload = json.dumps(
            {
                "code": "UNSUPPORTED_MEDIA_TYPE",
                "message": "The contact submission must use application/json.",
                "details": {},
                "correlation_id": get_correlation_id(),
            }
        ).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": 415,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"cache-control", b"no-store"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": payload})
