# Software Architecture Document: Binocular

> Date: 2026-05-31 | Status: Draft

## Purpose and Scope

Binocular is a self-hosted, single-user web application that automates firmware-update discovery for high-value **offline** devices (cameras, lenses, homelab hardware). It maintains a device inventory, runs user-managed extension modules that scrape manufacturer firmware pages on a schedule, compares detected versions against the user's recorded version, and dispatches notifications when an update is available.

The system boundary is a single deployable application running on a private, trusted LAN: one container exposing one HTTP port, persisting all state to one local data volume, with no external database, broker, account system, or cloud dependency. The architecture separates a stable **Core System** (inventory, scheduling, alerting, API, UI) from pluggable **Intelligence** (user-authored extension modules), so users extend device coverage without modifying core code.

## Technical Context

**Language/Version**: Python 3.13+ (backend); TypeScript 5.x / React 18 (frontend)  
**Primary Dependencies**: FastAPI, Uvicorn, aiosqlite, Pydantic, APScheduler, Apprise, httpx, structlog (backend); React, Vite, Tailwind CSS, React Router, TanStack Query, React Hook Form (frontend)<br>
**Storage**: SQLite single file (`binocular.db`) via aiosqlite with raw SQL and a numbered-migration runner; no ORM, no external DB server  
**Testing**: pytest + pytest-asyncio, httpx.AsyncClient (backend); Vitest + React Testing Library, one Playwright smoke test (frontend); golden/fixture-based module correctness tests<br>
**Target Platform**: Linux Docker container (`python:3.13-slim`), single port 8000; also runnable directly on a host with Python/Node runtimes  
**Project Type**: Web application — Python/FastAPI backend + React SPA, single-process monolith<br>
**Performance Goals**: Responsive UI on mobile and desktop; concurrent multi-site checks via async I/O without blocking the UI; modest homelab hardware footprint  
**Constraints**: Self-contained storage (no external DB), single-container/single-volume/zero-config/non-root operability, trusted-LAN single-user, no telemetry, polite-scraping mandatory, unsandboxed extension execution  
**Scale/Scope**: Single user, single instance; inventory of roughly 5–50+ devices; one background scheduler concurrent with UI reads

## System Scope and Context

Primary actor is the **self-hosting operator** (also the sole user). External systems are **manufacturer firmware pages** (scrape targets), and the **notification channels** Email/SMTP and Gotify. Module authors interact indirectly by supplying extension modules; there is no external account provider or cloud backend.

### C4 System Context

```mermaid
C4Context
    title System Context
    Person(user, "Operator", "Single user")
    System(binocular, "Binocular", "Firmware watcher")
    System_Ext(vendor, "Vendor Pages", "Firmware sources")
    System_Ext(email, "Email / SMTP", "Notification")
    System_Ext(gotify, "Gotify", "Notification")
    Rel(user, binocular, "Manages inventory")
    Rel(binocular, vendor, "Scrapes")
    Rel(binocular, email, "Notifies")
    Rel(binocular, gotify, "Notifies")
```

### C4 Container View

```mermaid
C4Container
    title Container View
    Person(user, "Operator")
    System_Boundary(binocular, "Binocular") {
        Container(spa, "Web UI", "React/Vite/Tailwind", "Responsive SPA")
        Container(api, "App Server", "Python/FastAPI", "API + static + scheduler")
        ContainerDb(db, "SQLite", "aiosqlite file", "Inventory and logs")
        Container(modules, "Modules Dir", "Volume of .py files", "Extension scripts")
    }
    System_Ext(vendor, "Vendor Pages", "Firmware sources")
    System_Ext(notify, "Email / Gotify", "Notification")
    Rel(user, spa, "Uses")
    Rel(spa, api, "Calls /api/v1")
    Rel(api, db, "Read/write")
    Rel(api, modules, "Loads")
    Rel(api, vendor, "Scrapes")
    Rel(api, notify, "Dispatches")
```

### C4 Component View

