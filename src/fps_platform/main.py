from __future__ import annotations

from fps_platform.bootstrap import create_app
from fps_platform.config import Settings
from fps_platform.observability.logging import configure_logging

settings = Settings()
configure_logging(settings)
app = create_app(settings)
