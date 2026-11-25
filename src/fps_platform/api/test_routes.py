from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(include_in_schema=False)


class JsonPayload(BaseModel):
    value: str = Field(min_length=1, max_length=32)


@router.get("/_test/validation")
def validation_probe(value: int) -> dict[str, int]:
    return {"value": value}


@router.post("/_test/json")
def json_probe(payload: JsonPayload) -> JsonPayload:
    return payload


@router.get("/_test/error")
def error_probe() -> Literal["unreachable"]:
    raise RuntimeError("probe failure")
