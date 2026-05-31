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

## Extension Trust Boundary

Future extension modules are user-vetted code. They are not sandboxed and will run in-process with application privileges. Non-root container execution reduces host-level blast radius but is not a sandbox.