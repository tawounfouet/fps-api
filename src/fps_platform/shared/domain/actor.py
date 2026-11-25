from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from re import Pattern, compile
from uuid import UUID

CORRELATION_ID_PATTERN: Pattern[str] = compile(r"^[A-Za-z0-9_-]{1,128}$")
REQUEST_ID_PATTERN: Pattern[str] = compile(r"^[A-Za-z0-9_-]{1,128}$")


class ActorType(StrEnum):
    SYSTEM = "SYSTEM"
    USER = "USER"
    SERVICE = "SERVICE"
    AGENT = "AGENT"
    INTEGRATION = "INTEGRATION"


@dataclass(frozen=True, slots=True)
class ActorContext:
    actor_type: ActorType
    correlation_id: str
    actor_id: UUID | None = None
    request_id: str | None = None

    def __post_init__(self) -> None:
        if not CORRELATION_ID_PATTERN.fullmatch(self.correlation_id):
            raise ValueError("correlation_id must contain 1 to 128 safe characters")
        if self.request_id is not None and not REQUEST_ID_PATTERN.fullmatch(self.request_id):
            raise ValueError("request_id must contain 1 to 128 safe characters")
        if self.actor_type is ActorType.SYSTEM and self.actor_id is not None:
            raise ValueError("SYSTEM actors must not carry actor_id")
