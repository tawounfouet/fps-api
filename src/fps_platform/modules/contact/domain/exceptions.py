from __future__ import annotations


class ContactError(Exception):
    code = "CONTACT_ERROR"


class InvalidContactDataError(ContactError):
    code = "INVALID_CONTACT_DATA"


class ContactNotFoundError(ContactError):
    code = "CONTACT_NOT_FOUND"


class IdempotencyConflictError(ContactError):
    code = "IDEMPOTENCY_KEY_CONFLICT"


class InvalidContactTransitionError(ContactError):
    code = "INVALID_CONTACT_TRANSITION"


class ContactRateLimitError(ContactError):
    code = "RATE_LIMITED"

    def __init__(self, retry_after: int) -> None:
        super().__init__("contact submission rate limit exceeded")
        self.retry_after = retry_after


class ContactPayloadTooLargeError(ContactError):
    code = "PAYLOAD_TOO_LARGE"


class ContactUnsupportedMediaTypeError(ContactError):
    code = "UNSUPPORTED_MEDIA_TYPE"


class ContactDeliveryError(ContactError):
    code = "CONTACT_DELIVERY_FAILED"


class RetryableContactDeliveryError(ContactDeliveryError):
    code = "CONTACT_DELIVERY_RETRYABLE"


class PermanentContactDeliveryError(ContactDeliveryError):
    code = "CONTACT_DELIVERY_PERMANENT"
