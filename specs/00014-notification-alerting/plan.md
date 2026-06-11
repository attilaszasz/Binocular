# Implementation Plan: Notification & Alerting

**Branch**: `00014-notification-alerting` | **Date**: 2026-06-11 | **Spec**: [spec.md](spec.md)

## Summary

**Goal**: Deliver a robust notification system that dispatches firmware update alerts via Email/SMTP and Gotify (using Apprise), deduplicates alerts per device using `last_notified_version`, and provides a settings UI page for configuration and testing.  
**Approach**: Add database tables/columns via SQLite migrations, write a `NotifierService` using Apprise and Jinja2 templates, expose FastAPI settings and test routes, and build a configuration form in the React SPA.  
**Key Constraint**: Deduplication must strictly only send alerts when the detected version is newer than the recorded `last_notified_version`.

## Technical Context

**Language/Version**: Python 3.13 (backend); TypeScript 5.x / React 19 (frontend)  
**Primary Dependencies**: FastAPI, Apprise, Jinja2, aiosqlite, structlog (backend); React, TanStack Query, shadcn/ui primitives (frontend)  
**Storage**: SQLite (`binocular.db`) via aiosqlite  
**Testing**: pytest, pytest-asyncio (backend); Vitest (frontend)  
**Target Platform**: Linux Docker container / Local host runtime  
**Project Type**: web  
**Project Mode**: brownfield  
**Performance Goals**: Test dispatches complete/timeout within 5 seconds; async dispatch does not block check runner or web server main thread.  
**Constraints**: Apprise URL format; light-themed responsive HTML email styled with inline CSS.  
**Scale/Scope**: ~2 channels, ~10–50 devices.

## Instructions Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Instruction | Target Rule / Text | Satisfied By |
|-------------|--------------------|--------------|
| I. Honest Failure | Delivery failures logged to activity log | Failure exceptions caught during dispatch, logged to database activity log. |
| II. Polite by Default | Centralized HTTP client or library defaults | SMTP and Gotify outbound traffic managed through Apprise. |
| III. Data Ownership | SQLite persistent storage | Channel configurations and `last_notified_version` stored in SQLite db. |
| IV. Least Privilege | Non-root container compatibility | DB access and file changes compatible with standard non-root container paths. |
| V. Type Safety | Strict typing and tests | NotifierService fully typed; unit tests written for deduplication and rendering. |

## Architecture

```mermaid
C4Container
  title Container Diagram for Notification System
  
  Person(user, "Operator", "Self-hosting administrator")
  
  System_Boundary(binocular, "Binocular System") {
      Container(spa, "Web UI SPA", "React, TypeScript", "Interface for channel settings")
      Container(api, "FastAPI Application", "Python, FastAPI", "Serves API requests, runs update checks")
      Container(notifier, "Notifier Service", "Python, Apprise", "Renders HTML email, routes alerts to Apprise")
      ContainerDb(db, "SQLite Database", "aiosqlite file", "Stores inventory, schedules, channel configurations")
  }
  
  System_Ext(smtp, "SMTP Server", "Email gateway")
  System_Ext(gotify, "Gotify Server", "Push message endpoint")
  
  Rel(user, spa, "Configures channels, runs tests")
  Rel(spa, api, "PUT/GET /api/v1/notifications")
  Rel(api, db, "Reads/writes configurations & last_notified_version")
  Rel(api, notifier, "Invokes dispatch or runs tests")
  Rel(notifier, smtp, "Sends HTML email via SMTP")
  Rel(notifier, gotify, "Dispatches JSON payload to Apprise webhook")
```

## Architecture Decisions

| ID | Decision | Options Considered | Chosen | Rationale |
|----|----------|--------------------|--------|-----------|
| AD-001 | Persistent Storage of Channel Credentials | Flat JSON file / Database table | Database table `notification_channels` | Keeps all system configuration cohesive inside the SQLite database, easing backup and migration processes. |
| AD-002 | Email Template Choice | Markdown / HTML template via Jinja2 | HTML template via Jinja2 | Allows for a responsive, light-themed HTML design matching the application's UI aesthetics. |
| AD-003 | Where to trigger notifications | Trigger in SchedulerService / Trigger in CheckService.check_device | Trigger in CheckService.check_device | Ensures that both automated scheduled checks and manual on-demand checks successfully trigger update alerts. |

## Data Model Summary

| Entity | Key Fields | Relationships | Notes |
|--------|------------|---------------|-------|
| Device | `last_notified_version` (TEXT, Nullable) | Extended from existing schema | Nullable version string. Reset to NULL on manual update confirmation to allow next-detection notification. |
| NotificationChannel | `type` (TEXT, PK), `enabled` (INTEGER), `config` (TEXT) | None | `config` is a JSON-serialized string of credentials and settings. |

**Detail**: `specs/00014-notification-alerting/data-model.md`

## API Surface Summary

| Method | Path | Purpose | Auth | Req/Res Types |
|--------|------|---------|------|---------------|
| GET | `/api/v1/notifications` | Fetch configurations for SMTP/Gotify | Optional Basic | `None` / `List[ChannelResponse]` |
| PUT | `/api/v1/notifications` | Update configuration for a specific channel | Optional Basic | `ChannelUpdate` / `ChannelResponse` |
| POST | `/api/v1/notifications/test` | Run test dispatch for validation | Optional Basic | `TestChannelRequest` / `TestChannelResponse` |

