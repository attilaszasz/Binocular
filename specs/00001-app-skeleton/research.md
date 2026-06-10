## Research Report

**Context**: Technical research for E001 — FastAPI app skeleton with Pydantic Settings config, structlog logging, non-root Docker container with PUID/PGID entrypoint, compose volumes.

## FastAPI Application Factory Pattern
- **Key findings**: FastAPI lifespan context manager (async generator) is the current pattern for startup/shutdown, replacing deprecated `on_event`. App factory pattern isolates config from import-time side effects and improves testability.
- **Recommended**: Use `create_app() -> FastAPI` factory with `@asynccontextmanager` lifespan. Register routers via an aggregator module.
- **Avoid**: Module-level FastAPI instantiation; deprecated `@app.on_event("startup")`.
### Sources
- https://fastapi.tiangolo.com/advanced/events/ — official lifespan docs

## Pydantic Settings for Configuration
- **Key findings**: `pydantic-settings` v2+ loads from env vars, `.env` files, and secrets directories. `model_config = SettingsConfigDict(env_prefix="BINOCULAR_")` is idiomatic. Fields with defaults enable zero-config startup per Principle VI.
- **Recommended**: Single `Settings` class with typed fields, sensible defaults, env-prefix. Use `secrets_dir` for Docker secrets compatibility.
- **Avoid**: Multiple settings classes for a single-container app; parsing env vars manually.
### Sources
- https://docs.pydantic.dev/latest/concepts/pydantic_settings/ — official pydantic-settings docs

## structlog JSON Logging
- **Key findings**: structlog's `configure()` with `JSONRenderer` for production and `ConsoleRenderer` for development. Bind request context via middleware. Use stdlib integration for library log capture.
- **Recommended**: Configure once at startup via lifespan. JSON in production, pretty console in dev (toggled by `LOG_FORMAT` env var). Use `structlog.stdlib.ProcessorPipeline`.
- **Avoid**: Multiple `structlog.configure()` calls; skipping stdlib integration (loses uvicorn/library logs).
### Sources
- https://www.structlog.org/en/stable/configuration.html — official config guide

## Non-Root Docker with PUID/PGID
- **Key findings**: LinuxServer.io pattern: entrypoint creates/modifies a user with specified PUID/PGID, chowns app directories, then exec's the app via `su-exec` (Alpine) or `gosu` (Debian). `python:3.13-slim` is Debian-based → `gosu` or install `su-exec` from source. Alternative: use `su-exec` from a static build.
- **Recommended**: Install `su-exec` in Dockerfile. Entrypoint: create `binocular` user with PUID/PGID (default 1000:1000), chown `/app/data` and `/app/modules`, exec via `su-exec binocular:binocular`. Use `ENTRYPOINT ["/entrypoint.sh"]`.
- **Avoid**: Running as root; using `su` (keeps parent process); hardcoded UID/GID.
### Sources
- https://github.com/ncopa/su-exec — lightweight setuid+setgid+exec
- https://docs.linuxserver.io/general/understanding-puid-and-pgid/ — PUID/PGID pattern

### Summary
Use FastAPI app factory with lifespan, Pydantic Settings for zero-config defaults, structlog configured once at startup with JSON/console toggle, and a su-exec-based entrypoint for PUID/PGID in the python:3.13-slim container.

### Sources Index
| URL | Topic | Fetched |
|-----|-------|---------| 
| https://fastapi.tiangolo.com/advanced/events/ | FastAPI lifespan | 2026-06-10 |
| https://docs.pydantic.dev/latest/concepts/pydantic_settings/ | Pydantic Settings | 2026-06-10 |
| https://www.structlog.org/en/stable/configuration.html | structlog config | 2026-06-10 |
| https://github.com/ncopa/su-exec | su-exec | 2026-06-10 |
| https://docs.linuxserver.io/general/understanding-puid-and-pgid/ | PUID/PGID | 2026-06-10 |
