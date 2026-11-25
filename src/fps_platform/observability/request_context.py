from __future__ import annotations

from contextvars import ContextVar, Token
from re import Pattern, compile
from uuid import uuid4

CORRELATION_ID_PATTERN: Pattern[str] = compile(r"^[A-Za-z0-9_-]{1,128}$")
_correlation_id: ContextVar[str] = ContextVar("fps_correlation_id", default="")
_request_id: ContextVar[str] = ContextVar("fps_request_id", default="")


def new_identifier() -> str:
    return str(uuid4())


def is_valid_correlation_id(value: str) -> bool:
    return bool(CORRELATION_ID_PATTERN.fullmatch(value))


def set_request_context(*, correlation_id: str, request_id: str) -> tuple[Token[str], Token[str]]:
    return (
        _correlation_id.set(correlation_id),
        _request_id.set(request_id),
    )


def reset_request_context(tokens: tuple[Token[str], Token[str]]) -> None:
    correlation_token, request_token = tokens
    _correlation_id.reset(correlation_token)
    _request_id.reset(request_token)


def get_correlation_id() -> str:
    return _correlation_id.get() or new_identifier()


def get_request_id() -> str:
    return _request_id.get() or new_identifier()
