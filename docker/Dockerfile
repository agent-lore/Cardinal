# syntax=docker/dockerfile:1.7
# Cardinal - GitHub repository analysis CLI tool
# Multi-stage build for smaller image

# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

RUN uv venv /app/.venv
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV UV_LINK_MODE=copy

# Cache dependency layer separately from source
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

# Install the project separately so normal code changes reuse the cached dependency layer.
COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install .

# Stage 2: Runtime image
FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Install git for repo cloning operations
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Create runtime user and data directory with host-friendly ownership
RUN groupadd --gid 1000 cardinal \
    && useradd --uid 1000 --gid 1000 --create-home --home-dir /home/cardinal --shell /usr/sbin/nologin cardinal \
    && mkdir -p /data/repos \
    && chown -R 1000:1000 /data /home/cardinal

# Default environment variables pointing to /data paths
ENV HOME=/home/cardinal
ENV CARDINAL_CONFIG=/data/cardinal.toml
ENV CARDINAL_DB_PATH=/data/cardinal.db
ENV CARDINAL_REPO_DIR=/data/repos

USER 1000:1000

CMD ["cardinal", "--help"]
