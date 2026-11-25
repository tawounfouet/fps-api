from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from fps_platform.modules.contact.application.ports import ContactUnitOfWork
from fps_platform.modules.contact.domain.entities import ContactDelivery, ContactSubmission
from fps_platform.modules.contact.domain.enums import ContactWorkflowStatus
from fps_platform.modules.contact.domain.exceptions import ContactNotFoundError


def get_contact(uow: ContactUnitOfWork, submission_id: UUID) -> ContactSubmission:
    submission = uow.contacts.get(submission_id)
    if submission is None:
        raise ContactNotFoundError("contact submission was not found")
    return submission


def list_contacts(
    uow: ContactUnitOfWork,
    *,
    limit: int,
    offset: int,
    workflow_status: ContactWorkflowStatus | None = None,
) -> Sequence[ContactSubmission]:
    return uow.contacts.list(limit=limit, offset=offset, workflow_status=workflow_status)


def count_contacts(
    uow: ContactUnitOfWork, *, workflow_status: ContactWorkflowStatus | None = None
) -> int:
    return uow.contacts.count(workflow_status=workflow_status)


def list_deliveries(uow: ContactUnitOfWork, submission_id: UUID) -> Sequence[ContactDelivery]:
    return uow.deliveries.list_by_submission(submission_id)


def latest_delivery(uow: ContactUnitOfWork, submission_id: UUID) -> ContactDelivery | None:
    return uow.deliveries.latest(submission_id)
