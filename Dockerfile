FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home app

WORKDIR /app

COPY --chown=app:app pyproject.toml uv.lock README.md ./
COPY --chown=app:app src ./src

RUN pip install uv==0.11.18 \
    && uv sync --frozen --no-dev --no-editable --python /usr/local/bin/python3.13

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=2).read()" || exit 1

CMD ["/app/.venv/bin/uvicorn", "fps_platform.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
