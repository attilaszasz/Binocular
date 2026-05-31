---
feature_branch: "00001-application-skeleton-container"
created: "2026-05-31"
input: "E001 Application Skeleton & Container"
spec_type: "technical"
spec_maturity: "draft"
epic_id: "E001"
epic_sources: "{SAD:ADR-0001}{SAD:ADR-0002}"
---

# Feature Specification: Application Skeleton & Container

**Feature Branch**: `00001-application-skeleton-container`  
**Created**: 2026-05-31  
**Status**: Draft  
**Spec Type**: technical  
**Spec Maturity**: draft  
**Epic ID**: E001  
**Epic Sources**: {SAD:ADR-0001}{SAD:ADR-0002}  
**Product Document**: specs/prd.md

## Problem Statement

Binocular needs a runnable foundation before product capabilities, data, scheduling, or modules can land. Operators and maintainers need a zero-config FastAPI app and container that start, report liveness, emit structured logs, and run with least privilege. Without it, later epics lack stable integration points and validation targets.

## Scope

### Included

- A Python 3.13 FastAPI backend skeleton with route, service, repository, and extension packages.
- Typed zero-required-settings configuration and a port 8000 runtime contract.
- A shallow `/healthz` endpoint returning a liveness payload.
- Structured JSON logging to stdout using `structlog`.
- A multi-stage non-root Docker image with a working `HEALTHCHECK`.

### Excluded

- SQLite migrations and repositories — owned by E004 Data Layer & Migrations.
- Frontend static asset serving — owned by E003 Frontend SPA Shell.
- Scheduler, scraping, modules, notifications, and auth — owned by later epics.
- CI workflow gates — owned by E002 Continuous Integration Pipeline.

### Edge Cases & Boundaries

- The app MUST start successfully with no environment variables set.
- Missing optional configuration MUST fall back to documented defaults.
- `/healthz` MUST remain cheap and MUST NOT depend on future database, network, or module-engine availability.
- Container health MUST fail when HTTP on port 8000 is unavailable.

## Technical Objectives

### Objective 1 - Runnable FastAPI Application Skeleton (Priority: P1)

Create the importable backend package and app factory with route, service, repository, and extension structure.

**Why this priority**: Blocks every later backend, frontend-serving, data, and module epic.

**Rationale**: A stable app factory gives later routers, lifespan hooks, and domain modules one integration point.

**Deliverables**:
- Backend package under `backend/src/` with an app factory and router aggregator.
- Route, service, repository, and extension-boundary packages.
- `/healthz` route registered through the route layer.

**Validation Criteria**:
1. **Given** backend dependencies are installed, **When** the app module is imported, **Then** the FastAPI app can be constructed without required configuration.
2. **Given** the application is running, **When** `GET /healthz` is requested, **Then** it returns a successful liveness payload.

### Objective 2 - Zero-Config Runtime Settings (Priority: P1)

Provide typed settings with defaults for service identity, host, port, data path placeholders, and logging mode.

**Why this priority**: Zero-config startup is a non-negotiable project principle and required for the first container smoke test.

**Rationale**: Later epics need a typed, centralized, test-overrideable configuration contract.

**Deliverables**:
- Typed settings module with defaults requiring no secrets or external services.
- Documented environment variable names for skeleton runtime settings.
- Test override path for app construction.

**Validation Criteria**:
1. **Given** no environment variables are set, **When** settings load, **Then** defaults resolve and include port 8000.
2. **Given** test overrides, **When** the app is constructed, **Then** override values are used without mutating global state.

### Objective 3 - Structured Logging Baseline (Priority: P1)

Configure structured stdout logging for startup, request events, and exceptions.

**Why this priority**: Honest failure and container operability depend on machine-readable logs from the first runnable increment.

**Rationale**: Later modules and services need logs that work with `docker logs` and no external telemetry.

**Deliverables**:
- `structlog` configuration initialized during app setup.
- JSON stdout renderer with timestamp, level, logger, event, and exception fields.
- Startup log event identifying the service.

**Validation Criteria**:
1. **Given** the app starts, **When** startup logging occurs, **Then** stdout contains parseable JSON with required fields.
2. **Given** an exception is logged, **When** the record is emitted, **Then** exception details are preserved.

### Objective 4 - Non-Root Container Image (Priority: P1)

Build a multi-stage image that exposes port 8000 and runs as non-root.

**Why this priority**: The project is distributed primarily as a single container and least-privilege execution is mandatory.

**Rationale**: A working image gives later epics a concrete runtime target and enforces deployment boundaries early.

**Deliverables**:
- Multi-stage `Dockerfile` based on Python 3.13 slim runtime.
- `.dockerignore` for local artifacts and dependency caches.
- Exec-form command and `HEALTHCHECK` targeting `/healthz`.

