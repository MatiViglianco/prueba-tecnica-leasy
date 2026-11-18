# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1: install locked dependencies into a virtualenv with uv.
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

# Only the lockfiles first, so this layer stays cached until dependencies change.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ---------------------------------------------------------------------------
# Stage 2: slim runtime image, no build tooling, non-root user.
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=0 \
    DJANGO_DB_PATH=/app/data/db.sqlite3 \
    DJANGO_STATIC_ROOT=/app/staticfiles

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app --no-create-home app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app src ./src
COPY --chown=app:app docker/backend-entrypoint.sh /usr/local/bin/backend-entrypoint.sh

# Static files are collected at build time; the throwaway key is only for this
# command and never reaches the running container.
RUN DJANGO_SECRET_KEY=collectstatic-only python src/manage.py collectstatic --noinput \
    && mkdir -p /app/data \
    && chown -R app:app /app/data /app/staticfiles \
    && chmod +x /usr/local/bin/backend-entrypoint.sh

USER app

EXPOSE 8000
VOLUME ["/app/data"]

HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/accounts/login/', timeout=2)"]

ENTRYPOINT ["backend-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", \
     "--chdir", "src", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--no-control-socket", \
     "--access-logfile", "-"]