```mermaid
C4Component
    title Component View
    Container_Boundary(api, "App Server") {
        Component(routes, "API Routes", "FastAPI", "HTTP endpoints")
        Component(services, "Services", "Python", "Domain logic")
        Component(repos, "Repositories", "aiosqlite", "Data access")
        Component(scheduler, "Scheduler", "APScheduler", "Interval jobs")
        Component(engine, "Module Engine", "importlib", "Load + run")
        Component(httpcli, "Scrape Client", "httpx", "Polite HTTP")
        Component(notifier, "Notifier", "Apprise", "Dispatch")
    }
    ComponentDb(db, "SQLite", "file", "Inventory and logs")
    Rel(routes, services, "Calls")
    Rel(services, repos, "Uses")
    Rel(repos, db, "Read/write")
    Rel(scheduler, services, "Triggers checks")
    Rel(services, engine, "Runs modules")
    Rel(engine, httpcli, "Provides client")
    Rel(services, notifier, "Sends alerts")
```

## Solution Strategy and Architecture Style

- **Architecture Style**: Single-process modular monolith. Internally layered (API routes → services → repositories) with an explicit Core/Extension seam; runtime concerns (scheduler, module engine, scrape client, notifier) are in-process collaborators. See {SAD:ADR-0001}.
- **Source Code Location**: All project source code resides under `/src` within each application root — backend code under `backend/src/` and frontend code under `frontend/src/`.
- **Why this style fits**: It is the only style that satisfies the self-hosted, zero-infrastructure, single-volume, set-and-forget constraints while keeping the user-extensibility seam explicit. No inter-service networking, single port, trivial backup.
- **Alternatives considered**: Microservices/multi-container (rejected — disproportionate operational overhead for one user) and serverless/cloud (rejected — violates self-hosted, offline-LAN, data-ownership constraints). Captured in {SAD:ADR-0001}.

## Key Runtime Flows and Failure Paths

### Primary Flow — Scheduled Firmware Check

```mermaid
sequenceDiagram
    participant Sched as Scheduler
    participant Svc as Check Service
    participant Eng as Module Engine
    participant HTTP as Scrape Client
    participant Vendor as Vendor Page
    participant DB as SQLite
    participant Notify as Notifier
    Sched->>Svc: Trigger check (device type)
    Svc->>Eng: Run module(url, model, client)
    Eng->>HTTP: Fetch (robots, UA, rate limit)
    HTTP->>Vendor: GET firmware page
    Vendor-->>HTTP: HTML
    HTTP-->>Eng: Response
    Eng-->>Svc: latest_version
    Svc->>DB: Record result + log
    alt latest > current
        Svc->>Notify: Dispatch alert
    end
```

### Failure Paths

- Module raises / times out → caught by the per-invocation error boundary (Exception + SystemExit, timeout via `asyncio.wait_for`); recorded as a failed check in the activity log; other modules and the core process continue. See {SAD:ADR-0005}.
- Vendor page changed / unparseable → module returns no version or errors → surfaced as a visible "scrape failed" status with last-success timestamp; never a silent miss.
- Vendor returns 429/5xx → scrape client applies exponential backoff and per-domain rate limiting; persistent failure logged. See {SAD:ADR-0006}.
- Notification channel (SMTP/Gotify) failure → dispatch error logged in the activity log for operator visibility; check result still persisted.
- SQLite lock contention → `busy_timeout` (5s) wait; WAL allows concurrent reads during scheduler writes. See {SAD:ADR-0004}.
- Malformed module upload → rejected pre-save by two-phase validation (static AST + optional runtime proof) with structured per-phase results; never enters the modules directory.

## Deployment and Infrastructure View

```mermaid
flowchart TB
    subgraph Host["Self-hosted Host (Docker)"]
        subgraph Container["binocular/app (python:3.13-slim, non-root)"]
            Uvicorn["Uvicorn :8000<br>FastAPI + StaticFiles"]
            Sched["APScheduler<br>(in-process)"]
        end
        Vol1["Volume /app/data<br>binocular.db"]
        Vol2["Volume /app/modules<br>.py extensions"]
    end
    User["Operator browser<br>(LAN)"] --> Uvicorn
    Uvicorn --> Vol1
    Uvicorn --> Vol2
    Sched --> Uvicorn
    Uvicorn --> Vendor["Manufacturer pages"]
    Uvicorn --> Notify["Email / Gotify"]
```

A multi-stage Docker build compiles the Vite frontend in a Node stage and copies `dist/` into the Python image, which serves it via FastAPI `StaticFiles` with an SPA catch-all — single port, single image. Two volumes (`/app/data`, `/app/modules`) hold all mutable state. The container runs as a non-root user; a `HEALTHCHECK` validates liveness. See {SAD:ADR-0001}, {SAD:ADR-0003}.

## Cross-Cutting Concerns

### Security

