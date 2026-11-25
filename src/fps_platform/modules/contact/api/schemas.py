from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from fps_platform.modules.contact.domain.enums import (
    ContactDeliveryStatus,
    ContactLocale,
    ContactSubject,
    ContactWorkflowStatus,
)

NAME_PATTERN = r"^[^\r\n\t\x00-\x1f\x7f]{1,128}$"
TEXT_PATTERN = r"^[^\r\n\t\x00-\x1f\x7f]{1,128}$"
MESSAGE_PATTERN = r"^[^\r\n\t\x00-\x1f\x7f]{1,4000}$"
EMAIL_PATTERN = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$"
PHONE_PATTERN = r"^[+0-9 ()-]{3,32}$"


class ContactSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    first_name: str = Field(
        validation_alias=AliasChoices("firstName", "first_name"),
        min_length=1,
        max_length=128,
        pattern=NAME_PATTERN,
    )
    last_name: str = Field(
        validation_alias=AliasChoices("name", "last_name", "lastName"),
        min_length=1,
        max_length=128,
        pattern=NAME_PATTERN,
    )
    email: str = Field(
        min_length=3,
        max_length=254,
        pattern=EMAIL_PATTERN,
    )
    phone: str | None = Field(
        default=None,
        max_length=32,
        pattern=PHONE_PATTERN,
    )
    organisation: str | None = Field(
        default=None, min_length=1, max_length=128, pattern=TEXT_PATTERN
    )
    job_title: str | None = Field(
        default=None,
        validation_alias=AliasChoices("fonction", "job_title", "jobTitle"),
        min_length=1,
        max_length=128,
        pattern=TEXT_PATTERN,
    )
    subject: ContactSubject
    message: str = Field(min_length=1, max_length=4000, pattern=MESSAGE_PATTERN)
    rgpd_consent: bool = Field(validation_alias=AliasChoices("rgpdConsent", "rgpd_consent"))
    locale: ContactLocale | None = None
    website: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def validate_form(self) -> ContactSubmitRequest:
        if not self.rgpd_consent:
            raise ValueError("rgpdConsent must be true")
        if self.website:
            raise ValueError("website must be empty")
        return self


class ContactSubmitResponse(BaseModel):
    id: UUID
    workflow_status: ContactWorkflowStatus
    delivery_status: ContactDeliveryStatus
    replayed: bool


class ContactStatusChangeRequest(BaseModel):
    reason_code: str | None = Field(default=None, min_length=1, max_length=64)
    expected_version: int | None = Field(default=None, ge=1)


class ContactCommandResponse(BaseModel):
    submission_id: UUID
    workflow_status: ContactWorkflowStatus
    delivery_status: ContactDeliveryStatus
    version: int


class ContactDeliveryResponse(BaseModel):
    id: UUID
    channel: str
    provider: str
    status: ContactDeliveryStatus
    attempt_number: int
    requested_at: datetime
    attempted_at: datetime | None
    completed_at: datetime | None
    provider_reference: str | None
    failure_code: str | None


class ContactSubmissionResponse(BaseModel):
    id: UUID
    workflow_status: ContactWorkflowStatus
    received_at: datetime
    updated_at: datetime
    contacted_at: datetime | None
    closed_at: datetime | None
    archived_at: datetime | None
    close_reason_code: str | None
    version: int
    delivery_status: ContactDeliveryStatus | None


class ContactSubmissionListResponse(BaseModel):
    items: list[ContactSubmissionResponse]
    total: int
    limit: int
    offset: int
