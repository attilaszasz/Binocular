---
feature_branch: "00001-app-skeleton"
created: "2026-06-10"
input: "E001 Establish the runnable FastAPI app skeleton with config, logging, /healthz, non-root Docker container with PUID/PGID entrypoint, compose.yaml"
spec_type: "technical"
spec_maturity: "draft"
epic_id: "E001"
epic_sources: "{SAD:ADR-0001}{SAD:ADR-0002}{SAD:ADR-0008}{DOD:DDR-004}"
---

# Feature Specification: Application Skeleton & Container

**Feature Branch**: `00001-app-skeleton`
**Created**: 2026-06-10
**Status**: Draft
**Spec Type**: technical
**Spec Maturity**: draft
**Epic ID**: E001
**Epic Sources**: {SAD:ADR-0001}{SAD:ADR-0002}{SAD:ADR-0008}{DOD:DDR-004}
**Product Document**: specs/prd.md

## Problem Statement

Binocular has no runnable application yet. Every subsequent epic — data layer, module engine, UI, scheduling — depends on a working FastAPI process inside a correctly-configured container. Without this foundation, no increment can be built, tested, or deployed. The container must run as a non-root user with configurable PUID/PGID from day one to satisfy the least-privilege security posture (Principle IV).

## Scope

### Included

- FastAPI application factory with async lifespan and router aggregator
- Pydantic Settings configuration with environment variable support and zero-config defaults
- structlog logging with JSON (production) and console (development) output
- `/healthz` endpoint returning 200 OK
- `pyproject.toml` with all core dependencies
- `Dockerfile` based on `python:3.13-slim` with non-root execution
- `entrypoint.sh` supporting PUID/PGID via `su-exec`
- `compose.yaml` with `/app/data` and `/app/modules` volume mounts
- `.env.example` documenting all supported environment variables

### Excluded

- Database layer and migrations — deferred to E002
- CI pipeline — deferred to E003
- Frontend SPA — deferred to E004
- Application business logic (devices, modules, checks) — later epics
- HTTPS/TLS termination — out of scope, assumed handled by reverse proxy

### Edge Cases & Boundaries

- Missing PUID/PGID environment variables must fall back to safe defaults (1000:1000)
- Invalid PUID/PGID values (non-numeric, 0, negative) must cause the entrypoint to exit with a clear error
- The container must start successfully with no environment variables set (zero-config)
- `/healthz` must respond even when no downstream services are configured

## Technical Objectives

### Objective 1 - FastAPI Application Factory (Priority: P1)

The backend must expose a FastAPI application created via a factory function with async lifespan management and a centralized router aggregator, serving as the single entry point for all future route registration.

**Why this priority**: Foundation for every subsequent backend epic — nothing runs without the app factory.

**Rationale**: An app factory pattern isolates configuration from import-time side effects, enables test overrides, and provides a single lifespan for startup/shutdown orchestration. The router aggregator ensures future epics register endpoints without modifying the factory.

**Deliverables**:
- `backend/src/binocular/app.py` — app factory with lifespan
- `backend/src/binocular/routes/__init__.py` — router aggregator
- `backend/src/binocular/routes/health.py` — `/healthz` endpoint
- `backend/src/binocular/__init__.py` — package init

**Validation Criteria**:
1. **Given** the app factory is invoked, **When** the application starts, **Then** structlog is configured and the lifespan completes startup without error
2. **Given** the application is running, **When** `GET /healthz` is requested, **Then** the response is `200 OK` with a JSON body `{"status": "ok"}`
3. **Given** the application is running, **When** a new router module is added to the routes package, **Then** it can be registered via the aggregator without modifying `app.py`

### Objective 2 - Pydantic Settings Configuration (Priority: P1)

A single Pydantic Settings class must centralize all application configuration with typed fields, environment variable loading (prefixed `BINOCULAR_`), and sensible defaults enabling zero-config startup.

**Why this priority**: Every component reads configuration — the config module is a prerequisite for the app factory lifespan and all downstream epics.

