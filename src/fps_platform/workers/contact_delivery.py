from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from fps_platform.modules.audit.domain.enums import AuditAction, AuditSource
from fps_platform.modules.contact.application.ports import (
    ContactEmailMessage,
    ContactUnitOfWork,
    EmailDeliveryPort,
)
from fps_platform.modules.contact.domain.entities import ContactDelivery, ContactSubmission
from fps_platform.modules.contact.domain.enums import ContactDeliveryStatus
from fps_platform.modules.contact.domain.exceptions import (
    PermanentContactDeliveryError,
    RetryableContactDeliveryError,
)
from fps_platform.modules.contact.domain.value_objects import normalize_failure_code
from fps_platform.modules.outbox.domain.enums import OutboxEventType
from fps_platform.modules.outbox.domain.outbox_event import OutboxEvent
from fps_platform.shared.domain.clock import Clock

UowFactory = Callable[[], ContactUnitOfWork]


@dataclass(slots=True)
class ContactDeliveryWorkerStats:
    released: int = 0
    claimed: int = 0
    succeeded: int = 0
    retried: int = 0
    dead: int = 0
    skipped: int = 0


class ContactDeliveryWorker:
    def __init__(
        self,
        *,
        uow_factory: UowFactory,
        email_port: EmailDeliveryPort,
        clock: Clock,
        provider: str,
        retry_delays_seconds: tuple[int, ...],
        lease_seconds: int,
        worker_id: str | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._email_port = email_port
        self._clock = clock
        self._provider = provider
        self._retry_delays = retry_delays_seconds
        self._lease_seconds = lease_seconds
        self._worker_id = worker_id or "contact-delivery-worker"

    def run_once(self, *, limit: int = 20) -> ContactDeliveryWorkerStats:
        stats = ContactDeliveryWorkerStats()
        now = self._clock.now()
        with self._uow_factory() as uow:
            stats.released = uow.outbox_events.release_expired(now=now, limit=limit)
            events = uow.outbox_events.list_due(now=now, limit=limit)
            uow.commit()
        for event in events:
            if event.event_type is not OutboxEventType.CONTACT_DELIVERY_REQUESTED:
                stats.skipped += 1
                continue
            self._process_event(event, stats)
        return stats

    def _process_event(self, event: OutboxEvent, stats: ContactDeliveryWorkerStats) -> None:
        now = self._clock.now()
        lease_token = uuid4()
        with self._uow_factory() as uow:
            claimed = uow.outbox_events.claim(
                event_id=event.id,
                lease_token=lease_token,
                leased_until=now + timedelta(seconds=self._lease_seconds),
                locked_by=self._worker_id,
                now=now,
            )
            if not claimed:
                stats.skipped += 1
                return
            stats.claimed += 1
            current_event = uow.outbox_events.get(event.id) or event
            delivery_id = self._payload_uuid(current_event, "delivery_intent_id")
            delivery = uow.deliveries.get(delivery_id)
            if delivery is None:
                uow.outbox_events.mark_dead(event_id=event.id, last_error_code="DELIVERY_NOT_FOUND")
                stats.dead += 1
                uow.commit()
                return
            submission = uow.contacts.get(delivery.submission_id)
            if submission is None:
                uow.outbox_events.mark_dead(event_id=event.id, last_error_code="CONTACT_NOT_FOUND")
                stats.dead += 1
                uow.commit()
                return
            if delivery.status is ContactDeliveryStatus.SUCCEEDED:
                uow.outbox_events.complete(event_id=event.id, completed_at=now)
                uow.commit()
                return
            if delivery.status is ContactDeliveryStatus.IN_PROGRESS:
                delivery.mark_failed(now, "STALE_IN_PROGRESS")
                uow.deliveries.save(delivery)
                self._record_failure_audit(uow, delivery, "STALE_IN_PROGRESS")
                self._apply_failure(uow, current_event, delivery, "STALE_IN_PROGRESS", stats, now)
                uow.commit()
                return
            if delivery.status is ContactDeliveryStatus.FAILED:
                delivery = self._new_attempt(uow, delivery, now)
            try:
                delivery.mark_in_progress(now)
                uow.deliveries.save(delivery)
                receipt = self._email_port.send(self._message(submission))
            except PermanentContactDeliveryError as exc:
                self._fail(
                    uow, current_event, delivery, type(exc).__name__, stats, now, permanent=True
                )
                uow.commit()
                return
            except RetryableContactDeliveryError as exc:
                self._fail(uow, current_event, delivery, type(exc).__name__, stats, now)
                uow.commit()
                return
            except Exception as exc:
                self._fail(uow, current_event, delivery, type(exc).__name__, stats, now)
                uow.commit()
                return
            delivery.mark_succeeded(now, receipt.provider_reference)
            uow.deliveries.save(delivery)
            uow.audit_recorder.record(
                action=AuditAction.CONTACT_DELIVERY_SUCCEEDED,
                resource_type="ContactSubmission",
                resource_id=submission.id,
                metadata={
                    "attempt_number": delivery.attempt_number,
                    "provider_code": receipt.provider,
                },
                source=AuditSource.WORKER,
            )
            uow.outbox_events.complete(event_id=event.id, completed_at=now)
            stats.succeeded += 1
            uow.commit()

    def _fail(
        self,
        uow: ContactUnitOfWork,
        event: OutboxEvent,
        delivery: ContactDelivery,
        error: str,
        stats: ContactDeliveryWorkerStats,
        now: datetime,
        *,
        permanent: bool = False,
    ) -> None:
        code = normalize_failure_code(error)
        if delivery.status is ContactDeliveryStatus.IN_PROGRESS:
            delivery.mark_failed(now, code)
            uow.deliveries.save(delivery)
        self._record_failure_audit(uow, delivery, code)
        self._apply_failure(uow, event, delivery, code, stats, now, permanent=permanent)

    def _apply_failure(
        self,
        uow: ContactUnitOfWork,
        event: OutboxEvent,
        delivery: ContactDelivery,
        code: str,
        stats: ContactDeliveryWorkerStats,
        now: datetime,
        *,
        permanent: bool = False,
    ) -> None:
        attempt = event.attempt_count
        if permanent or attempt >= event.max_attempts:
            uow.outbox_events.mark_dead(event_id=event.id, last_error_code=code)
            stats.dead += 1
            return
        delay = self._retry_delay(attempt)
        uow.outbox_events.mark_retry_wait(
            event_id=event.id,
            available_at=now + timedelta(seconds=delay),
            last_error_code=code,
        )
        stats.retried += 1

    def _retry_delay(self, attempt: int) -> int:
        index = max(0, min(attempt - 1, len(self._retry_delays) - 1))
        return self._retry_delays[index]

    def _new_attempt(
        self,
        uow: ContactUnitOfWork,
        previous: ContactDelivery,
        now: datetime,
    ) -> ContactDelivery:
        attempt = ContactDelivery(
            id=uuid4(),
            submission_id=previous.submission_id,
            channel=previous.channel,
            provider=self._provider,
            status=ContactDeliveryStatus.PENDING,
            attempt_number=uow.deliveries.next_attempt_number(previous.submission_id),
            requested_at=now,
        )
        uow.deliveries.add(attempt)
        return attempt

    def _message(self, submission: ContactSubmission) -> ContactEmailMessage:
        return ContactEmailMessage(
            submission_id=submission.id,
            template_code="contact_request",
            recipient_group_code="contact_team",
            locale=submission.locale,
            subject=submission.subject,
            first_name=submission.first_name,
            last_name=submission.last_name,
            email=submission.email,
            phone=submission.phone,
            organisation=submission.organisation,
            job_title=submission.job_title,
            message=submission.message,
            rgpd_consent=submission.rgpd_consent,
            correlation_id=self._worker_id,
        )

    def _record_failure_audit(
        self, uow: ContactUnitOfWork, delivery: ContactDelivery, code: str
    ) -> None:
        uow.audit_recorder.record(
            action=AuditAction.CONTACT_DELIVERY_FAILED,
            resource_type="ContactSubmission",
            resource_id=delivery.submission_id,
            metadata={"attempt_number": delivery.attempt_number, "failure_code": code},
            source=AuditSource.WORKER,
        )

    def _payload_uuid(self, event: OutboxEvent, key: str) -> UUID:
        value = event.payload.get(key)
        if not isinstance(value, str):
            raise ValueError("outbox payload is invalid")
        return UUID(value)


def build_contact_delivery_worker(
    *,
    uow_factory: UowFactory,
    email_port: EmailDeliveryPort,
    clock: Clock,
    provider: str,
    retry_delays_seconds: list[int],
    lease_seconds: int,
    worker_id: str | None = None,
) -> ContactDeliveryWorker:
    return ContactDeliveryWorker(
        uow_factory=uow_factory,
        email_port=email_port,
        clock=clock,
        provider=provider,
        retry_delays_seconds=tuple(retry_delays_seconds),
        lease_seconds=lease_seconds,
        worker_id=worker_id,
    )
