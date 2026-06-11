---
feature_branch: "00013-automated-scheduled-checking"
created: "2026-06-11"
input: "specs/plan/E013.md"
spec_type: "product"
spec_maturity: "draft"
epic_id: "E013"
epic_sources: "{PRD:CAP-004}{SAD:ADR-0007}"
---

# Feature Specification: Automated Scheduled Checking

**Feature Branch**: `00013-automated-scheduled-checking`  
**Created**: 2026-06-11  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: draft  
**Epic ID**: E013  
**Epic Sources**: {PRD:CAP-004}{SAD:ADR-0007}  
**Product Document**: specs/prd.md

## Problem Statement

Automated scheduled checking is required to automatically query manufacturer firmware pages at regular intervals. Without scheduling, the user has to manually trigger updates, defeating the set-and-forget product vision. If scheduling is not restart-safe or configurable, checks may fail to run after container restarts or overload third-party servers due to rigid timing.

## Scope

### Included

- Database migration to create the `schedules` table linking each module to an interval.
- Integration of `APScheduler` (AsyncIOScheduler) running in-process.
- Service class `SchedulerService` to load, register, and update schedules.
- REST API endpoints GET/PUT `/api/v1/schedules` to read and edit frequencies per module.
- Startup hook to initialize the scheduler and resume schedules safely.
- A UI component `FrequencyEditor` embedded on the Modules page.

### Excluded

- User accounts or authentication config (rely on existing basic auth middleware if active).
- Job stores other than memory-based scheduler backed by custom SQLite tables.

### Edge Cases & Boundaries

- **App start with expired intervals**: When the app starts, if `now` > `next_run`, the check should run immediately, and then reschedule for `now + interval_hours`.
- **Modifying intervals dynamically**: Changing a module's interval must reschedule the active job in APScheduler.
- **Concurrent DB writes**: Multiple background checks executing and writing results concurrently.

## User Scenarios & Testing

### User Story 1 - View and Edit Schedules (Priority: P1)

As a user, I want to view the check intervals for my modules on the Modules page, and change them so that I can control how frequently each module checks for updates.

**Why this priority**: Core scheduling configurability is essential for setting check frequency.

**Independent Test**: Retrieve the schedules via GET `/api/v1/schedules`, update one using PUT, and confirm the new interval is saved and active.

**Acceptance Scenarios**:

1. **Given** the database contains a module with a default 24h schedule, **When** I view the Modules page, **Then** I see the "Frequency: Every 24 hours" display.
2. **Given** a module schedule exists, **When** I update the frequency to 12 hours and save, **Then** the database updates `interval_hours` to 12 and the background scheduler reschedules the job.

### User Story 2 - Scheduled Background Executions (Priority: P1)

As the system, I want to run background checks automatically at the configured intervals, and update the next run times accordingly.

**Why this priority**: Core automation requirement.

**Independent Test**: Set a module's interval to a short time, verify the scheduler executes it, and check that `last_run` and `next_run` are updated in the DB.

**Acceptance Scenarios**:

1. **Given** an active module and its schedule, **When** the scheduled time is reached, **Then** the system triggers `CheckService` for all devices using that module.
2. **Given** a successful check run, **When** the check completes, **Then** the database updates `last_run` and `next_run` for the schedule.

### User Story 3 - Restart Resume Execution (Priority: P1)

As a user, I want the scheduler to pick up where it left off when the application container restarts, so that no checks are missed or run too early.

**Why this priority**: Set-and-forget reliability requirement.

**Independent Test**: Record a schedule's next run time, restart the app, and verify that the job is registered for the correct next run time.

**Acceptance Scenarios**:

1. **Given** a schedule with `next_run` in 4 hours, **When** the application restarts, **Then** the background job is scheduled to run in exactly 4 hours.
2. **Given** a schedule with `next_run` in the past, **When** the application restarts, **Then** the check runs immediately and reschedules the next check.

## Integration Points

- **IP-001**: `SchedulerService` depends on `CheckService` for running checks.
- **IP-002**: `FrequencyEditor` depends on GET/PUT `/api/v1/schedules` for data.

## Requirements

### Functional Requirements

- **FR-001**: System MUST support configuring checking intervals (in hours) per extension module.
- **FR-002**: GET `/api/v1/schedules` MUST return a list of modules with their schedules (interval_hours, last_run, next_run).
- **FR-003**: PUT `/api/v1/schedules` MUST update the schedule interval for a given module and update the active job in APScheduler.
- **FR-004**: System MUST seed default schedules (24 hours) for newly created or imported modules.

### Technical Requirements

- **TR-001**: DB schema migration MUST create `schedules` table with fields: `id`, `module_id` (FK to modules table), `interval_hours` (default 24), `last_run` (timestamp), `next_run` (timestamp).
- **TR-002**: APScheduler MUST trigger checks for all devices associated with the module when the interval expires.

### Key Entities

- **Schedule**:
  - `id`: Unique identifier
  - `module_id`: FK reference to `modules.id`
  - `interval_hours`: Frequency of check in hours
  - `last_run`: Timestamp of last executed check (optional)
  - `next_run`: Timestamp of next scheduled check

## Assumptions & Risks

### Assumptions

- Users accept hours-based checking interval granularity.
- The system timezone is UTC or system local.

### Risks

- **[Locking contention]** *(likelihood: low, impact: medium)*: SQLite database lock conflicts due to concurrent writes from check service and scheduler. Mitigated by WAL mode and transaction retries.

## Implementation Signals

- `MIGRATION` — Add `schedules` table to SQLite.
- `NEW-API` — REST API endpoints for GET/PUT `/api/v1/schedules`.
- `NEW-UI` — Integrate FrequencyEditor inside ModuleCard.
- `NEW-WORKER` — APScheduler background loop initialization on app startup.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: Users can view and update checking intervals from the UI.
- **SC-002** [US2]: Scheduled jobs run in the background at the exact interval.
- **SC-003** [US3]: Application restarts preserve next run times and resume checking.

## Glossary

| Term | Definition |
|------|------------|
| Schedule | A database record storing the configured checking interval, last run time, and next run time for an extension module. |
| Check Interval | The configured frequency (in hours) at which a module is executed to check for firmware updates. |

## Compliance Check

- **Core Principles**: Satisfied. Central polite HTTP client is utilized for checks, SQLite is used for database, no root container setup.
- **Technology Stack**: Satisfied. APScheduler 3.x is used in backend, no ORMs are introduced.
- **Source Code Layout**: Satisfied. Backend code is placed in `backend/src/`, frontend in `frontend/src/`.
