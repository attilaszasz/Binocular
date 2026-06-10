---
feature_branch: "00015-automated-scheduled-checking"
created: "2026-05-31"
input: "E011 Automated Scheduled Checking"
spec_type: "product"
spec_maturity: "draft"
epic_id: "E011"
epic_sources: "{PRD:CAP-004}{SAD:ADR-0007}"
---

# Feature Specification: Automated Scheduled Checking

**Feature Branch**: `00015-automated-scheduled-checking`  
**Created**: 2026-05-31  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: draft  
**Epic ID**: E011  
**Epic Sources**: {PRD:CAP-004}{SAD:ADR-0007}  
**Product Document**: specs/prd.md

## Problem Statement

Binocular can run checks manually, but operators still must remember to start them. The product promise is unattended monitoring, so each device type needs a saved interval that resumes after restart. If scheduled checks fail, overlap, or stop silently, Binocular can miss updates without warning.

## Scope

### Included

- Configure enabled/disabled scheduled-check intervals per device type.
- Run unattended checks through the existing detection/check-result service.
- Resume schedules after restart from SQLite configuration.
- Retry missed windows on the next interval without backlog replay.
- Show next run, last success, and failure diagnostics in the UI.

### Excluded

- Notification dispatch — covered by E012.
- Activity-log browsing — covered by E014.
- External worker, broker, or multi-process scheduler coordination — out of scope.
- Manual check controls — covered by E010.

### Edge Cases & Boundaries

- Disabled schedules do not run and show disabled state.
- Overlapping intervals are skipped or coalesced visibly.
- Restart after missed intervals schedules one future check, not a backlog.
- Empty or unconfigured device types complete with diagnostics.
- Module or scheduler failures remain visible and preserve last-success context.

## User Scenarios & Testing

### User Story 1 - Configure Device-Type Schedules (Priority: P1)

As an operator, I need per-type frequency controls so different gear can use appropriate intervals.

**Why this priority**: Core value proposition — unattended checking cannot work until the operator can save per-type intervals.

**Independent Test**: Configure an interval, reload the app, and verify saved schedule and next-run state.

**Acceptance Scenarios**:

1. **Given** a device type, **When** the operator enables scheduling and saves an interval, **Then** Binocular persists it and shows the next run.
2. **Given** a scheduled device type, **When** the operator disables scheduling, **Then** no future unattended checks run for that type until re-enabled.
3. **Given** an invalid interval, **When** the operator saves, **Then** Binocular rejects it with a visible validation message.

### User Story 2 - Run Unattended Checks Reliably (Priority: P1)

As the system, I need to check active devices on schedule so updates are discovered without clicks.

**Why this priority**: Core value proposition — scheduled checks are the unattended detect loop.

**Independent Test**: Configure a short interval and verify check results appear without a manual trigger.

**Acceptance Scenarios**:

1. **Given** an enabled device type with active devices, **When** its interval arrives, **Then** Binocular runs detection for eligible devices in that type.
2. **Given** one scheduled device fails and another succeeds, **When** the run completes, **Then** each device has an independent visible result.
3. **Given** the prior run is still executing, **When** the next interval arrives, **Then** Binocular avoids duplicate work and records the skip.

### User Story 3 - Resume After Restart (Priority: P1)

As an operator, I need schedules to resume after restart without reconfiguration.

**Why this priority**: Set-and-forget reliability — restart survival is mandatory for unattended operation.

**Independent Test**: Save a schedule, restart, and verify one job is reconstructed and runs on the next interval.

**Acceptance Scenarios**:

1. **Given** saved configuration, **When** the app starts, **Then** Binocular rebuilds scheduler jobs from persisted state.
2. **Given** the app was down for multiple intervals, **When** it restarts, **Then** Binocular schedules the next run without backlog replay.
3. **Given** scheduler startup fails for a device type, **When** the operator views schedules, **Then** the failure is visible with diagnostics.

### User Story 4 - View Schedule Health (Priority: P2)

As an operator, I need next run, last run, and failure details.

**Why this priority**: Significant reliability value — P1 can schedule checks, but visible health makes failures actionable.

**Independent Test**: Cause success, failure, and skip, then verify health fields.

**Acceptance Scenarios**:

1. **Given** a scheduled run succeeds, **When** the operator views the device type, **Then** last-completed and last-success timestamps are shown.
2. **Given** a run fails, **When** the operator views the device type, **Then** diagnostics are shown without hiding prior success.

