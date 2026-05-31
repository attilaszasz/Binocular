FROM node:22-slim AS frontend-builder

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim AS builder

WORKDIR /build
COPY backend/pyproject.toml ./pyproject.toml
COPY backend/src ./src
COPY --from=frontend-builder /frontend/dist ./src/binocular/static_dist
RUN python -m pip install --no-cache-dir --root-user-action=ignore --upgrade pip build \
    && python -m build --wheel --outdir /wheels

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BINOCULAR_DATA_DIR=/app/data

RUN groupadd --system binocular \
    && useradd --system --gid binocular --home-dir /app --create-home binocular

WORKDIR /app
RUN mkdir -p /app/data /app/modules \
    && chown -R binocular:binocular /app/data /app/modules
COPY --from=builder /wheels/*.whl /tmp/
RUN python -m pip install --no-cache-dir --root-user-action=ignore /tmp/*.whl \
    && rm /tmp/*.whl

USER binocular
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2).read()"

CMD ["uvicorn", "binocular.main:app", "--host", "0.0.0.0", "--port", "8000"]