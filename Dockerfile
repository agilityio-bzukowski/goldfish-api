# syntax=docker/dockerfile:1
# Multi-stage build: builder installs deps + app, runtime runs uvicorn only.
# Layer order: deps first (pyproject.toml + poetry.lock) then src for cache.

FROM python:3.11-slim AS builder

ENV POETRY_VERSION=2.0.0 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_NO_INTERACTION=1

RUN apt-get update -q && apt-get install -y -q --no-install-recommends curl \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && apt-get purge -y -q curl && apt-get autoremove -y -q && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first for better layer caching (Poetry 2: --only main = production deps only)
COPY pyproject.toml poetry.lock ./
RUN /opt/poetry/bin/poetry install --only main --no-root

# Copy app and install the package into the venv
COPY src ./src
RUN /opt/poetry/bin/poetry install --only main

# Runtime stage: only venv + app (no Poetry/tools)
FROM python:3.11-slim AS runtime

WORKDIR /app

# Directory for SQLite DB (mounted as volume in compose)
RUN mkdir -p /app/data

# Copy virtualenv from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src"

# Copy application source (Poetry editable install references /app/src via .pth)
COPY --from=builder /app/src /app/src

# Copy Alembic so we can run migrations on startup
COPY alembic.ini ./
COPY alembic ./alembic

EXPOSE 8000

# Run migrations then start the API (DATABASE_URL must point at a writable path, e.g. /app/data)
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
