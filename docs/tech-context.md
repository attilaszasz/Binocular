# Tech Context: Binocular

## 1. Architectural Overview

Binocular is a **self-hosted, monolithic web application**. It is designed to be low-maintenance, resource-efficient, and easily deployable via Docker. The architecture separates the "Core System" (Inventory, Scheduling, Alerting) from the "Intelligence" (Extension Modules), allowing users to extend functionality without modifying the core application code.

### High-Level Components

1. **Web Server (Core):** Serves the API and the static frontend assets.

2. **Scheduler (Core):** A background thread that executes scraping jobs based on user-defined intervals.

3. **Extension Execution:** User-provided scripts are dynamically loaded and executed directly within the application context to fetch data.

4. **Database:** A local, file-based SQL database (SQLite).

## 2. Technology Stack Selection

### 2.1. Backend: Python (FastAPI)

* **Choice:** Python 3.11+ with **FastAPI**.

* **Justification:**

  * **Scraping Ecosystem:** Python is the undisputed leader in scraping (BeautifulSoup, Scrapy, Playwright), which is the core business logic of Binocular.

  * **Dynamic Loading:** Python makes it trivial to import user-dropped `.py` files as modules at runtime, which is essential for the "Extension Module" requirement.

  * **Performance:** FastAPI provides high-performance async I/O, allowing the system to check multiple manufacturer websites concurrently without blocking the UI.

### 2.2. Frontend: React + Tailwind CSS

* **Choice:** **React** (Vite build) with **Tailwind CSS**.

* **Justification:**

  * **Responsiveness:** React's component-based model ensures a fluid experience on mobile devices (a core requirement).

  * **State Management:** Handling real-time updates (e.g., a "Checking..." spinner or live log updates) is cleaner with React's state management than server-side templates.

  * **Tailwind:** Provides a modern, utility-first styling approach that makes dark mode (essential for homelabs) and mobile responsiveness easy to implement.

### 2.3. Data Storage: SQLite

* **Choice:** **SQLite**.

* **Justification:**

  * **Zero Configuration:** Meets the "Self-Contained" requirement. No external server (Postgres/MySQL) is needed.

  * **Single File:** The entire database is a single file (`binocular.db`), making backups as simple as copying a file.

  * **Concurrency:** SQLite's WAL (Write-Ahead Logging) mode is sufficient for the expected concurrency of a single-user environment.

### 2.4. Task Scheduling: APScheduler

* **Choice:** **Advanced Python Scheduler (APScheduler)**.

* **Justification:**

  * Runs entirely within the Python process (no need for a separate Redis/Celery container).

  * Supports complex intervals (e.g., "Check Sony devices every 6 hours").

### 2.5. Notifications: Apprise

* **Choice:** **Apprise**.

* **Justification:**

  * A powerful Python library that abstracts notification services.

  * **Native Support:** Out-of-the-box support for **Email (SMTP)** and **Gotify** (as requested), plus virtually every other platform (Telegram, Discord, Slack, Pushover) for free.

## 3. Extension Module Design (The "Plug-in" System)

To fulfill the requirement for extensible, user-managed scripts, we will define a strict **Interface Contract**.

* **Format:** Single Python files (e.g., `sony_alpha.py`) placed in a `/modules` directory.

* **Structure:** Each module must define a standard class or function, for example:

  ```python
  def get_latest_version(url: str) -> str:
      # Logic to scrape URL and return version string
      pass
  ```

* **Execution & Stability:**
  * Modules are loaded via `importlib` and run in the main application process.
  * **No Sandboxing:** Extensions have full access to the environment. The user is responsible for vetting scripts to ensure they are safe.
  * **Error Handling:** The system will wrap execution in `try/catch` blocks solely to prevent script errors (e.g., syntax errors, network timeouts) from crashing the main application loop.

## 4. Deployment Strategy

The application will likely be distributed as a single Docker image `binocular/app:latest`.

**Container Structure:**

* **Base:** `python:3.11-slim`

* **Process:**

  * Backend runs on port `8000` (Uvicorn).

  * Frontend static files are served by FastAPI directly via `StaticFiles`, ensuring a single-port exposure for the user.

* **Volumes:**

  * `/app/data`: Stores `binocular.db`.

  * `/app/modules`: Stores user-added python extension scripts.



Binocular: Component Decomposition

