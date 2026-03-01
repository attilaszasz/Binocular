# Binocular Project Instructions

## Core Principles

### I. Self-Contained Deployment

The application MUST run as a single Docker container with zero external dependencies.

- All data persistence MUST use SQLite stored in a single mounted volume (`/app/data`). No external database servers (Postgres, MySQL, Redis) are permitted.
- The container MUST start with zero required environment variables, using sensible defaults for all configuration.
- The Docker image MUST run as a non-root user and include a `HEALTHCHECK` instruction.
- The backend and frontend MUST be served through a single exposed port.
- A `docker-compose.yml` MUST be provided for one-command startup.

**Rationale**: Binocular targets homelab users who expect "set and forget" reliability. A batteries-included, single-container deployment removes friction and maintenance burden. Aligned with 12-Factor App principles adapted for self-hosted tools (https://12factor.net/).

### II. Extension-First Architecture

All device-specific intelligence MUST live in Extension Modules. The core system MUST NOT hard-code any vendor-specific scraping logic.

- Extension Modules MUST implement a strict interface contract (Protocol/ABC) validated at load time. Modules that do not conform MUST be rejected with a clear error message.
- Modules MUST be loaded via `importlib` — never `exec()` or `eval()`.
- Each module execution MUST be wrapped in an isolated error boundary (`try/except`) so a single broken script cannot crash the scheduler or core application.
- Module return values MUST be validated through Pydantic models before entering core logic.
- Modules SHOULD declare a capability manifest (e.g., `MODULE_VERSION`, `SUPPORTED_DEVICE_TYPE`) for registration and compatibility checks.

**Rationale**: The extension system is Binocular's core differentiator. A strict contract ensures reliability and empowers users to add device support without modifying core code. Pattern guidance from Python packaging standards (https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/).

### III. Responsible Scraping (NON-NEGOTIABLE)

All automated web requests MUST follow ethical scraping practices. Violations of this principle are blocking defects.

- Modules MUST check `robots.txt` before fetching and honor `Crawl-delay` directives (RFC 9309).
- All requests MUST use a descriptive `User-Agent` string (e.g., `Binocular/1.0 (+https://github.com/...)`).
- A minimum per-domain delay of 2 seconds MUST be enforced between consecutive requests to the same host.
- The system MUST implement exponential backoff with jitter on HTTP 429 and 5xx responses.
- Responses SHOULD be cached aggressively — firmware pages rarely change more than once per week.
- Modules SHOULD prefer structured data sources (RSS, APIs, `<meta>` tags) over deep DOM parsing when available.

**Rationale**: Aggressive scraping gets IPs banned and damages the project's reputation. Responsible scraping ensures long-term viability and respects manufacturer infrastructure. Aligned with RFC 9309 (https://datatracker.ietf.org/doc/html/rfc9309).

### IV. Type Safety & Validation

The codebase MUST enforce type safety and input validation at all boundaries.

- All Python code MUST pass `mypy --strict` with zero errors.
- All API request and response payloads MUST be validated through Pydantic models.
- Structured logging (via `structlog` or equivalent) MUST be used; plain `print()` statements are not permitted in production code.
- All configuration MUST be validated through Pydantic `BaseSettings` models with explicit defaults and type constraints.

**Rationale**: Type safety catches entire categories of bugs at development time. Pydantic at API boundaries provides automatic validation, serialization, and OpenAPI documentation. Structured logging enables effective troubleshooting in containerized environments. Guidance from Pydantic (https://docs.pydantic.dev/) and FastAPI (https://fastapi.tiangolo.com/) documentation.

### V. Test-First Development

Tests MUST be written before implementation code. The Red-Green-Refactor cycle is strictly enforced.

- All features MUST have API-level integration tests using `pytest` + `httpx.AsyncClient` via FastAPI's `TestClient`.
- Tests MUST use isolated SQLite instances (in-memory or temp-file fixtures) — never the production database.
- Extension Module contract compliance MUST be covered by dedicated test fixtures that validate the interface contract.
- Test coverage SHOULD target API behavior and integration boundaries, not internal implementation details.

**Rationale**: Test-first development prevents regressions and documents expected behavior. API-level integration tests provide higher confidence than unit-mocking internals for a web application. Guidance from FastAPI testing docs (https://fastapi.tiangolo.com/advanced/testing/).

## Technology Stack

The following technology choices are fixed for the initial release. Changes require a MAJOR version bump to these instructions.

| Layer | Technology | Version Constraint |
|---|---|---|
| Backend | Python + FastAPI | Python 3.11+ |
| Frontend | React + Tailwind CSS | Vite build toolchain |
| Database | SQLite | WAL mode, `busy_timeout` configured |
| Scheduling | APScheduler | In-process, no external broker |
| Notifications | Apprise | Email (SMTP) + Gotify required at launch |
| Containerization | Docker | Single-stage or multi-stage build, `python:3.11-slim` base |

- The backend MUST serve frontend static assets directly via FastAPI `StaticFiles` (single-port architecture).
- SQLite MUST be configured with WAL journal mode and an appropriate `busy_timeout` for concurrent read/write access.
- Dependencies MUST be pinned with exact versions in a lock file (`poetry.lock` or `requirements.txt` with hashes).

## Development Workflow

### Code Quality Gates

- All code MUST pass linting (`ruff`), formatting (`ruff format`), and type checking (`mypy --strict`) before merge.
- All API endpoints MUST have corresponding integration tests that pass.
- Extension Module changes MUST include updated contract tests.

### Documentation Standards

- All public API endpoints MUST have OpenAPI documentation generated from Pydantic models.
- Extension Module contract MUST be documented with a developer guide and at least two working example modules (Sony Alpha, Panasonic Lumix).
- The README MUST include a Quick Start command (`docker run ...` or `docker compose up`).

### Commit Conventions

- Commits MUST follow Conventional Commits format (e.g., `feat:`, `fix:`, `docs:`, `chore:`).
- Each commit SHOULD be atomic and focused on a single logical change.

## Governance

These project instructions are the highest authority in the SDD process. All specifications, plans, and implementations MUST comply with the principles defined here.

- **Precedence**: Project instructions supersede all other practices, conventions, or defaults.
- **Compliance**: All code reviews and spec reviews MUST verify alignment with these principles. Violations are blocking.
- **Amendments**: Changes to project instructions MUST be documented with a version bump, rationale, and migration plan for affected artifacts. Use `/sddp-init` to amend.
- **Versioning**: Instructions follow semantic versioning — MAJOR for principle removals/redefinitions, MINOR for new principles or material expansions, PATCH for clarifications and wording fixes.
- **Complexity justification**: Any deviation from simplicity MUST be justified with a concrete technical rationale.

**Version**: 1.0.0 | **Last Amended**: 2026-03-01
