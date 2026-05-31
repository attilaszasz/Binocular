# Research: Application Skeleton & Container
> E001 | 2026-05-31 | Inform architecture, validation, and QC tooling

## FastAPI Skeleton and Config
- **Decision**: Use a package-based FastAPI app factory with APIRouter aggregation and typed Pydantic Settings defaults.
- **Rationale**: This keeps startup importable, test-overridable, and compatible with later routers and lifespan hooks.
- **Rejected**: Route-heavy modules and direct environment reads; they hide ownership and complicate tests.
- **Pitfalls**: Do not require secrets, databases, or local-only files before app construction.
- **Sources**: https://fastapi.tiangolo.com/tutorial/bigger-applications/, https://fastapi.tiangolo.com/advanced/settings/

## Startup and Health Contract
- **Decision**: Bind one Uvicorn process on port 8000 and expose a cheap `/healthz` liveness endpoint.
- **Rationale**: Liveness should prove HTTP responsiveness without depending on future database or network dependencies.
- **Rejected**: Deep health checks for this epic; they belong with the dependencies they verify.
- **Pitfalls**: Avoid development reload mode and slow checks in the production container.
- **Sources**: https://fastapi.tiangolo.com/deployment/manually/, https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/

## Structured Logging
- **Decision**: Configure `structlog` once and render JSON logs to stdout.
- **Rationale**: Docker log collection and project observability both depend on parseable stdout records.
- **Rejected**: File-only logs and mixed renderers; they break container-first operation.
- **Pitfalls**: Avoid duplicate stdlib handlers and missing exception fields.
- **Sources**: https://www.structlog.org/en/stable/standard-library.html, https://docs.docker.com/engine/logging/

## Docker Runtime
- **Decision**: Use a multi-stage Python 3.13 slim image, exec-form command, non-root user, port 8000, and HTTP healthcheck.
- **Rationale**: This matches project deployment constraints and gives later epics one runtime target.
- **Rejected**: Root runtime, bundled build tools, shell-form commands, and deprecated FastAPI base images.
- **Pitfalls**: Copy order and `.dockerignore` must avoid cache churn and accidental local artifacts.
- **Sources**: https://docs.docker.com/develop/develop-images/dockerfile_best-practices/, https://fastapi.tiangolo.com/deployment/docker/

## Summary
| Topic | Decision | Rationale |
|-------|----------|-----------|
| App | FastAPI app factory | Importable, testable foundation |
| Config | Typed defaults | Zero-config startup |
| Health | Shallow `/healthz` | Cheap liveness |
| Runtime | Non-root multi-stage image | Least-privilege container |

## Sources Index
| URL | Topic | Fetched |
|-----|-------|---------|
| https://fastapi.tiangolo.com/tutorial/bigger-applications/ | FastAPI Skeleton and Config | 2026-05-31 |
| https://fastapi.tiangolo.com/advanced/settings/ | FastAPI Skeleton and Config | 2026-05-31 |
| https://fastapi.tiangolo.com/deployment/manually/ | Startup and Health Contract | 2026-05-31 |
| https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/ | Startup and Health Contract | 2026-05-31 |
| https://www.structlog.org/en/stable/standard-library.html | Structured Logging | 2026-05-31 |
| https://docs.docker.com/engine/logging/ | Structured Logging | 2026-05-31 |
| https://docs.docker.com/develop/develop-images/dockerfile_best-practices/ | Docker Runtime | 2026-05-31 |
| https://fastapi.tiangolo.com/deployment/docker/ | Docker Runtime | 2026-05-31 |