Trusted-LAN, single-user model: no authentication by default, with optional basic-auth middleware for operators who expose the UI more broadly. Extension modules execute in-process with **no sandbox** — an explicit, accepted arbitrary-code-execution trust boundary mitigated (not eliminated) by non-root container execution and operator vetting. Secrets (SMTP/Gotify credentials) load via environment variables / `_FILE` Docker-secret patterns and are never hardcoded; raw SQL uses parameterized queries exclusively. See {SAD:ADR-0008}, {SAD:ADR-0005}.

### Reliability

Set-and-forget operation: the scheduler runs in-process and resumes on restart; missed windows are retried on the next interval rather than replayed. Per-module error boundaries and timeouts guarantee a broken module cannot crash the host. Honest-failure principle — failures surface as visible status with last-success timestamps, never silent misses. Scrape resilience handled via backoff/rate limiting at the HTTP client. See {SAD:ADR-0006}, {SAD:ADR-0007}.

### Observability

Structured logging via `structlog` across migration runner, connection lifecycle, repositories, API requests, and check execution, with contextual fields (`device_id`, `module_name`). Logs emit to stdout/stderr for `docker logs` and to a size-bounded rolling activity log persisted in SQLite and viewable in the UI. No external telemetry or analytics by design.

### Data Management

All state in SQLite (`binocular.db`) on the `/app/data` volume; backup = copy the file. Schema evolves via numbered SQL migrations (`001_initial.sql`, …) tracked by a `schema_version` table, auto-applied on startup. WAL journaling, `foreign_keys=ON`, and `busy_timeout` set per connection. The activity log is rolling/size-bounded to prevent unbounded growth. See {SAD:ADR-0004}.

### Integration Strategy

Outbound only: manufacturer firmware pages are scraped through the host-provided polite HTTP client (the single enforcement point for robots.txt, identifiable User-Agent, per-domain rate limiting, and backoff); notifications dispatch through Apprise (Email/SMTP and Gotify at launch, extensible to other channels). No inbound integrations or third-party APIs. See {SAD:ADR-0006}, {SAD:ADR-0007}.

### Operations

Distributed primarily as a Docker image (single port, two volumes, non-root, healthcheck), with a host-runtime fallback. Zero-config startup with sensible defaults; `BINOCULAR_DB_PATH` configurable. Dependencies pinned (lock file with hashes). A standalone module dev/test kit lets authors validate modules locally against the same polite HTTP client.

## Quality Attributes

| Attribute | Target | Measurement | Notes |
|-----------|--------|-------------|-------|
| Performance | Concurrent multi-site checks without UI blocking | Async I/O behavior under a multi-device check | I/O-bound workload; GIL not a constraint |
| Reliability | A broken/timed-out module never crashes the core; no silent missed updates | Fault-injection tests + fixture regression | Honest-failure principle |
| Security | No hardcoded secrets; non-root container; parameterized SQL | Static analysis + image inspection | ACE trust boundary accepted by design |
| Maintainability | mypy --strict (backend) and tsc strict (frontend) pass; pinned deps | CI type-check + lint (Ruff/Biome) | Single-maintainer OSS |
| Scalability | Single-user, single-instance workload served comfortably | Manual load on representative inventory | No horizontal scaling goal |
| Correctness | Detected latest == actual published latest; zero false positives/negatives for shipped modules | Golden/fixture-based module tests per release | No field telemetry available |

## Architecture Decision Records

Project-level architectural decisions are maintained as standalone MADR files under `specs/adrs/`. This table is a navigational index — full decision records live in the linked files.

