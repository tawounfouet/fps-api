from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from fps_platform.api.schemas import ErrorResponse
from fps_platform.config import Settings
from fps_platform.modules.contact.api.dependencies import (
    get_admin_contact_uow,
    get_contact_settings,
)
from fps_platform.modules.contact.api.schemas import (
    ContactCommandResponse,
    ContactDeliveryResponse,
    ContactStatusChangeRequest,
    ContactSubmissionListResponse,
    ContactSubmissionResponse,
)
from fps_platform.modules.contact.application import handlers, queries
from fps_platform.modules.contact.application.commands import (
    ArchiveContactCommand,
    CloseContactCommand,
    ContactCommandResult,
    MarkContactedCommand,
    ReopenContactCommand,
    RetryContactDeliveryCommand,
)
from fps_platform.modules.contact.application.ports import ContactUnitOfWork
from fps_platform.modules.contact.domain.entities import ContactSubmission
from fps_platform.modules.contact.domain.enums import ContactWorkflowStatus
from fps_platform.modules.contact.domain.exceptions import InvalidContactDataError
from fps_platform.modules.contact.domain.value_objects import ContactCloseReason
from fps_platform.modules.identity.domain.value_objects import PermissionCode
from fps_platform.shared.auth.dependencies import require_permission

router = APIRouter(prefix="/api/v1/admin/contacts", tags=["admin"])

ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponse, "description": "Authentication is required"},
    403: {"model": ErrorResponse, "description": "Permission is denied"},
    404: {"model": ErrorResponse, "description": "Contact submission was not found"},
    409: {"model": ErrorResponse, "description": "Command conflicts with current state"},
    422: {"model": ErrorResponse, "description": "Validation error"},
}


def _submission_response(
    uow: ContactUnitOfWork, submission: ContactSubmission
) -> ContactSubmissionResponse:
    delivery = queries.latest_delivery(uow, submission.id)
    return ContactSubmissionResponse(
        id=submission.id,
        workflow_status=submission.workflow_status,
        received_at=submission.received_at,
        updated_at=submission.updated_at,
        contacted_at=submission.contacted_at,
        closed_at=submission.closed_at,
        archived_at=submission.archived_at,
        close_reason_code=submission.close_reason.value if submission.close_reason else None,
        version=submission.version,
        delivery_status=delivery.status if delivery is not None else None,
    )


def _command_response(result: ContactCommandResult) -> ContactCommandResponse:
    return ContactCommandResponse(
        submission_id=result.submission_id,
        workflow_status=result.workflow_status,
        delivery_status=result.delivery_status,
        version=result.version,
    )


@router.get(
    "",
    operation_id="adminListContacts",
    response_model=ContactSubmissionListResponse,
    responses=ERROR_RESPONSES,
)
def list_contacts(
    response: Response,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    workflow_status: ContactWorkflowStatus | None = Query(default=None, alias="status"),
    _: object = Depends(require_permission(PermissionCode.VIEW_CONTACTS)),
    uow: ContactUnitOfWork = Depends(get_admin_contact_uow),
) -> ContactSubmissionListResponse:
    submissions = queries.list_contacts(
        uow,
        limit=limit,
        offset=offset,
        workflow_status=workflow_status,
    )
    response.headers["Cache-Control"] = "no-store"
    return ContactSubmissionListResponse(
        items=[_submission_response(uow, submission) for submission in submissions],
        total=queries.count_contacts(uow, workflow_status=workflow_status),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{submission_id}",
    operation_id="adminGetContact",
    response_model=ContactSubmissionResponse,
    responses=ERROR_RESPONSES,
)
def get_contact(
    submission_id: UUID,
    _: object = Depends(require_permission(PermissionCode.VIEW_CONTACTS)),
    uow: ContactUnitOfWork = Depends(get_admin_contact_uow),
) -> ContactSubmissionResponse:
    return _submission_response(uow, queries.get_contact(uow, submission_id))


