---
feature_branch: "00018-activity-logging-visibility"
created: "2026-06-01"
input: "E014 Activity Logging & Visibility — bounded activity log + in-UI viewer"
spec_type: "product"
spec_maturity: "clarified"
epic_id: "E014"
epic_sources: "{PRD:CAP-010}"
---

# Feature Specification: Activity Logging & Visibility

**Feature Branch**: `00018-activity-logging-visibility`  
**Created**: 2026-06-01  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: clarified  
**Epic ID**: E014  
**Epic Sources**: {PRD:CAP-010}  
**Product Document**: specs/prd.md

## Problem Statement

When Binocular runs scheduled or manual firmware checks, scrapes third-party manufacturer pages, or dispatches outbound SMTP and Gotify alerts, the entire process runs in the background. If a manufacturer support portal changes its HTML layout or a network failure occurs, the operator has no visibility into what broke or why unless they manually inspect container logs on the host. To fulfill the "honest failure" product principle, the application needs a self-contained, rolling activity log persisted in SQLite and viewable in the UI, surfacing exactly what is happening under the hood.

## Scope

### Included

- **Activity Database Persistence**: Automatically record a structured database entry in a new `activity_log` SQLite table whenever a device check starts, succeeds, or fails, or when a notification dispatch is attempted.
- **Detailed Diagnostics**: Capture rich metadata including timestamps, event types (`check`, `notification`), outcome status (`success`, `failed`), and detailed error messages/stack trace tracebacks.
- **Robust Rolling Retention**: Implement an automated size-bounding pruning mechanism that keeps the database database-friendly by retaining at most the 1,000 most recent records.
- **JSON REST API Endpoint**: Expose `GET /api/v1/activity` with support for optional query filtering (e.g. by status, type) and sorting in reverse chronological order.
- **In-UI Logs Viewer**: Build a dedicated Activity Log route/page in the React SPA featuring clean, responsive tables, badge-highlighted statuses, and expandable detail cards for diagnostic tracebacks.
- **De-coupled Asset Survival**: Preserve original plain-text device and module names inside log rows so that history remains accurate and readable even if the underlying device or module is deleted from the inventory.

### Excluded

- **Log Export Options**: In-UI download formats (e.g. CSV, JSON exports) are out of scope.
- **Advanced Query Builder**: Complex boolean logical queries or Elasticsearch-style full-text searches.
- **Real-Time Push Streams**: WebSockets log streaming is excluded; the UI will use standard state-driven page loading or manual refetching.

### Edge Cases & Boundaries

- **Inventory Deletion**: If a user deletes a device or module, foreign key references should not cascade-delete logs or result in empty strings. The log records must store the snapshot names at the time of the event.
- **High Check Concurrency**: Concurrent background checks could attempt parallel writes to the activity log. Thread safety must be managed via standard SQLite WAL connection and busy timeout protocols.
- **Massive Stack Traces**: Truncate exceptionally long traceback strings before insertion to protect SQLite volume constraints.

## User Scenarios & Testing

### User Story 1 - View Check & Alert History (Priority: P1)

As an operator, I want to see a unified history of checks and notifications in the UI so that I have a reliable record of what has run.

**Why this priority**: Core value proposition — operator visibility and reassurance that unattended operations are successfully working.

**Independent Test**: Navigate to the Activity Log view in the browser, check for past events, and verify that columns display timestamps, event types, device names, and status badges correctly.

**Acceptance Scenarios**:

1. **Given** several manual and scheduled checks have run, **When** the operator opens the Activity Log page, **Then** the list shows all checks in reverse chronological order.
2. **Given** a successful notification was dispatched, **When** the operator views the activity list, **Then** a row representing the notification exists with a green "Success" badge.

### User Story 2 - Diagnose Outbound Scrape & Alert Failures (Priority: P1)

As an operator, I want to expand failed activity rows to inspect their detailed traceback or error message so that I can troubleshoot broken modules or invalid credentials.

**Why this priority**: Crucial debugging utility — enables operators to quickly understand why a check or notification failed and fix it without host/SSH access.