| ADR ID | Title | Status | Date | Supersedes | File |
|--------|-------|--------|------|------------|------|
| ADR-0001 | Self-hosted single-container monolith with core/extension separation | accepted | 2026-05-31 | — | [0001-self-hosted-single-container-monolith-with-core-extension-separation.md](adrs/0001-self-hosted-single-container-monolith-with-core-extension-separation.md) |
| ADR-0002 | Python 3.13 and FastAPI for the backend | accepted | 2026-05-31 | — | [0002-python-311-and-fastapi-for-the-backend.md](adrs/0002-python-311-and-fastapi-for-the-backend.md) |
| ADR-0003 | React + Vite + Tailwind SPA served by FastAPI as static files | accepted | 2026-05-31 | — | [0003-react-vite-tailwind-spa-served-by-fastapi-as-static-files.md](adrs/0003-react-vite-tailwind-spa-served-by-fastapi-as-static-files.md) |
| ADR-0004 | SQLite file storage with aiosqlite and raw SQL (no ORM) | accepted | 2026-05-31 | — | [0004-sqlite-file-storage-with-aiosqlite-and-raw-sql-no-orm.md](adrs/0004-sqlite-file-storage-with-aiosqlite-and-raw-sql-no-orm.md) |
| ADR-0005 | Unsandboxed extension module engine with two-phase validation | accepted | 2026-05-31 | — | [0005-unsandboxed-extension-module-engine-with-two-phase-validation.md](adrs/0005-unsandboxed-extension-module-engine-with-two-phase-validation.md) |
| ADR-0006 | Centralized responsible-scraping HTTP client provided to modules | accepted | 2026-05-31 | — | [0006-centralized-responsible-scraping-http-client-provided-to-modules.md](adrs/0006-centralized-responsible-scraping-http-client-provided-to-modules.md) |
| ADR-0007 | In-process scheduling with APScheduler and Apprise notifications | accepted | 2026-05-31 | — | [0007-in-process-scheduling-with-apscheduler-and-apprise-notifications.md](adrs/0007-in-process-scheduling-with-apscheduler-and-apprise-notifications.md) |
| ADR-0008 | Trusted-LAN single-user security model with optional basic auth | accepted | 2026-05-31 | — | [0008-trusted-lan-single-user-security-model-with-optional-basic-auth.md](adrs/0008-trusted-lan-single-user-security-model-with-optional-basic-auth.md) |
| ADR-0009 | Module-Derived Device Type — Remove Standalone Device Type Field, Derive from Linked Module | accepted | 2026-06-04 | — | [0009-module-derived-device-type-remove-standalone-device-type-field.md](adrs/0009-module-derived-device-type-remove-standalone-device-type-field.md) |

<!-- Rows are managed by the ADR Author subagent. Do not embed full decision prose here. -->

## Risks, Assumptions, Constraints, and Open Questions

### Risks

- Unsandboxed extension modules run with host privileges — accepted ACE trust boundary; mitigated by non-root execution and operator vetting only.
- Manufacturer page changes break scrapers — highest operational risk; mitigated by visible failure status rather than silent misses.
- False negatives (missed updates) are invisible without telemetry — mitigated by fixture-based correctness validation at release.
- Notification-channel misconfiguration/outage goes unnoticed — mitigated by activity-log visibility.
- Scheduler shares the app process lifecycle — a restart pauses jobs until the next interval.

### Assumptions

- Deployment is on a private, trusted LAN with a single user/operator.
- A persistent volume is available for `/app/data` and `/app/modules`.
- The operator has or can configure SMTP and/or Gotify for notifications.
- Manufacturer firmware pages remain publicly reachable and scrapable.

### Constraints

- No external database server; all persistence in a single SQLite file.
- Single container, single port, single data volume, non-root, zero-config startup.
- No telemetry or central data collection.
- Modules must use the host-provided HTTP client for all outbound scraping.

### Open Questions

- Should optional basic auth be encouraged (or defaulted on) for users who reverse-proxy the UI beyond a trusted LAN?
- What default check frequency best balances timeliness against polite-scraping load?
- How should the product signal and recover when a shipped official module breaks due to a manufacturer page change?

## Project Context Baseline Updates

*Managed section — rewritten by SDD planning agents. Do not edit manually.*

- SQLite persistence uses an application-owned startup migration runner with append-only numbered SQL files, `schema_version` tracking, required connection pragmas, and a fatal pre-migration backup gate before pending migrations apply.
- Domain repositories use a shared raw-SQL repository base with parameter binding and allowlisted dynamic identifiers; no ORM abstraction is introduced.
- Responsible scraping uses a host-owned async `httpx` client wrapper with robots.txt checks, identifiable User-Agent defaults, per-origin pacing, bounded retry/backoff, and typed diagnostics for visible failures.
- Extension modules use a trusted in-process Python contract with importlib path loading, host ScrapeClient injection, per-invocation timeout/error boundaries, and two-phase static/runtime validation; validation is not a sandbox.
- Bundled official starter modules are automatically discovered, validated, and seeded/upserted into the SQLite database on application startup, enabling out-of-the-box tracking of devices without manual upload.
- Device type is derived from the linked extension module; the standalone DeviceType entity is removed from the domain model. Devices reference modules directly via `module_id` FK; device type grouping is computed at query time. See {SAD:ADR-0009}.

