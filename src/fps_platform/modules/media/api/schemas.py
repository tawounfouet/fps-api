from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from fps_platform.modules.media.domain.enums import MediaStatus


class UploadIntentRequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename_safe: str = Field(min_length=1, max_length=255)
    declared_mime: str = Field(min_length=1, max_length=64)
    declared_size_bytes: int = Field(ge=1)


class UploadIntentResponse(BaseModel):
    media_asset_id: UUID
    intent_id: UUID
    method: Literal["PUT"]
    upload_url: str
    required_headers: dict[str, str]
    expires_at: datetime
    version: int


class MediaConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_version: int = Field(ge=1)


class MediaConfirmResponse(BaseModel):
    media_asset_id: UUID
    status: MediaStatus
    version: int
    checksum_sha256: str | None = None
    failure_code: str | None = None


class MediaResponse(BaseModel):
    id: UUID
    status: MediaStatus
    version: int
    original_filename: str
    mime_type: str
    byte_size: int
    width: int | None = None
    height: int | None = None
    checksum_sha256: str | None = None
    failure_code: str | None = None
    created_at: datetime
    updated_at: datetime
    ready_at: datetime | None = None


class MediaListResponse(BaseModel):
    items: list[MediaResponse]
    total: int
    limit: int
    offset: int
