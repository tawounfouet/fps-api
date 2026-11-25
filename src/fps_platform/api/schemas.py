from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class LiveResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadyResponse(BaseModel):
    status: Literal["ready"] = "ready"
    database: Literal["ok"] = "ok"


class VersionResponse(BaseModel):
    service: str
    version: str
    environment: str
    release_sha: str | None = None


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(description="Stable details; empty object when none")
    correlation_id: str