**Detail**: `specs/00014-notification-alerting/contracts/api.md`

## Testing Strategy

| Tier | Tool | Scope | Mock Boundary | Install |
|------|------|-------|---------------|---------|
| Unit | pytest | Test Jinja2 HTML rendering, NotifierService URL construction, and version compare deduplication logic | Mock Apprise send function | `configured` |
| Integration | pytest | Test DB Migrations, Repository CRUD operations, and `/api/v1/notifications` REST API endpoints | Mock SMTP server and Gotify HTTP requests | `configured` |
| Security | Ruff / mypy | Static typing analysis & code security guidelines | — | `configured` |
| Coverage | pytest-cov | Check coverage target (80%) for new notification service modules | — | `configured` |

## Error Handling Strategy

| Error Category | Pattern | Response | Retry |
|----------------|---------|----------|-------|
| API Validation | FastAPI Pydantic parsing | 422 Unprocessable Entity with error locations | No |
| Delivery Failures | Log & catch within notifier boundary | Log to database activity log; return failure message in API test route | No (rely on next check run) |
| DB Constraint | Unique key violation | 400 Bad Request if trying to insert duplicate channel type | No |

## Integration Points

| Spec Reference | System/Service | Technical Approach | Contract |
|----------------|----------------|--------------------|----------|
| FR-003 | Apprise | Interface with `apprise.Apprise` using parsed SMTP/Gotify settings | Apprise API URL schema (`mailto://`, `gotify://`) |
| FR-004 | Jinja2 | Render HTML using static mail template and standard Jinja2 context variables | HTML Context dict |

## Risk Mitigation

| Risk (from spec) | Likelihood | Impact | Mitigation | Owner |
|-------------------|------------|--------|------------|-------|
| SMTP Blockages / Failures | Medium | High | Expose error details in settings UI via test route. Catch exceptions, write detailed error logs in activity log. | Notifier / API |
| Gotify API Errors / Token Expiry | Low | Medium | Return failure responses in test dispatches. Log network failures during scheduled runs. | Notifier / API |

## Requirement Coverage Map

| Req ID | Component(s) | File Path(s) | Notes |
|--------|--------------|--------------|-------|
| FR-001 | API endpoints | `backend/src/binocular/routes/notifications.py` | Exposes GET/PUT for configs. |
| FR-002 | DB Repository / Migration | `backend/src/binocular/db/migrations/0005_notifications.sql`, `backend/src/binocular/db/notifications_repository.py` | Create table, load and save. |
| FR-003 | NotifierService | `backend/src/binocular/services/notifier.py` | Apprise orchestration wrapper. |
| FR-004 | EmailRenderer | `backend/src/binocular/services/email_renderer.py`, `backend/src/binocular/templates/email.html` | Jinja2 responsive HTML template. |
| FR-005 | CheckService | `backend/src/binocular/services/checks.py` | Deduplicates before sending. |
| FR-006 | CheckService / DB | `backend/src/binocular/services/checks.py` | Saves `last_notified_version` on successful dispatch. |
| FR-007 | API test route | `backend/src/binocular/routes/notifications.py` | Endpoint to test config. |
| FR-008 | CheckService | `backend/src/binocular/services/checks.py` | Writes failures to activity log. |

## Project Structure

### Source Code

```text
~ backend/src/binocular/
  ~ db/
    ~ migrations/
      + 0005_notifications.sql
    + notifications_repository.py
  ~ routes/
    ~ __init__.py
    + notifications.py
  ~ services/
    ~ __init__.py
    ~ checks.py
    + notifier.py
    + email_renderer.py
  + templates/
    + email.html
~ frontend/src/
  ~ pages/
    ~ settings.tsx
```

**Patterns to reuse**: Standard router pattern, parameterized SQL repositories (e.g., using `sqlite3`/`aiosqlite` connection directly as seen in `devices`), FastAPI path dependencies.  
**Tests to extend**: Add `backend/tests/test_notifications.py` for repository, service, and API endpoint coverage. Extend device tests to check `last_notified_version` column.  
**Naming conventions**: Snake case for Python service files, camelCase for TSX components.

## Implementation Hints

- **[HINT-001]** Apprise URLs: For SMTP, use `mailto://user:pass@host:port?to=to_email&from=from_email&secure=true` (or configure parameters specifically based on TLS/SSL). For Gotify, use `gotify://host/token`.
- **[HINT-002]** Password Masking: Ensure sensitive keys like `smtp_pass` and `app_token` are masked with `********` when read by GET endpoints, but keep them editable/updatable.
- **[HINT-003]** DB Repository: Return empty dicts if configurations do not exist, ensuring frontend settings page starts with clean default fields.
- **[HINT-004]** Version Compare Fallback: Ensure semantic version comparison handles non-standard characters gracefully when deciding if `latest_version > last_notified_version`.
- **[HINT-005]** SMTP Port Types: 465 is typically implicit SSL, whereas 587 uses explicit STARTTLS. Ensure Apprise config URL maps parameters correctly depending on the TLS configuration saved.