**Rationale**: Pydantic Settings provides type validation, env-var loading, `.env` support, and secrets-directory integration. A single class avoids fragmented configuration and ensures all settings are discoverable.

**Deliverables**:
- `backend/src/binocular/config.py` — `Settings` class with Pydantic Settings
- `.env.example` — documents all supported environment variables

**Validation Criteria**:
1. **Given** no environment variables are set, **When** `Settings()` is instantiated, **Then** all fields have valid defaults and the application starts
2. **Given** `BINOCULAR_LOG_FORMAT=json` is set, **When** `Settings()` is instantiated, **Then** `settings.log_format` equals `"json"`
3. **Given** an invalid value for a typed field, **When** `Settings()` is instantiated, **Then** a `ValidationError` is raised with a clear message

### Objective 3 - Structured Logging (Priority: P1)

structlog must be configured once at application startup with JSON output for production and console output for development, capturing both application and library (uvicorn) logs.

**Why this priority**: Observability from the first line of code — all subsequent epics emit logs through this configuration.

**Rationale**: structlog with stdlib integration captures uvicorn and third-party library logs in the same pipeline. JSON output enables log aggregation; console output aids local development.

**Deliverables**:
- `backend/src/binocular/logging.py` — structlog configuration function

**Validation Criteria**:
1. **Given** `log_format="json"`, **When** logging is configured and a log event is emitted, **Then** output is valid JSON with `event`, `level`, and `timestamp` fields
2. **Given** `log_format="console"`, **When** logging is configured and a log event is emitted, **Then** output is human-readable colored console format
3. **Given** logging is configured, **When** uvicorn emits a log, **Then** it appears in the structlog pipeline with consistent formatting

### Objective 4 - Non-Root Docker Container with PUID/PGID (Priority: P1)

The Docker image must be based on `python:3.13-slim`, execute the application as a non-root user, and support configurable PUID/PGID via an entrypoint script using `su-exec`.

**Why this priority**: Security posture (Principle IV) — the container must never run as root; PUID/PGID enables host volume permission alignment.

**Rationale**: LinuxServer-style PUID/PGID lets self-hosters align container user IDs with host filesystem ownership. `su-exec` replaces the entrypoint process (no zombie parent) and is lightweight.

**Deliverables**:
- `Dockerfile` — multi-stage or single-stage build with `su-exec`, non-root user
- `entrypoint.sh` — PUID/PGID user creation, directory ownership, exec via `su-exec`
- `compose.yaml` — service definition with volume mounts and environment variables

**Validation Criteria**:
1. **Given** `PUID=1001 PGID=1001`, **When** the container starts, **Then** the application process runs as UID 1001 / GID 1001
2. **Given** no PUID/PGID set, **When** the container starts, **Then** the application runs as UID 1000 / GID 1000 (defaults)
3. **Given** `PUID=0`, **When** the container starts, **Then** the entrypoint exits with a non-zero code and error message
4. **Given** the container starts successfully, **When** `GET /healthz` is sent to port 8000, **Then** the response is `200 OK`
5. **Given** the container restarts, **When** `/app/data` contains prior state, **Then** the data persists intact

### Technical Constraints

- Python 3.13+ required
- `mypy --strict` must pass on all backend source code
- Single port exposure (8000)
- Base image: `python:3.13-slim`
- Application runs via `uvicorn` with the app factory
- Source code under `backend/src/binocular/` per ENFORCE_SRC_ROOT policy

## Integration Points

- **IP-001**: E002 (Data Layer) depends on the app factory lifespan for database connection lifecycle
- **IP-002**: E003 (CI Pipeline) depends on `pyproject.toml` for dependency installation and test/lint commands
- **IP-003**: E004 (Frontend SPA) depends on the FastAPI static file / SPA serving capability
- **IP-004**: E005–E020 depend on the router aggregator for endpoint registration
- **IP-005**: All epics depend on `config.py` for settings access and `logging.py` for log output

## Requirements

### Technical Requirements

