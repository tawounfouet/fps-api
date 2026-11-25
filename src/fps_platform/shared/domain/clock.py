from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FakeClock:
    def __init__(self, value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError("FakeClock requires an aware UTC datetime")
        self._value = value.astimezone(UTC)

    def now(self) -> datetime:
        return self._value

    def advance(self, *, seconds: int = 0, minutes: int = 0) -> None:
        self._value += timedelta(seconds=seconds, minutes=minutes)
