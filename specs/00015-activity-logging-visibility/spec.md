---
feature_branch: "00015-activity-logging-visibility"
created: "2026-06-11"
input: "E015"
spec_type: "product"
spec_maturity: "clarified"
epic_id: "E015"
epic_sources: "{PRD:CAP-010}"
product_document: "specs/prd.md"
---

# Feature Specification: Activity Logging & Visibility

**Feature Branch**: `00015-activity-logging-visibility`  
**Created**: 2026-06-11  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: clarified  
**Epic ID**: E015  
**Epic Sources**: {PRD:CAP-010}  
**Product Document**: specs/prd.md

## Problem Statement

When firmware checks or notifications fail in an unattended system, operators lack the visibility to diagnose issues without SSHing into the host and parsing raw container logs. This makes troubleshooting difficult and erodes trust in the automated update loop. Storing activity events in a structured, size-bounded database table and presenting them in a dedicated UI page ensures operators can easily track success and debug failures.

## Scope

### Included

- **SQLite Database Persistence**: A dedicated `activity_log` table storing timestamp, level, category, message, device ID, module name, and traceback.
- **Size-Bounded Retention**: Automated pruning mechanism that limits the log size to a maximum of 1000 entries (retains the latest 1000).
- **Backend API**: A `GET /api/v1/activity` endpoint with pagination and filtering by level, category, and device ID.
- **Frontend Logs Viewer**: A dedicated "Logs" page in the navigation containing a log table, filter controls, pagination, and a traceback inspection panel.
- **Automatic Event Recording**: Auto-logging check successes/failures and notification dispatches.

### Excluded

- **Log Export Functionality** — Downloading logs (e.g., as CSV or JSON) is deferred to future work.
- **Log Level Configuration** — Changing log levels via the UI is out of scope; system uses default severities (INFO, WARNING, ERROR).
- **Log Deletion / Purging via UI** — Manual pruning or deleting logs via the UI is not supported (handled automatically by size bounding).

### Edge Cases & Boundaries

- **Database Performance**: Pruning large traceback messages must not block concurrent read or write operations on SQLite.
- **Detached Devices**: If a device is deleted, activity logs associated with its `device_id` should have their `device_id` set to NULL or be cascades-deleted. We will set `device_id` to NULL on delete or cascade delete. Let's cascade delete the logs to maintain a clean database.
- **Concurrent Check Events**: Multiple scheduled checks running in parallel must serialize writes to the log database cleanly without producing SQLite lock errors.

## User Scenarios & Testing

### User Story 1 - View Activity Log Table (Priority: P1)

As an operator, I want to view a table of recent checks, notification dispatches, and system events so that I can verify the system is running correctly.

**Why this priority**: Essential requirement for basic visibility into the system's runtime state.

**Independent Test**: Navigate to the Logs page in the UI and verify that check executions and notifications are displayed in a paginated list with correct timestamps.

**Acceptance Scenarios**:

1. **Given** that several activity logs have been generated, **When** I navigate to the "Logs" page, **Then** I see a table displaying the timestamp, level (e.g., INFO, ERROR), category, and message for each log entry.
2. **Given** a log list with more than 50 entries, **When** I scroll to the bottom of the table or click next, **Then** I can paginate to see older entries.

### User Story 2 - Filter Activity Logs (Priority: P1)

As an operator, I want to filter logs by severity level, event category, or device, so that I can isolate relevant events quickly.

**Why this priority**: Necessary to quickly diagnose specific failure points or narrow down issues to a particular device or module.

**Independent Test**: Select "ERROR" from the level filter and verify that only ERROR level entries are displayed.

**Acceptance Scenarios**:

1. **Given** a mixed list of INFO and ERROR logs, **When** I select the "ERROR" filter in the Filter Bar, **Then** only log entries with the level ERROR are shown in the table.
2. **Given** logs from different categories, **When** I filter by category "notification", **Then** only notification dispatch logs are shown.

### User Story 3 - View Detailed Exception Tracebacks (Priority: P2)

As an operator, I want to view the full traceback or error details of failed checks or notifications so that I can troubleshoot the underlying issue.

**Why this priority**: High value for debugging, but secondary to seeing that a failure occurred.

**Independent Test**: Trigger a failing check (e.g., a mock failure), find the resulting log entry in the table, click to open it, and inspect the traceback in the panel.

**Acceptance Scenarios**:

1. **Given** an activity log entry with an error level and a non-empty traceback, **When** I click on the log row or a "View Details" button, **Then** a panel or modal opens displaying the formatted traceback.
2. **Given** a log entry with no traceback, **When** I click on it, **Then** no traceback panel is shown or the details indicate no traceback is available.

### User Story 4 - Size-Bounded Log Retention (Priority: P2)

As an operator, I want the system to manage its own storage footprint so that the database does not grow indefinitely.

**Why this priority**: Key operational hygiene for set-and-forget reliability, but invisible to the end user.

**Independent Test**: Seed the database with 1050 log entries and verify that the database contains exactly 1000 entries, retaining the latest ones.

**Acceptance Scenarios**:

1. **Given** 1000 existing activity log entries, **When** a new activity log entry is inserted, **Then** the oldest entry is pruned, and the database row count remains exactly 1000.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST create an `activity_log` table storing logs with timestamp, level, category, message, device ID (optional), module name (optional), and traceback (optional).
- **FR-002**: The system MUST insert a new activity log entry on every device check attempt, recording whether the check succeeded or failed.
- **FR-003**: The system MUST insert a new activity log entry on every notification dispatch attempt, recording success or failure.
- **FR-004**: The system MUST query and list logs via `GET /api/v1/activity` with support for filtering by `level`, `category`, and `device_id`.
- **FR-005**: The endpoint `GET /api/v1/activity` MUST support paging using `limit` and `offset` query parameters.
- **FR-006**: The system MUST enforce a rolling log retention policy of exactly 1000 maximum entries in the database.
- **FR-007**: The frontend UI MUST include a "Logs" menu item in the navigation bar.
- **FR-008**: The Logs page MUST present a paginated table showing log details with colored badges for levels (e.g., red for ERROR, orange for WARNING, blue/gray for INFO).
- **FR-009**: The Logs page MUST provide controls to filter the list by level, category, and device.
- **FR-010**: The Logs page MUST display a traceback drawer or dialog for entries containing a traceback.

### Key Entities

- **ActivityLogEntry**: Represents a single logged activity event.
  - `id` (integer, auto-incrementing primary key)
  - `timestamp` (datetime, defaults to current time, index)
  - `level` (string: `INFO`, `WARNING`, `ERROR`, index)
  - `category` (string: `check`, `notification`, `system`, index)
  - `message` (text)
  - `device_id` (integer, nullable foreign key to `devices`, cascades on delete)
  - `module_name` (string, nullable)
  - `traceback` (text, nullable)

## Assumptions & Risks

### Assumptions

- The operator accesses the UI from a device that supports modern React web features.
- The volume of check logs matches the check frequency; for typical setups (e.g., checks every 1–24 hours), 1000 logs covers months of history.
- Performance impact of database writes is negligible since checks and notifications run asynchronously on background threads.

### Risks

- **[Risk 1]** *(likelihood: low, impact: medium)*: High-frequency checking leads to lock contention on SQLite.
  - *Mitigation*: Ensure connections are managed properly and writes are brief, leveraging SQLite's WAL mode (which is standard for FastAPI + aiosqlite setup).
- **[Risk 2]** *(likelihood: low, impact: low)*: Log pruning query runs slowly on write operations when table gets large.
  - *Mitigation*: Add database index on `timestamp` (or `id`) to ensure the pruning query can quickly identify and delete old rows.

## Implementation Signals

- `MIGRATION` — Add `0006_activity_log.sql` creating the `activity_log` table with indices.
- `NEW-ENTITY` — Create an `ActivityLog` Pydantic model for backend type safety.
- `NEW-API` — Implement `/api/v1/activity` router with listing, pagination, and filtering.
- `NEW-UI` — Create `frontend/src/components/logs/LogsPage.tsx` and register the route in the SPA navigation shell.
- `NEW-WORKER` — Add auto-logging calls within the check execution and notification dispatch workers/services.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: The Logs page renders a list of logs fetched from the API with correct timestamp, level, category, and message fields.
- **SC-002** [US2]: Selecting an ERROR filter renders only entries with `level = 'ERROR'`.
- **SC-003** [US3]: Clicking an error log containing a traceback displays a formatted traceback in a drawer/dialog.
- **SC-004** [US4]: The `activity_log` table never exceeds 1000 rows, even after inserting more than 1000 entries.

## Glossary

| Term | Definition |
|------|------------|
| Activity Log | Structured list of events (checks, notifications, system restarts) kept in the database. |
| Rolling Retention | System of keeping only a fixed amount of recent history, purging older items automatically. |
| Traceback | The stack trace of an exception or error, used for debugging code failures. |

## Clarifications

### Session 2026-06-11

- Q: What is the database table name for activity logs? -> A: activity_log (chosen to align with existing table names like notification_channels).
- Q: What is the rolling retention limit? -> A: 1000 (standard limit that balances diagnostic utility and database file size).

## Stress-Test Findings

### Session 2026-06-11

- **STF-001**: SQLite database lock contention during concurrent write operations from parallel scheduled checks.
  - Category: concurrency
  - Severity: LOW
  - Scenario: Multiple background check threads complete simultaneously and attempt to insert into `activity_log` and prune in the same connection.
  - Resolution: The repository transaction handles connection reuse properly, using write-ahead logging (WAL) which allows concurrent reads and serializes writes without blocking.

## Compliance Check

### Instructions Check Report
**Target**: spec.md
**Status**: PASS

| Principle | Verdict | Notes |
|-----------|---------|-------|
| I. Honest Failure | PASS | Activity logs track both check/notification success and failures, including full tracebacks. |
| II. Polite by Default | PASS | N/A for logging itself; logs are generated locally. |
| III. Data Ownership & Self-Containment | PASS | All log entries are persisted in the existing local SQLite database. |
| IV. Least-Privilege & Explicit Trust Boundary | PASS | No sandboxing claims are made; non-root execution is preserved. |
| V. Type Safety & Correctness-First | PASS | Log models and APIs will use static type checking (Pydantic, strict typing). |
| VI. Set-and-Forget Reliability | PASS | Size-bounded retention to exactly 1000 entries prevents disk exhaustion. |