## Requirements

### Functional Requirements

- **FR-001**: System MUST allow the operator to enable or disable scheduled checking per device type.
- **FR-002**: System MUST allow the operator to configure a valid scheduled-check interval per device type.
- **FR-003**: System MUST persist schedule configuration in the application SQLite database.
- **FR-004**: System MUST rebuild scheduled jobs from persisted configuration on startup.
- **FR-005**: System MUST check active eligible devices at the configured interval.
- **FR-006**: System MUST use the existing detection/check-result service for scheduled device checks.
- **FR-007**: System MUST avoid overlapping duplicate scheduled runs for the same device type.
- **FR-008**: System MUST retry missed windows at the next configured interval without replaying a downtime backlog.
- **FR-009**: System MUST expose enabled state, interval, next run, last run, last success, last failure, and diagnostics.
- **FR-010**: System MUST surface scheduler startup errors, execution errors, missed runs, and skipped overlaps visibly.
- **FR-011**: System MUST NOT require an external worker, broker, cloud service, or database server for scheduled checking.

### Key Entities

- **Schedule**: Per-device-type configuration and runtime status.
- **DeviceType Schedule Configuration**: Saved enabled state and interval.
- **Scheduled Check Run**: One unattended execution window.
- **CheckResult**: The existing structured outcome reused for every scheduled device check.

## Assumptions & Risks

### Assumptions

- E009 exposes a stable device check service and result semantics.
- Device types can be queried with active devices and module association.
- Binocular runs as one scheduler-owning application process in the supported deployment.
- Conservative default intervals can be chosen during planning.
- SQLite remains sufficient for schedule state and check-result persistence.

### Risks

- **Duplicate jobs in unsupported multi-worker deployments** *(likelihood: low, impact: high)*: Multiple workers could run the same schedule; mitigation is explicit single scheduler-owner support.
- **Scraping bursts after downtime** *(likelihood: medium, impact: high)*: Replaying missed intervals could overload sources; mitigation is no backlog replay.
- **Silent scheduler failure** *(likelihood: medium, impact: high)*: Scheduler errors could hide missed updates; mitigation is visible schedule health and diagnostics.

## Implementation Signals

- `NEW-ENTITY` — Add per-device-type schedule configuration and runtime status.
- `MIGRATION` — Persist settings, timestamps, and diagnostics in SQLite.
- `NEW-API` — Add endpoints to read and update schedule settings and status.
- `NEW-UI` — Add schedule controls and health state to device-type views.
- `NEW-WORKER` — Add an in-process APScheduler service owned by app lifecycle.
- `NEW-CONFIG` — Document single scheduler-owner behavior and default interval limits.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: An operator can enable, disable, and save a valid interval for a device type.
- **SC-002** [US1]: Saved schedule configuration remains visible after application restart.
- **SC-003** [US2]: An enabled device type runs unattended checks at its configured interval and produces check results for eligible devices.
- **SC-004** [US2]: A slow scheduled run cannot create overlapping duplicate work for the same device type.
- **SC-005** [US3]: Restart reconstructs one deterministic job per enabled device type from SQLite configuration.
- **SC-006** [US3]: Downtime missed intervals are not replayed as a backlog.
- **SC-007** [US4]: Schedule health displays next run, last completion, last success, and visible failure diagnostics.

## Glossary

| Term | Definition |
|------|------------|
| Schedule | Saved interval and runtime health state for one device type. |
| Scheduled Check Run | An unattended check execution triggered by the scheduler. |
| Missed Window | An interval that elapsed while the app could not run the job. |
| Overlap Skip | Visible state recorded when an interval arrives while the prior run is active. |

## Compliance Check

### Instructions Check Report
**Target**: specs/00015-automated-scheduled-checking/spec.md
**Status**: PASS

| Principle | Verdict | Notes |
|-----------|---------|-------|
| Honest Failure | PASS | Scheduler and check failures are visible. |
| Polite by Default | PASS | No backlog replay or scraping burst. |
| Data Ownership & Self-Containment | PASS | Schedule state stays in SQLite. |
| Least-Privilege & Explicit Trust Boundary | PASS | Existing module boundary unchanged. |
| Type Safety & Correctness-First | PASS | Typed contracts and lifecycle tests required. |
| Set-and-Forget Reliability | PASS | Restart reconstruction required. |

**Violations**:
None