@router.get(
    "/{submission_id}/deliveries",
    operation_id="adminListContactDeliveries",
    response_model=list[ContactDeliveryResponse],
    responses=ERROR_RESPONSES,
)
def list_contact_deliveries(
    submission_id: UUID,
    _: object = Depends(require_permission(PermissionCode.VIEW_CONTACTS)),
    uow: ContactUnitOfWork = Depends(get_admin_contact_uow),
) -> list[ContactDeliveryResponse]:
    queries.get_contact(uow, submission_id)
    return [
        ContactDeliveryResponse(
            id=delivery.id,
            channel=delivery.channel.value,
            provider=delivery.provider,
            status=delivery.status,
            attempt_number=delivery.attempt_number,
            requested_at=delivery.requested_at,
            attempted_at=delivery.attempted_at,
            completed_at=delivery.completed_at,
            provider_reference=delivery.provider_reference,
            failure_code=delivery.failure_code,
        )
        for delivery in queries.list_deliveries(uow, submission_id)
    ]


@router.post(
    "/{submission_id}/contacted",
    operation_id="adminMarkContacted",
    response_model=ContactCommandResponse,
    responses=ERROR_RESPONSES,
)
def mark_contacted(
    submission_id: UUID,
    payload: ContactStatusChangeRequest,
    _: object = Depends(require_permission(PermissionCode.MANAGE_CONTACTS)),
    uow: ContactUnitOfWork = Depends(get_admin_contact_uow),
) -> ContactCommandResponse:
    result = handlers.mark_contacted(
        uow,
        MarkContactedCommand(
            submission_id=submission_id, expected_version=payload.expected_version
        ),
    )
    uow.commit()
    return _command_response(result)


@router.post(
    "/{submission_id}/close",
    operation_id="adminCloseContact",
    response_model=ContactCommandResponse,
    responses=ERROR_RESPONSES,
)
def close_contact(
    submission_id: UUID,
    payload: ContactStatusChangeRequest,
    _: object = Depends(require_permission(PermissionCode.MANAGE_CONTACTS)),
    uow: ContactUnitOfWork = Depends(get_admin_contact_uow),
) -> ContactCommandResponse:
    if payload.reason_code is None:
        raise InvalidContactDataError("reason_code is required")
    result = handlers.close_contact(
        uow,
        CloseContactCommand(
            submission_id=submission_id,
            reason=ContactCloseReason(payload.reason_code),
            expected_version=payload.expected_version,
        ),
    )
    uow.commit()
    return _command_response(result)


@router.post(
    "/{submission_id}/reopen",
    operation_id="adminReopenContact",
    response_model=ContactCommandResponse,
    responses=ERROR_RESPONSES,
)
def reopen_contact(
    submission_id: UUID,
    payload: ContactStatusChangeRequest,
    _: object = Depends(require_permission(PermissionCode.MANAGE_CONTACTS)),
    uow: ContactUnitOfWork = Depends(get_admin_contact_uow),
) -> ContactCommandResponse:
    result = handlers.reopen_contact(
        uow,
        ReopenContactCommand(
            submission_id=submission_id, expected_version=payload.expected_version
        ),
    )
    uow.commit()
    return _command_response(result)


@router.post(
    "/{submission_id}/archive",
    operation_id="adminArchiveContact",
    response_model=ContactCommandResponse,
    responses=ERROR_RESPONSES,
)
def archive_contact(
    submission_id: UUID,
    payload: ContactStatusChangeRequest,
    _: object = Depends(require_permission(PermissionCode.MANAGE_CONTACTS)),
    uow: ContactUnitOfWork = Depends(get_admin_contact_uow),
) -> ContactCommandResponse:
    result = handlers.archive_contact(
        uow,
        ArchiveContactCommand(
            submission_id=submission_id, expected_version=payload.expected_version
        ),
    )
    uow.commit()
    return _command_response(result)


@router.post(
    "/{submission_id}/delivery/retry",
    operation_id="adminRetryContactDelivery",
    response_model=ContactCommandResponse,
    responses=ERROR_RESPONSES,
)
def retry_delivery(
    submission_id: UUID,
    payload: ContactStatusChangeRequest,
    settings: Settings = Depends(get_contact_settings),
    _: object = Depends(require_permission(PermissionCode.MANAGE_CONTACTS)),
    uow: ContactUnitOfWork = Depends(get_admin_contact_uow),
) -> ContactCommandResponse:
    result = handlers.retry_contact_delivery(
        uow,
        RetryContactDeliveryCommand(
            submission_id=submission_id,
            provider=settings.contact_email_provider,
            max_attempts=settings.contact_delivery_max_attempts,
            expected_version=payload.expected_version,
        ),
    )
    uow.commit()
    return _command_response(result)