This document breaks down the Binocular application into discrete features for specification-driven development. Each component represents a distinct body of work with clear boundaries.

Epic 1: Core Foundation & Inventory (The Engine)

This is the minimum viable base. The frontend and backend can be developed in parallel if an API spec (e.g., OpenAPI) is defined first.

Feature 1.1: Database Schema & Models

SQLite setup.

Tables: DeviceType, Device, AppConfig.

Feature 1.2: Inventory API (CRUD)

FastAPI endpoints to Add, Read, Update, and Delete devices and device types.

Includes the "one-click confirmation" endpoint to sync current_version with latest_seen_version.

Feature 1.3: Core Frontend (UI/UX)

React + Tailwind scaffold (Responsive layout, Dark mode).

Main Dashboard: View grouped devices, showing local vs. web versions.

Forms to add/edit devices and map them to device types.

Epic 2: The Extension Engine (The Brains)

This is the core differentiator of Binocular. It defines how custom code interacts with the system.

Feature 2.1: Module Interface Contract & Mock Execution

Define the exact Python function signature every module must implement (e.g., def check_firmware(url) -> dict).

Create a Mock/Dummy module and the backend logic to execute it and return dummy version data.

Feature 2.2: Module Validation Engine

Logic to inspect an uploaded .py file (using Python's ast or inspect modules) to ensure it contains the required functions before saving it.

Feature 2.3: Module Management (API & UI)

Backend endpoints to upload .py files, list installed modules, and delete them.

Frontend UI to manage the module library (Upload area, Active/Inactive status).

Epic 3: Automation & Task Management (The Heartbeat)

Makes the system operate autonomously.

Feature 3.1: Task Scheduler

Integrate APScheduler.

Logic to dynamically create, update, or remove cron/interval jobs based on the DeviceType check frequency settings.

Feature 3.2: Manual Trigger System

Backend logic to trigger an immediate, out-of-band execution for a single device or a bulk execution for all devices.

Frontend buttons ("Check Now", "Check All") with loading states (spinners) and real-time result polling.

Epic 4: Visibility & Notifications (The Voice)

Keeping the user informed and tracking system health.

Feature 4.1: Activity Logging System

Backend logic to record system events (e.g., "Check started", "Version mismatch found", "Scrape failed").

Rolling log implementation (limiting to X lines/days to prevent DB bloat).

Frontend log viewer component.

Feature 4.2: Alerting Engine (Apprise Integration)

Integrate the Python apprise library.

Settings UI to configure Email (SMTP) and Gotify credentials.

Logic to dispatch a notification when latest_seen_version > current_version.

Epic 5: Official Scraper Modules (Parallel Track)

These can be developed entirely in parallel with Epics 1-4 once the "Module Interface Contract" (Feature 2.1) is locked.

Feature 5.1: Sony Alpha Module

Python script to scrape alphauniverse.com/firmware/.

Handles pagination or dynamic loading specific to Sony's site.

Feature 5.2: Panasonic Lumix Module

Python script to scrape the Panasonic global support portal.

Epic 6: Developer Experience & Ops (The Wrapper)

Making it easy to deploy and easy to extend.

Feature 6.1: Deployment & Security

Dockerfile creation (multi-stage build, combining React static build with FastAPI).

Volume mapping setup for /data and /modules.

Optional Basic Auth middleware for the UI.

Feature 6.2: Module Dev Kit

A standalone CLI script (e.g., test_module.py) so users can test their scrapers locally without spinning up the whole Binocular UI.

AI System Prompt / Guidelines: A predefined markdown file (e.g., writing-modules-for-ai.md) that users can feed to ChatGPT/Claude, instructing the AI on exactly how to write a valid Binocular module.


Quality Checklists for Binocular

1. The "Polite Scraper" Checklist

Crucial for the longevity of the project. Aggressive scraping gets IPs banned and gives open-source tools a bad reputation.

[ ] Robots.txt Compliance: Does the scraper check robots.txt before fetching?

[ ] User-Agent Rotation: Are requests identified accurately? (e.g., Binocular/1.0 (+https://github.com/your/repo) rather than a fake Chrome string, or properly rotating if necessary).

[ ] Rate Limiting (Throttling): Is there a hard delay between requests to the same domain (e.g., sleep(2))?

[ ] Error Handling & Backoff: Does the system use "Exponential Backoff" when it hits 429 (Too Many Requests) or 5xx errors?

[ ] Bandwidth Efficiency: Does the scraper use HEAD requests where possible to check Last-Modified headers before downloading full pages?

2. The "Self-Hosted" UX Checklist

Homelab users expect "set and forget" reliability and privacy.

[ ] Zero-Config Startup: Can the container start with zero environment variables and still function (using sensible defaults)?

[ ] Data Persistence: Are all database files and logs stored in a single, clearly defined /data volume?

[ ] Container User Permissions: Does the Docker container run as a non-root user (PUID/PGID support)?

[ ] Logs: Are logs output to stdout/stderr (for Docker logs) and optionally a rolling file?

[ ] Offline-First UI: Does the UI handle losing connection to the backend gracefully (e.g., retry indicators instead of white screens)?

[ ] Dark Mode: Is Dark Mode supported? (A near-mandatory requirement for self-hosted tools).

3. Docker & Security Checklist

Even on private networks, basic security hygiene is required.

[ ] Image Size: Is the Docker image optimized? (e.g., using python:3.11-slim or alpine base).

[ ] Dependency Pinning: Are Python dependencies pinned with hashes (e.g., using poetry.lock or requirements.txt with versions) to prevent build breaks?

[ ] Secrets Management: Does the app support loading sensitive config (if any) via _FILE environment variables (Docker Secrets pattern)?

[ ] No Hardcoded Creds: Are there any hardcoded passwords or API keys in the source code?

[ ] Healthcheck: Does the Dockerfile include a HEALTHCHECK instruction?

4. Python/FastAPI Code Quality

[ ] Type Hinting: Is the codebase fully typed? (Checked via mypy).

[ ] Async Correctness: Are scraping operations correctly await-ed to prevent blocking the main event loop?

[ ] Pydantic Validation: Are all API inputs and config files validated using Pydantic models?

[ ] Structured Logging: Do logs contain context (e.g., device_id, module_name) rather than just text messages?

5. Open Source Launch Checklist

[ ] License: Is a valid open-source license (e.g., MIT, GPL) included?

[ ] README: Does the README include a "Quick Start" command (e.g., docker run ...)?

[ ] Contributing Guide: Is there a CONTRIBUTING.md explaining how to write a new Extension Module?

[ ] Screenshots: Does the repo include high-quality screenshots/GIFs of the UI?

## Project Context Baseline Updates

*Managed section — rewritten by SDD planning agents. Do not edit manually.*

### Database Configuration Baseline

- **Engine**: SQLite (single file: `/app/data/binocular.db`)
- **Journal Mode**: WAL (Write-Ahead Logging) — enabled per-connection via `PRAGMA journal_mode = WAL`
- **Contention Handling**: `PRAGMA busy_timeout = 5000` (5-second wait on lock)
- **Foreign Keys**: `PRAGMA foreign_keys = ON` — must be set per-connection (SQLite default is OFF)
- **Concurrency Model**: Single-user, single-instance; WAL allows concurrent reads during scheduler writes
- **Migration Strategy**: Custom lightweight runner with numbered SQL files (`001_initial.sql`, `002_*.sql`, …) and a `schema_version` tracking table; auto-applied on startup

### Data Access Pattern

- **No ORM**: Raw SQL via `aiosqlite` with Pydantic models for serialization/deserialization
- **Repository Pattern**: One repository class per entity providing typed async CRUD methods
- **Pydantic Models**: One model file per entity in `backend/src/models/`; AppConfig uses `BaseSettings` pattern with typed defaults
- **Version Comparison**: Semver parsing (`packaging.version.Version`) with string inequality fallback — pure function, not DB-level

### Repository Layout

- **Structure**: Web application layout — `backend/` (Python/FastAPI) + `frontend/` (React/Vite/Tailwind)
- **Backend paths**: `backend/src/db/` (connection, migrations), `backend/src/models/`, `backend/src/repositories/`, `backend/src/utils/`, `backend/src/api/`, `backend/src/services/`
- **Test paths**: `backend/tests/` with temp-file SQLite fixtures per test; `backend/tests/test_api/` for integration tests via `httpx.AsyncClient`

### API Architecture

- **Routing Pattern**: Hybrid — nested routes for resource creation under a parent (`POST /api/v1/device-types/{id}/devices`), flat routes for querying and individual operations (`GET/PATCH/DELETE /api/v1/devices/{id}`)
- **Service Layer**: Thin service classes in `backend/src/services/` wrap repository calls and translate low-level exceptions into typed domain exceptions
- **Exception Handling**: Domain exceptions (`NotFoundError`, `DuplicateNameError`, `CascadeBlockedError`, `NoLatestVersionError`) caught by registered FastAPI exception handlers and mapped to the error envelope format
- **State Transitions**: Custom action endpoints (`POST /…/confirm`) for operations that are state transitions, not generic field updates — following Google API Design Guide custom methods pattern
- **API Versioning**: All routes prefixed with `/api/v1/`

### API Design Standards

- **Error Envelope**: All error responses use a consistent structure: human-readable `detail` + machine-readable `error_code` + optional `field` identifier
- **Error Codes**: Fixed vocabulary — `DUPLICATE_NAME`, `NOT_FOUND`, `VALIDATION_ERROR`, `CASCADE_BLOCKED`, `NO_LATEST_VERSION`, `INTERNAL_ERROR`
- **Mutation Responses**: All create/update endpoints return the complete updated resource in the response body (no follow-up GET needed)
- **Resource Shape**: All resource representations include `id`, `created_at`, `updated_at` in ISO 8601 format
- **Input Validation**: Validated at API boundary via Pydantic — non-empty trimmed names (max 200 chars), syntactically valid URLs, positive numeric values
- **Cascade Safety**: Destructive operations on parent resources require explicit confirmation (`?confirm_cascade=true`) when child records exist
- **Idempotent Actions**: State-transition endpoints (e.g., confirm update) are idempotent — safe to retry or double-invoke
- **OpenAPI Documentation**: Auto-generated interactive docs grouped by resource type, browsable at `/docs`
- **Response Enrichment**: API responses include derived fields (e.g., `status`, `device_count`, `device_type_name`) computed at query time, not stored

### Developer Experience

- **Entry Point**: `backend/src/main.py` — FastAPI app factory with Uvicorn
- **F5 Debugging**: `.vscode/launch.json` with `debugpy` launching Uvicorn with `--reload`
- **DB Path Config**: `BINOCULAR_DB_PATH` environment variable, defaults to `./data/binocular.db` locally, `/app/data/binocular.db` in Docker

### Cross-Cutting Standards

- **Structured Logging**: `structlog` for all backend components (migration runner, connection lifecycle, repository errors, API requests)
- **Dependency Pinning**: Exact versions in lock file (`poetry.lock` or `requirements.txt` with hashes) — required by project instructions
- **Type Safety**: All Python code must pass `mypy --strict`; all API payloads validated through Pydantic models
- **Testing**: `pytest` + `pytest-asyncio` for async tests; `httpx.AsyncClient` for API integration tests; isolated temp-file SQLite per test

### Frontend Architecture

- **Stack**: React + Tailwind CSS, built with Vite; served as static files through the FastAPI backend (single-port)
- **Application Shell**: Fixed sidebar navigation on desktop (≥ 768px), off-canvas hamburger menu on mobile (< 768px); sticky top header with page title and theme toggle
- **Navigation**: Client-side routing (SPA) — four tabs: Inventory, Activity Logs, Modules, Settings
- **Dark Mode**: System preference detection (`prefers-color-scheme`) with manual toggle; choice persisted in `localStorage`; applied before first paint to prevent theme flash
- **Placeholder Pattern**: Non-implemented tabs render styled placeholder views describing upcoming functionality — prevents dead-end navigation while features are delivered incrementally

### Frontend-Backend Integration

- **Data Flow**: Frontend is a thin API consumer; backend API is the single source of truth for all data (no local DB, no offline cache in V1)
- **Error Handling**: Backend error conditions (duplicate name, not found, validation failure, cascade conflict, missing version data) are mapped to user-friendly inline messages at the UI layer
- **Validation**: Client-side validation mirrors backend rules (non-empty trimmed names ≤ 200 chars, valid URLs ≤ 2048 chars, notes ≤ 2000 chars) for immediate feedback; backend remains authoritative
- **Mutation Pattern**: All create/update/confirm actions use backend responses to update UI state in place (no follow-up GET needed)
- **Tri-State Status**: Device update status (update available / up to date / never checked) is derived from backend data, displayed with distinct visual treatments (color + icon + text label)