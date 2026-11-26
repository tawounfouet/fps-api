from __future__ import annotations


class InvalidMediaTransitionError(ValueError):
    pass


class InvalidMediaObjectError(ValueError):
    pass


class MediaStorageError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


class MediaStorageTransientError(MediaStorageError):
    def __init__(self, message: str) -> None:
        super().__init__(message, retryable=True)


class MediaStoragePermanentError(MediaStorageError):
    def __init__(self, message: str) -> None:
        super().__init__(message, retryable=False)
