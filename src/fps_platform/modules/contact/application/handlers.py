from __future__ import annotations

from hashlib import sha256
from uuid import UUID

from fps_platform.modules.audit.domain.enums import AuditAction, AuditSource
from fps_platform.modules.contact.application.commands import (
    ArchiveContactCommand,
    CloseContactCommand,
    ContactCommandResult,
    ContactSubmissionResult,
    MarkContactedCommand,
    ReopenContactCommand,
    RetryContactDeliveryCommand,
    SubmitContactCommand,
)
from fps_platform.modules.contact.application.ports import ContactUnitOfWork
from fps_platform.modules.contact.domain.entities import ContactDelivery, ContactSubmission
from fps_platform.modules.contact.domain.enums import (
    ContactDeliveryChannel,
    ContactDeliveryStatus,
    ContactSource,
    ContactWorkflowStatus,
)
from fps_platform.modules.contact.domain.exceptions import (
    ContactNotFoundError,
    InvalidContactTransitionError,
)
from fps_platform.modules.contact.domain.value_objects import contact_fingerprint
from fps_platform.modules.outbox.domain.enums import OutboxEventType
from fps_platform.shared.domain.errors import ConcurrentModificationError


def _key_hash(command: SubmitContactCommand) -> str:
    return sha256(command.idempotency_key.value.encode("utf-8")).hexdigest()


def _fingerprint(command: SubmitContactCommand) -> str:
    return contact_fingerprint(
        {
            "first_name": str(command.first_name),
            "last_name": str(command.last_name),
            "email": str(command.email),
            "phone": str(command.phone) if command.phone is not None else "",
            "organisation": str(command.organisation) if command.organisation is not None else "",
            "job_title": str(command.job_title) if command.job_title is not None else "",
            "subject": str(command.subject),
            "message": str(command.message),
            "locale": str(command.locale),
            "rgpd_consent": command.rgpd_consent,
        }
    )


def _delivery_status(uow: ContactUnitOfWork, submission_id: UUID) -> ContactDeliveryStatus:
    delivery = uow.deliveries.latest(submission_id)
    return delivery.status if delivery is not None else ContactDeliveryStatus.PENDING


def _load_submission(uow: ContactUnitOfWork, submission_id: UUID) -> ContactSubmission:
    submission = uow.contacts.get(submission_id)
    if submission is None:
        raise ContactNotFoundError("contact submission was not found")
    return submission


def _require_version(submission: ContactSubmission, expected_version: int | None) -> None:
    if expected_version is not None and expected_version != submission.version:
        raise ConcurrentModificationError("contact version changed")


def _command_result(uow: ContactUnitOfWork, submission: ContactSubmission) -> ContactCommandResult:
    return ContactCommandResult(
        submission_id=submission.id,
        workflow_status=submission.workflow_status,
        delivery_status=_delivery_status(uow, submission.id),
        version=submission.version,
    )


def _record_contact_outbox(
    uow: ContactUnitOfWork,
    *,
    submission: ContactSubmission,
    delivery: ContactDelivery,
    template_code: str,
    recipient_group_code: str,
    max_attempts: int,
) -> None:
    uow.outbox_recorder.record(
        event_type=OutboxEventType.CONTACT_DELIVERY_REQUESTED,
        aggregate_type="ContactSubmission",
        aggregate_id=submission.id,
        operation_id=f"contact-delivery-{delivery.id}",
        dedup_key=f"contact-delivery-{delivery.id}",
        payload={
            "contact_submission_id": str(submission.id),
            "delivery_intent_id": str(delivery.id),
            "template_code": template_code,
            "recipient_group_code": recipient_group_code,
        },
        max_attempts=max_attempts,
    )


def submit_contact(
    uow: ContactUnitOfWork, command: SubmitContactCommand
) -> ContactSubmissionResult:
    key_hash = _key_hash(command)
    fingerprint = _fingerprint(command)
    submission_id = uow.id_generator.new_id()
    existing_id = uow.idempotency_keys.claim(
        key_hash=key_hash,
        fingerprint=fingerprint,
        submission_id=submission_id,
    )
    if existing_id is not None:
        existing = _load_submission(uow, existing_id)
        return ContactSubmissionResult(
            submission_id=existing.id,
            workflow_status=existing.workflow_status,
            delivery_status=_delivery_status(uow, existing.id),
            replayed=True,
        )

    now = uow.clock.now()
    submission = ContactSubmission(
        id=submission_id,
        first_name=command.first_name,
        last_name=command.last_name,
        email=command.email,
        phone=command.phone,
        organisation=command.organisation,
        job_title=command.job_title,
        subject=command.subject,
        message=command.message,
        locale=command.locale,
        source=ContactSource.WEBSITE,
        workflow_status=ContactWorkflowStatus.RECEIVED,
        rgpd_consent=command.rgpd_consent,
        received_at=now,
        updated_at=now,
        version=1,
    )
    uow.contacts.add(submission)

    delivery = ContactDelivery(
        id=uow.id_generator.new_id(),
        submission_id=submission.id,
        channel=ContactDeliveryChannel.EMAIL,
        provider=command.provider,
        status=ContactDeliveryStatus.PENDING,
        attempt_number=1,
        requested_at=now,
    )
    uow.deliveries.add(delivery)
    _record_contact_outbox(
        uow,
        submission=submission,
        delivery=delivery,
        template_code=command.template_code,
        recipient_group_code=command.recipient_group_code,
        max_attempts=command.max_attempts,
    )
    uow.audit_recorder.record(
        action=AuditAction.CONTACT_DELIVERY_REQUESTED,
        resource_type="ContactSubmission",
        resource_id=submission.id,
        metadata={
            "template_code": command.template_code,
            "recipient_group_code": command.recipient_group_code,
        },
        source=AuditSource.APPLICATION,
    )
    return ContactSubmissionResult(
        submission_id=submission.id,
        workflow_status=submission.workflow_status,
        delivery_status=delivery.status,
        replayed=False,
    )


