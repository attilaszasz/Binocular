# ── Frontend build ────────────────────────────────────────────
FROM node:22-slim AS frontend-builder

WORKDIR /build/frontend

ARG VITE_APP_VERSION=dev
ENV VITE_APP_VERSION=${VITE_APP_VERSION}

# Install deps first for layer caching.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Build the SPA.
COPY frontend/ ./
RUN npm run build

# ── Backend build ─────────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /build

# Install build dependencies for su-exec.
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc make libc-dev curl && \
    curl -fsSL https://github.com/ncopa/su-exec/archive/refs/tags/v0.2.tar.gz | tar xz && \
    cd su-exec-0.2 && make && cp su-exec /usr/local/bin/su-exec && \
    apt-get purge -y gcc make libc-dev curl && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* /build

# Install uv for fast dependency resolution.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock* /app/
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/src /app/src
RUN uv sync --frozen --no-dev


FROM python:3.13-slim

# Apply available Debian security updates without retaining package metadata.
RUN apt-get update && \
    apt-get upgrade -y && \
    rm -rf /var/lib/apt/lists/*

LABEL maintainer="Binocular" \
      description="Self-hosted firmware-update watcher"

# Copy su-exec from builder.
COPY --from=builder /usr/local/bin/su-exec /usr/local/bin/su-exec

# Copy the virtual environment and app source.
COPY --from=builder /app/.venv /app/.venv
COPY backend/src /app/src

# Copy the built frontend assets.
COPY --from=frontend-builder /build/frontend/dist /app/static_dist

# Copy entrypoint.
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Ensure volume directories exist.
RUN mkdir -p /app/data /app/modules

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "binocular.app:create_app", "--host", "0.0.0.0", "--port", "8000", "--factory"]
