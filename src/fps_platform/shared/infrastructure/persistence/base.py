from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase

from fps_platform.shared.infrastructure.persistence.naming import create_metadata


class Base(DeclarativeBase):
    metadata = create_metadata()
