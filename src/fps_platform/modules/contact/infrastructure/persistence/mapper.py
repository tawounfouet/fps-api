from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fps_platform.modules.contact.domain.entities import ContactDelivery, ContactSubmission
from fps_platform.modules.contact.domain.enums import (
    ContactDeliveryChannel,
    ContactDeliveryStatus,
    ContactSource,
    ContactWorkflowStatus,
)
from fps_platform.modules.contact.domain.value_objects import (
    ContactCloseReason,
    ContactEmailAddress,
    ContactMessage,
    ContactOptionalText,
    PersonName,
    PhoneNumber,
    normalize_locale,
    normalize_subject,
)
from fps_platform.modules.contact.infrastructure.persistence.models import (
    ContactDeliveryRecord,
    ContactIdempotencyKeyRecord,
    ContactSubmissionRecord,
)


def to_submission_record(submission: ContactSubmission) -> ContactSubmissionRecord:
    return ContactSubmissionRecord(
        id=submission.id,
        first_name=str(submission.first_name),
        last_name=str(submission.last_name),
        email=str(submission.email),
        phone=str(submission.phone) if submission.phone is not None else None,
        organisation=str(submission.organisation) if submission.organisation is not None else None,
        job_title=str(submission.job_title) if submission.job_title is not None else None,
        subject=submission.subject.value,
        message=str(submission.message),
        locale=submission.locale.value,
        source=submission.source.value,
        workflow_status=submission.workflow_status.value,
        rgpd_consent=submission.rgpd_consent,
        received_at=submission.received_at,
        updated_at=submission.updated_at,
        contacted_at=submission.contacted_at,
        closed_at=submission.closed_at,
        archived_at=submission.archived_at,
        close_reason_code=submission.close_reason.value if submission.close_reason else None,
        version=submission.version,
    )


def to_submission(record: ContactSubmissionRecord) -> ContactSubmission:
    return ContactSubmission(
        id=record.id,
        first_name=PersonName(record.first_name),
        last_name=PersonName(record.last_name),
        email=ContactEmailAddress(record.email),
        phone=PhoneNumber(record.phone) if record.phone is not None else None,
        organisation=ContactOptionalText(record.organisation)
        if record.organisation is not None
        else None,
        job_title=ContactOptionalText(record.job_title) if record.job_title is not None else None,
        subject=normalize_subject(record.subject),
        message=ContactMessage(record.message),
        locale=normalize_locale(record.locale),
        source=ContactSource(record.source),
        workflow_status=ContactWorkflowStatus(record.workflow_status),
        rgpd_consent=bool(record.rgpd_consent),
        received_at=record.received_at,
        updated_at=record.updated_at,
        contacted_at=record.contacted_at,
        closed_at=record.closed_at,
        archived_at=record.archived_at,
        close_reason=ContactCloseReason(record.close_reason_code)
        if record.close_reason_code is not None
        else None,
        version=record.version,
    )


def to_delivery_record(delivery: ContactDelivery) -> ContactDeliveryRecord:
    return ContactDeliveryRecord(
        id=delivery.id,
        submission_id=delivery.submission_id,
        channel=delivery.channel.value,
        provider=delivery.provider,
        status=delivery.status.value,
        attempt_number=delivery.attempt_number,
        requested_at=delivery.requested_at,
        attempted_at=delivery.attempted_at,
        completed_at=delivery.completed_at,
        provider_reference=delivery.provider_reference,
        failure_code=delivery.failure_code,
    )


def to_delivery(record: ContactDeliveryRecord) -> ContactDelivery:
    return ContactDelivery(
        id=record.id,
        submission_id=record.submission_id,
        channel=ContactDeliveryChannel(record.channel),
        provider=record.provider,
        status=ContactDeliveryStatus(record.status),
        attempt_number=record.attempt_number,
        requested_at=record.requested_at,
        attempted_at=record.attempted_at,
        completed_at=record.completed_at,
        provider_reference=record.provider_reference,
        failure_code=record.failure_code,
    )


def to_idempotency_record(
    *, key_hash: str, fingerprint: str, submission_id: UUID, created_at: datetime
) -> ContactIdempotencyKeyRecord:
    return ContactIdempotencyKeyRecord(
        key_hash=key_hash,
        fingerprint=fingerprint,
        submission_id=submission_id,
        created_at=created_at,
    )
