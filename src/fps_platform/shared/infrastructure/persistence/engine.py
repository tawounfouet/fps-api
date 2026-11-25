from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True, slots=True)
class DatabaseRuntimeSettings:
    pool_size: int = 5
    max_overflow: int = 5
    pool_timeout: int = 5
    pool_recycle: int = 1800
    connect_timeout: int = 2

    def __post_init__(self) -> None:
        if self.pool_size < 1 or self.pool_size > 50:
            raise ValueError("DB_POOL_SIZE must be between 1 and 50")
        if self.max_overflow < 0 or self.max_overflow > 50:
            raise ValueError("DB_MAX_OVERFLOW must be between 0 and 50")
        if self.pool_timeout < 1 or self.pool_timeout > 60:
            raise ValueError("DB_POOL_TIMEOUT must be between 1 and 60")
        if self.pool_recycle < 30 or self.pool_recycle > 86400:
            raise ValueError("DB_POOL_RECYCLE must be between 30 and 86400")
        if self.connect_timeout < 1 or self.connect_timeout > 30:
            raise ValueError("DB_CONNECT_TIMEOUT must be between 1 and 30")


def create_db_engine(url: str, runtime: DatabaseRuntimeSettings | None = None) -> Engine:
    parsed = make_url(url)
    if parsed.get_backend_name() != "postgresql":
        raise ValueError("DATABASE_URL must use PostgreSQL")
    settings = runtime or DatabaseRuntimeSettings()
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_timeout=settings.pool_timeout,
        pool_recycle=settings.pool_recycle,
        connect_args={"connect_timeout": settings.connect_timeout},
        future=True,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)
