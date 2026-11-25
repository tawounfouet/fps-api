from __future__ import annotations


class RepositoryError(Exception):
    pass


class NotFoundError(RepositoryError):
    pass


class ConflictError(RepositoryError):
    pass


class ConcurrentModificationError(ConflictError):
    pass
