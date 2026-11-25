from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID, uuid4


class IdGenerator(Protocol):
    def new_id(self) -> UUID: ...


class Uuid4IdGenerator:
    def new_id(self) -> UUID:
        return uuid4()


class SequenceIdGenerator:
    def __init__(self, values: Sequence[UUID | str]) -> None:
        self._values = [UUID(str(value)) for value in values]
        self._index = 0

    def new_id(self) -> UUID:
        if self._index >= len(self._values):
            raise RuntimeError("Identifier sequence exhausted")
        value = self._values[self._index]
        self._index += 1
        return value