**Validation Criteria**:
1. **Given** Docker is available, **When** the image builds, **Then** the build succeeds without development caches.
2. **Given** the image is running, **When** user and `/healthz` are inspected, **Then** it is non-root and healthy on port 8000.

### Technical Constraints

- Backend source MUST live under `backend/src/` and use Python 3.13-compatible dependencies.
- The runtime MUST bind to port 8000 by default and expose one HTTP process.
- The container MUST run as non-root and require no external database, broker, cloud, account, or telemetry service.
- Route handlers MUST remain thin; domain and persistence concerns belong in service and repository layers.
- The extension seam MUST be documented as an in-process, unsandboxed trust boundary.

## Integration Points

- **IP-001**: Later API epics mount routers through the router aggregator.
- **IP-002**: E003 uses the app factory for static-file and SPA catch-all integration.
- **IP-003**: E004 uses lifespan/configuration hooks for SQLite startup.
- **IP-004**: E006 and E007 use the extension-boundary package and settings contract.
- **IP-005**: E002 uses the `Dockerfile` and backend commands as CI targets.

## Requirements

### Technical Requirements

- **TR-001**: System MUST provide a FastAPI app factory under `backend/src/` that imports and constructs without required external configuration.
- **TR-002**: System MUST organize backend code into route, service, repository, and extension-boundary packages.
- **TR-003**: System MUST expose `GET /healthz` returning a successful liveness payload when the process is responsive.
- **TR-004**: System MUST load typed runtime settings with zero-required-settings defaults, including port 8000.
- **TR-005**: System MUST configure JSON stdout logging with timestamp, level, logger, event, and exception fields.
- **TR-006**: System MUST provide a multi-stage Python 3.13 Docker image that starts the app on port 8000.
- **TR-007**: System MUST run the container process as a non-root user.
- **TR-008**: System MUST define a container `HEALTHCHECK` that verifies `/healthz` over HTTP.
- **TR-009**: System MUST document the core/extension trust boundary without claiming module sandboxing.

### Key Entities

- **App Factory**: Constructs the FastAPI app, router aggregation, settings, logging, and future lifespan hooks.
- **Settings**: Typed runtime configuration with safe defaults and environment overrides.
- **Health Endpoint**: Shallow liveness contract for operators, Docker healthcheck, and CI smoke tests.
- **Core/Extension Seam**: Package boundary where later unsandboxed extension-module integration attaches.

## Assumptions & Risks

### Assumptions

- Python 3.13-compatible backend dependencies are available.
- Docker is available for image validation.
- Frontend assets are not required for this skeleton image.
- Uvicorn is acceptable as the initial ASGI server.
- No default authentication is added in this epic.

### Risks

- **Dependency compatibility** *(likelihood: medium, impact: medium)*: Python 3.13 support may lag; mitigate with compatible pins.
- **Container health flakiness** *(likelihood: low, impact: medium)*: Startup timing could make healthchecks noisy; mitigate with start period.
- **Boundary drift** *(likelihood: medium, impact: high)*: Later work could bypass the app factory or seam; mitigate with docs and import tests.

## Implementation Signals

- `NEW-API` — Add `/healthz`.
- `NEW-CONFIG` — Add typed zero-config settings.
- `NEW-ENTITY` — Establish app factory, settings, health endpoint, and core/extension seam.
- `BREAKING-CHANGE` — None expected; no implementation source exists.

## Success Criteria

### Measurable Outcomes

- **SC-001** [OBJ1]: The FastAPI app imports, constructs, and serves locally without required environment variables.
- **SC-002** [OBJ1]: `GET /healthz` returns a 2xx liveness payload during local and container runs.
- **SC-003** [OBJ2]: Settings tests prove default port 8000 and at least one explicit override path.
- **SC-004** [OBJ3]: Logging tests parse startup logs as JSON and verify required fields.
- **SC-005** [OBJ4]: The Docker image builds successfully and runs the application as a non-root user.
- **SC-006** [OBJ4]: Docker healthcheck reaches `/healthz` on port 8000.

## Glossary

| Term | Definition |
|------|------------|
| App Factory | Function that constructs the FastAPI app. |
| Liveness Payload | Minimal response proving HTTP responsiveness. |
| Core/Extension Seam | In-process boundary for trusted user-managed modules. |
| Zero-Config Startup | Startup with sane defaults and no required environment variables. |

## Compliance Check

- **Status**: PASS
- **Checked Against**: project-instructions.md
- **Notes**: Preserves zero-config startup, non-root container execution, unsandboxed extension trust boundary, source-root layout, and no external service dependency.