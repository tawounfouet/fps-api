# M0 compatibility probe only, not FPS production application image.
# Index digest for official python:3.13-slim recorded 2026-11-25.
FROM python:3.13-slim@sha256:b3575dcf816cdacc5292df77a6e3e59b8941631078373a045efa2ac1e9c5c3b2
WORKDIR /probe
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_NO_PROGRESS=1
RUN python -m pip install --no-cache-dir uv==0.10.0
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY test_runtime_probe.py ./
CMD ["uv", "run", "--frozen", "pytest", "-q", "test_runtime_probe.py"]