**Independent Test**: Trigger a failed check (e.g., using a mock module designed to error), see the failed row in the UI list, expand it, and verify that the full error traceback is readable.

**Acceptance Scenarios**:

1. **Given** a check failed due to a scrape connection error, **When** the operator opens the Activity Log and expands the failed row, **Then** a structured details card displays the HTTP error and traceback.
2. **Given** an invalid SMTP password, **When** a notification fails, **Then** the notification activity log records a status of "failed" and captures the SMTP auth failure message.

### User Story 3 - Automatic Log Bounding & Rolling Retention (Priority: P1)

As the system, I want to prune older logs automatically so that database storage remains small and bounded.

**Why this priority**: Operational safety — prevents logs from growing without bounds and exhausting homelab disk volumes.

**Independent Test**: Seed the database with 1,000 log records, run a new check, and verify that the database table count remains capped at 1,000.

**Acceptance Scenarios**:

1. **Given** 1,000 logs in the database, **When** a new check completes and triggers a log insert, **Then** the system automatically prunes the oldest log row, maintaining the count at exactly 1,000.

## Requirements

### Functional Requirements

- **FR-001**: System MUST write a structured activity log entry whenever a manual/scheduled check starts, succeeds, or fails.
- **FR-002**: System MUST write a structured activity log entry whenever a notification dispatch succeeds or fails.
- **FR-003**: System MUST store timestamp, event type (`check`, `notification`), status (`success`, `failed`), device name, module name, and message/traceback in SQLite.
- **FR-004**: System MUST limit database activity logs to a maximum of 1,000 records, automatically pruning the oldest records upon new insertions.
- **FR-005**: System MUST expose a REST endpoint `GET /api/v1/activity` returning activity entries sorted by timestamp descending.
- **FR-006**: System MUST support filtering active logs on the API via optional query parameters (`status`, `type`).
- **FR-007**: The UI MUST render a dedicated Activity Log navigation path and full-screen view.
- **FR-008**: The Activity Log UI view MUST allow expanding failed rows to render detailed traceback/exception blocks with clear copyable formatting.
- **FR-009**: Activity logs MUST store device and module names as plain text snapshots to ensure logs survive inventoried asset deletions.

### Key Entities

- **ActivityLogEntry**: Represents a historical system event.
  - `id` (Integer, Primary Key)
  - `event_type` (Text: 'check', 'notification')
  - `status` (Text: 'success', 'failed')
  - `device_name` (Text, optional snapshot name)
  - `module_name` (Text, optional snapshot name)
  - `message` (Text, short description)
  - `traceback` (Text, optional exception stack trace)
  - `created_at` (Text, timestamp)

## Assumptions & Risks

### Assumptions

- The operator accesses the UI from a standard modern desktop or mobile browser.
- Individual error traceback strings do not exceed 10KB.
- Standard LAN traffic does not require complex log-streaming or real-time WebSockets connections.

### Risks

- **SQLite Write Locks** *(likelihood: low, impact: medium)*: Parallel activity writes from concurrent checks lock the database. Mitigation: WAL journal configuration and 5s `busy_timeout` connection handlers.
- **Log Volume Exhaustion** *(likelihood: low, impact: high)*: Massive log counts consume disk. Mitigation: Hard-bounded 1,000 record rolling limit verified in integration tests.

## Implementation Signals

- [Tag: `MIGRATION`] — Numbered migration `006_activity_log.sql` creating the `activity_log` table.
- [Tag: `NEW-ENTITY`] — Pydantic and raw SQL repo entities representing `ActivityLogEntry`.
- [Tag: `NEW-API`] — Router endpoints `/api/v1/activity` with filter capabilities.
- [Tag: `NEW-UI`] — A beautiful stateful Activity SPA page with badges, filters, and expandable traceback details.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: The Activity page renders all check and alerting histories properly with clean badge-indicated statuses.
- **SC-002** [US2]: Diagnostics and traceback strings are cleanly formatted and expandable inside failed activity log rows.
- **SC-003** [US3]: Database table counts never exceed the rolling threshold of 1,000 rows.
