---
feature_branch: "00011-update-detection-comparison"
created: "2026-05-31"
input: "E009 Update Detection & Comparison"
spec_type: "product"
spec_maturity: "draft"
epic_id: "E009"
epic_sources: "{PRD:CAP-006}"
---

# Feature Specification: Update Detection & Comparison

**Feature Branch**: `00011-update-detection-comparison`  
**Created**: 2026-05-31  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: draft  
**Epic ID**: E009  
**Epic Sources**: {PRD:CAP-006}  
**Product Document**: specs/prd.md

## Problem Statement

Binocular can store devices and run extension modules, but it still needs the core decision point that turns a module's latest-version response into a trustworthy device status. If this comparison is wrong or failure is hidden, later manual checks, scheduled checks, notifications, and activity logging can silently miss firmware updates. The system needs one shared detection result contract that records success, update availability, and visible failure for every checked device.

## Scope

### Included

- Run the installed module associated with a device or device type and collect its normalized latest-version result.
- Compare the module-reported latest version with the device's recorded current version.
- Persist and return a structured result with `up_to_date`, `update_available`, or `failed` status.
- Preserve last-success timestamp and visible failure detail when a module fails or version comparison cannot be trusted.
- Expose the shared check-result contract for future manual, scheduled, notification, and activity-log workflows.

### Excluded

- Manual on-demand check UI and bulk execution — covered by E010.
- Scheduled job orchestration — covered by E011.
- Notification dispatch — covered by E012.
- Activity-log viewer and long-term event browsing — covered by E014.
- Official module fixture correctness for Sony and Panasonic — covered by E015.

### Edge Cases & Boundaries

- A module returns `failed`, times out, raises, or emits invalid output; the result is persisted as failed without crashing the core process.
- A module succeeds but omits `latest_version`; the check is failed because no safe comparison is possible.
- A stored or detected version is unparseable; the check is failed visibly rather than guessed.
- Equal versions are up-to-date; strictly newer detected versions are update-available.
- Older detected versions are treated as up-to-date with diagnostics, not as an update.
- Archived or missing devices cannot be checked.

## User Scenarios & Testing

### User Story 1 - Detect Device Update Status (Priority: P1)

As the system, I need to run a device's firmware module and determine whether the detected latest version is newer than the operator's recorded version, so downstream workflows have one authoritative status.

**Why this priority**: Core value proposition — this decision is required before checks, notifications, and activity visibility can be reliable.

**Independent Test**: Run a check for devices whose module returns equal, newer, and older versions and verify the persisted status and returned result.

**Acceptance Scenarios**:

1. **Given** a device with current version `1.0` and a module returning latest version `1.1`, **When** the device is checked, **Then** the result status is `update_available` and the detected latest version is persisted.
2. **Given** a device with current version `1.1` and a module returning latest version `1.1`, **When** the device is checked, **Then** the result status is `up_to_date`.
3. **Given** a device with current version `2.0` and a module returning latest version `1.9`, **When** the device is checked, **Then** the result status is `up_to_date` with comparison diagnostics showing the detected version was not newer.

### User Story 2 - Surface Failed Detection Honestly (Priority: P1)

As the system, I need failed module runs and unsafe comparisons to produce visible failed results with useful diagnostics, so Binocular never silently misses an update when a source page changes or a module breaks.

**Why this priority**: Honest failure is a project principle and a prerequisite for unattended trust.

**Independent Test**: Run checks where the module fails, omits a latest version, or returns an unparseable version and verify failed status plus retained last-success data.

**Acceptance Scenarios**:

1. **Given** a device with a prior successful check, **When** its module fails, **Then** the device status becomes `check_failed` and the prior `last_success_at` remains unchanged.
2. **Given** a module returns success without a comparable latest version, **When** the device is checked, **Then** the result status is `failed` with a diagnostic reason.

### User Story 3 - Provide Shared Detection Contract (Priority: P2)

As downstream workflows, we need a stable check-result shape containing device identity, stored version, latest version, status, timestamps, source URL, and diagnostics, so manual checks, scheduled checks, notifications, and activity logging do not invent separate interpretations.

**Why this priority**: Significant integration value — later epics depend on this contract, but P1 comparison and failure semantics deliver the MVP decision core.

**Independent Test**: Inspect the API/service result for a successful and failed check and verify all contract fields are present and typed.

**Acceptance Scenarios**:

1. **Given** a successful update-available check, **When** a downstream caller receives the result, **Then** it includes the device ID, current version, latest version, status, timestamps, source URL, and diagnostics.
2. **Given** a failed check, **When** a downstream caller receives the result, **Then** it includes a stable failed status and diagnostic detail without requiring module-specific parsing.

## Requirements

### Functional Requirements

- **FR-001**: System MUST run the configured installed module for an active device using the existing module runner and host scraping client.
- **FR-002**: System MUST compare the module-reported latest version against the device's stored current version using deterministic version-ordering rules.
- **FR-003**: System MUST classify each check as `up_to_date`, `update_available`, or `failed`.
- **FR-004**: System MUST persist `latest_version`, `last_checked_at`, `last_success_at`, and `last_check_status` consistently with the check outcome.
- **FR-005**: System MUST preserve the previous `last_success_at` when a check fails.
- **FR-006**: System MUST treat missing, invalid, or unsafe version comparisons as visible failed checks.
- **FR-007**: System MUST return a structured check result containing device identity, current version, latest version, status, timestamps, source URL, module detail, and diagnostics.
- **FR-008**: System MUST NOT allow a module failure, timeout, invalid output, or comparison error to crash the core process.

### Key Entities

- **CheckResult**: A structured outcome for one device check, including status, versions, timestamps, source URL, and diagnostics.
- **Detection Event**: The persisted state transition produced by a check and later consumed by manual-check, scheduled-check, notification, and activity-log workflows.
- **Version Comparison**: The deterministic decision that identifies whether the detected latest version is newer than the stored current version.

## Assumptions & Risks

### Assumptions

- Installed modules can be mapped to a device or device type using existing module metadata or a simple configured association.
- Firmware versions are usually comparable as semantic, PEP 440-like, or dotted numeric strings.
- The existing device fields are sufficient for this increment; detailed check history belongs to the activity-log epic.
- The host scraping client from E007 remains the only outbound fetch path used during module execution.

### Risks

- **Vendor-specific version formats** *(likelihood: medium, impact: high)*: Some firmware versions may not fit common parsers; mitigation is explicit failed status plus diagnostics rather than guessing.
- **Module-to-device association gap** *(likelihood: medium, impact: medium)*: Existing module metadata may be insufficient for automatic selection; mitigation is to keep the association explicit and testable in the plan.
- **Shared contract churn** *(likelihood: low, impact: high)*: Later epics depend on this shape; mitigation is typed models and contract tests.

## Implementation Signals

- `NEW-ENTITY` — Add a typed `CheckResult` / detection-event model for service and API consumers.
- `NEW-API` — Add a minimal check endpoint or service entry point that returns the shared result.
- `MIGRATION` — Extend persistence only if existing device status fields cannot store required diagnostics or module association.
- `EXTERNAL-SERVICE` — Execute modules through the existing host-provided scraping client; no direct outbound requests.
- `NEW-WORKER` — Not in scope for this feature; scheduled execution is deferred to E011.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: A check with a newer detected version returns `update_available` and persists the detected latest version.
- **SC-002** [US1]: A check with an equal or older detected version returns `up_to_date` and does not create an update alert condition.
- **SC-003** [US2]: A failed module run returns `failed`, persists visible failed status, and keeps the prior last-success timestamp unchanged.
- **SC-004** [US2]: Missing or unparseable versions return `failed` with diagnostics rather than silently assuming up-to-date.
- **SC-005** [US3]: The check-result contract is covered by tests for update-available, up-to-date, and failed outcomes.

## Glossary

| Term | Definition |
|------|------------|
| CheckResult | The typed result of running detection for one device. |
| Detection Event | The status transition and metadata emitted by a detection check. |
| Latest Version | The firmware version reported by an extension module as currently published by a manufacturer. |
| Current Version | The firmware version recorded by the operator for a stored device. |

## Compliance Check

### Instructions Check Report
**Target**: specs/00011-update-detection-comparison/spec.md
**Status**: PASS

| Principle | Verdict | Notes |
|-----------|---------|-------|
| Honest Failure | PASS | Failed and unsafe checks are visible and preserve last-success context. |
| Polite by Default | PASS | Module execution uses the host scraping client; no direct outbound path is introduced. |
| Data Ownership & Self-Containment | PASS | Uses existing SQLite-backed device state; no external storage. |
| Least-Privilege & Explicit Trust Boundary | PASS | Keeps existing unsandboxed module trust boundary explicit. |
| Type Safety & Correctness-First | PASS | Requires typed contract and tests for comparison outcomes. |
| Set-and-Forget Reliability | PASS | Module failures cannot crash core process and must persist visible status. |

**Violations**:
None