def mark_contacted(uow: ContactUnitOfWork, command: MarkContactedCommand) -> ContactCommandResult:
    submission = _load_submission(uow, command.submission_id)
    _require_version(submission, command.expected_version)
    previous = submission.workflow_status.value
    submission.mark_contacted(uow.clock.now())
    uow.contacts.save(submission, expected_version=submission.version - 1)
    uow.audit_recorder.record(
        action=AuditAction.CONTACT_MARKED_CONTACTED,
        resource_type="ContactSubmission",
        resource_id=submission.id,
        metadata={"from_status": previous, "to_status": submission.workflow_status.value},
    )
    return _command_result(uow, submission)


def close_contact(uow: ContactUnitOfWork, command: CloseContactCommand) -> ContactCommandResult:
    submission = _load_submission(uow, command.submission_id)
    _require_version(submission, command.expected_version)
    previous = submission.workflow_status.value
    submission.close(uow.clock.now(), command.reason)
    uow.contacts.save(submission, expected_version=submission.version - 1)
    uow.audit_recorder.record(
        action=AuditAction.CONTACT_CLOSED,
        resource_type="ContactSubmission",
        resource_id=submission.id,
        metadata={
            "from_status": previous,
            "to_status": submission.workflow_status.value,
            "reason_code": command.reason.value,
        },
    )
    return _command_result(uow, submission)


def reopen_contact(uow: ContactUnitOfWork, command: ReopenContactCommand) -> ContactCommandResult:
    submission = _load_submission(uow, command.submission_id)
    _require_version(submission, command.expected_version)
    previous = submission.workflow_status.value
    submission.reopen(uow.clock.now())
    uow.contacts.save(submission, expected_version=submission.version - 1)
    uow.audit_recorder.record(
        action=AuditAction.CONTACT_REOPENED,
        resource_type="ContactSubmission",
        resource_id=submission.id,
        metadata={"from_status": previous, "to_status": submission.workflow_status.value},
    )
    return _command_result(uow, submission)


def archive_contact(uow: ContactUnitOfWork, command: ArchiveContactCommand) -> ContactCommandResult:
    submission = _load_submission(uow, command.submission_id)
    _require_version(submission, command.expected_version)
    previous = submission.workflow_status.value
    submission.archive(uow.clock.now())
    uow.contacts.save(submission, expected_version=submission.version - 1)
    uow.audit_recorder.record(
        action=AuditAction.CONTACT_ARCHIVED,
        resource_type="ContactSubmission",
        resource_id=submission.id,
        metadata={"from_status": previous, "to_status": submission.workflow_status.value},
    )
    return _command_result(uow, submission)


def retry_contact_delivery(
    uow: ContactUnitOfWork, command: RetryContactDeliveryCommand
) -> ContactCommandResult:
    submission = _load_submission(uow, command.submission_id)
    _require_version(submission, command.expected_version)
    latest = uow.deliveries.latest(submission.id)
    if latest is None:
        raise ContactNotFoundError("contact delivery was not found")
    if latest.status is ContactDeliveryStatus.SUCCEEDED:
        raise InvalidContactTransitionError("a succeeded delivery cannot be retried")
    if latest.status in {ContactDeliveryStatus.PENDING, ContactDeliveryStatus.IN_PROGRESS}:
        raise InvalidContactTransitionError("an active delivery cannot be retried")
    attempt_number = uow.deliveries.next_attempt_number(submission.id)
    if attempt_number > command.max_attempts:
        raise InvalidContactTransitionError("delivery retry budget is exhausted")
    now = uow.clock.now()
    delivery = ContactDelivery(
        id=uow.id_generator.new_id(),
        submission_id=submission.id,
        channel=ContactDeliveryChannel.EMAIL,
        provider=command.provider,
        status=ContactDeliveryStatus.PENDING,
        attempt_number=attempt_number,
        requested_at=now,
    )
    uow.deliveries.add(delivery)
    _record_contact_outbox(
        uow,
        submission=submission,
        delivery=delivery,
        template_code="contact_request",
        recipient_group_code="contact_team",
        max_attempts=command.max_attempts,
    )
    uow.audit_recorder.record(
        action=AuditAction.CONTACT_DELIVERY_RETRIED,
        resource_type="ContactSubmission",
        resource_id=submission.id,
        metadata={"attempt_number": attempt_number},
    )
    return _command_result(uow, submission)
