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
FROM python:3.13-alpine3.23 AS builder

WORKDIR /build

# Install build dependencies and the non-root entrypoint helper.
RUN apk add --no-cache build-base curl su-exec

# Install uv for fast dependency resolution.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock* /app/
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/src /app/src
RUN uv sync --frozen --no-dev


FROM python:3.13-alpine3.23

# Install runtime user-management tools and pull current security fixes.
RUN apk add --no-cache shadow && apk upgrade --no-cache

# Remove unused pip, including its independently vendored urllib3.
RUN python -m pip uninstall --yes pip

LABEL maintainer="Binocular" \
      description="Self-hosted firmware-update watcher"

# Copy su-exec from builder.
COPY --from=builder /sbin/su-exec /sbin/su-exec

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
