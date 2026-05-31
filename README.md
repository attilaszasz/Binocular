# Binocular

Binocular is a self-hosted firmware-update watcher for offline devices.

## Backend Skeleton

The backend lives under `backend/src/` and starts with zero required configuration.

```bash
cd backend
python -m pip install -e ".[dev]"
uvicorn binocular.main:app --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/healthz
```

Docker build and run:

```bash
docker build -t binocular:local .
docker run --rm -p 8000:8000 binocular:local
```

The container runs as the non-root `binocular` user and uses `/healthz` as its `HEALTHCHECK`.

## Self-Hosted Deployment

Binocular is designed for a trusted LAN and starts with authentication disabled. Optional HTTP basic auth can be enabled with `BINOCULAR_AUTH_ENABLED=true`, `BINOCULAR_AUTH_USERNAME`, and either `BINOCULAR_AUTH_PASSWORD` or `BINOCULAR_AUTH_PASSWORD_FILE`.

Basic auth is light protection for trusted-network or TLS reverse-proxy deployments. It is not a substitute for network isolation, TLS, or a public-internet security model.

All durable state should live in declared volumes: `/app/data` for SQLite data and backups, and `/app/modules` for trusted extension modules.

## Extension Trust Boundary

Future extension modules are user-vetted code. They are not sandboxed and will run in-process with application privileges. Non-root container execution reduces host-level blast radius but is not a sandbox.