- **TR-001**: System MUST expose a `create_app()` factory function returning a configured FastAPI application
- **TR-002**: System MUST provide a `/healthz` endpoint returning `200 OK` with `{"status": "ok"}`
- **TR-003**: System MUST load configuration from environment variables with `BINOCULAR_` prefix via Pydantic Settings
- **TR-004**: System MUST start with zero required configuration (all settings have defaults)
- **TR-005**: System MUST configure structlog with JSON output when `LOG_FORMAT=json` and console output otherwise
- **TR-006**: System MUST capture uvicorn and stdlib logs through the structlog pipeline
- **TR-007**: Dockerfile MUST use `python:3.13-slim` base and execute the application as a non-root user
- **TR-008**: `entrypoint.sh` MUST support PUID/PGID environment variables (default 1000:1000) using `su-exec`
- **TR-009**: `entrypoint.sh` MUST reject PUID or PGID of 0 with a non-zero exit code
- **TR-010**: `compose.yaml` MUST define `/app/data` and `/app/modules` as named or bind-mount volumes
- **TR-011**: All backend source MUST pass `mypy --strict`
- **TR-012**: `pyproject.toml` MUST declare all runtime and development dependencies

### Key Entities

- **Settings**: Application configuration — log format, host, port, data directory path, module directory path. No persistent state.
- **HealthResponse**: Schema for the `/healthz` response — `status` field.

## Assumptions & Risks

### Assumptions

- `su-exec` can be compiled from source or installed via `apt` on `python:3.13-slim` (Debian Bookworm)
- The application will be the sole process in the container (no process supervisor needed)
- Uvicorn is run directly (not behind gunicorn) — single-worker is sufficient for the target audience

### Risks

- **su-exec availability** *(likelihood: low, impact: medium)*: If `su-exec` is unavailable in Debian repos, building from source adds Dockerfile complexity. Mitigation: `gosu` is an alternative with Debian packages.
- **Python 3.13 slim image size** *(likelihood: low, impact: low)*: Newer Python images may be larger. Mitigation: multi-stage build if needed.

## Implementation Signals

- `NEW-API` — `/healthz` endpoint, router aggregator
- `NEW-CONFIG` — Pydantic Settings class, `.env.example`, `compose.yaml`
- `NEW-ENTITY` — Settings and HealthResponse schemas (no persistence)

## Success Criteria

### Measurable Outcomes

- **SC-001** [OBJ1]: Application starts via `create_app()` and responds to `GET /healthz` with `200 OK`
- **SC-002** [OBJ2]: `Settings()` instantiates with valid defaults when no env vars are set
- **SC-003** [OBJ3]: Log output is valid JSON when `LOG_FORMAT=json` and human-readable when `LOG_FORMAT=console`
- **SC-004** [OBJ4]: `docker compose up` starts the container, `/healthz` responds on port 8000, process runs as non-root user matching PUID/PGID
- **SC-005** [OBJ4]: Container data in `/app/data` survives `docker compose down && docker compose up`

## Glossary

| Term | Definition |
|------|------------|
| App factory | A function (`create_app()`) that constructs and returns a configured FastAPI application instance |
| PUID/PGID | User ID and Group ID environment variables for mapping container process ownership to host filesystem |
| su-exec | Lightweight tool that switches UID/GID and exec's the target process, replacing the current process (no zombie parent) |
| Lifespan | FastAPI async context manager for startup/shutdown logic, replacing deprecated `on_event` handlers |

## Compliance Check

### Instructions Check Report
**Target**: spec.md
**Status**: PASS

| Principle | Verdict | Notes |
|-----------|---------|-------|
| I. Honest Failure | N/A | No detection logic in skeleton |
| II. Polite by Default | N/A | No outbound scraping |
| III. Data Ownership | PASS | Volumes reference single SQLite path, no external deps |
| IV. Least-Privilege | PASS | TR-007/TR-008/TR-009 enforce non-root with PUID/PGID |
| V. Type Safety | PASS | TR-011 requires `mypy --strict` |
| VI. Set-and-Forget | PASS | TR-004 requires zero-config startup |
| VII. Agent Output Style | N/A | Spec document |

