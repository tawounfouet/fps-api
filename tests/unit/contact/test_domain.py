from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from fps_platform.modules.contact.domain.entities import ContactDelivery, ContactSubmission
from fps_platform.modules.contact.domain.enums import (
    ContactDeliveryChannel,
    ContactDeliveryStatus,
    ContactLocale,
    ContactSource,
    ContactSubject,
    ContactWorkflowStatus,
)
from fps_platform.modules.contact.domain.exceptions import InvalidContactTransitionError
from fps_platform.modules.contact.domain.value_objects import (
    ContactCloseReason,
    ContactEmailAddress,
    ContactIdempotencyKey,
    ContactMessage,
    ContactOptionalText,
    PersonName,
    PhoneNumber,
    contact_fingerprint,
)

MOMENT = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)


def status_value(submission: ContactSubmission) -> str:
    return str(submission.workflow_status.value)


def make_submission() -> ContactSubmission:
    return ContactSubmission(
        id=uuid4(),
        first_name=PersonName("Ada"),
        last_name=PersonName("Lovelace"),
        email=ContactEmailAddress("ada@example.test"),
        subject=ContactSubject.PARTENARIAT,
        message=ContactMessage("Bonjour"),
        locale=ContactLocale.FR,
        source=ContactSource.WEBSITE,
        workflow_status=ContactWorkflowStatus.RECEIVED,
        received_at=MOMENT,
        updated_at=MOMENT,
        version=1,
        phone=PhoneNumber("+33 1 23 45 67 89"),
        organisation=ContactOptionalText("Analytical Engines"),
        job_title=ContactOptionalText("Ingenieure"),
        rgpd_consent=True,
    )


def test_workflow_transitions_follow_decision_m4_dec04() -> None:
    submission = make_submission()
    submission.mark_contacted(MOMENT)
    assert status_value(submission) == "CONTACTED"
    submission.close(MOMENT, ContactCloseReason("resolved"))
    assert status_value(submission) == "CLOSED"
    submission.reopen(MOMENT)
    assert status_value(submission) == "CONTACTED"
    submission.close(MOMENT, ContactCloseReason("duplicate"))
    submission.archive(MOMENT)
    assert status_value(submission) == "ARCHIVED"
    assert submission.version == 6


def test_archive_requires_closed_status() -> None:
    submission = make_submission()
    with pytest.raises(InvalidContactTransitionError):
        submission.archive(MOMENT)


def test_delivery_transitions_are_guarded() -> None:
    delivery = ContactDelivery(
        id=uuid4(),
        submission_id=uuid4(),
        channel=ContactDeliveryChannel.EMAIL,
        provider="mock",
        status=ContactDeliveryStatus.PENDING,
        attempt_number=1,
        requested_at=MOMENT,
    )
    delivery.mark_in_progress(MOMENT)
    delivery.mark_succeeded(MOMENT, "mock_reference_001")
    assert delivery.status is ContactDeliveryStatus.SUCCEEDED
    with pytest.raises(InvalidContactTransitionError):
        delivery.mark_in_progress(MOMENT)


def test_idempotency_key_is_validated() -> None:
    with pytest.raises(ValueError):
        ContactIdempotencyKey("short")
    assert str(ContactIdempotencyKey("abcdefghijklmnop")) == "abcdefghijklmnop"


def test_fingerprint_is_canonical() -> None:
    first = contact_fingerprint({"b": 2, "a": "x"})
    second = contact_fingerprint({"a": "x", "b": 2})
    assert first == second
    assert len(first) == 64


def test_control_characters_are_rejected() -> None:
    with pytest.raises(ValueError):
        ContactMessage("bonjour\nmonde")
