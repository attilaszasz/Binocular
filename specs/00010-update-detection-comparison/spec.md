---
feature_branch: "00010-update-detection-comparison"
created: "2026-06-10"
input: "E010 Update Detection & Comparison — determine newer-than-recorded reliably"
spec_type: "product"
spec_maturity: "clarified"
epic_id: "E010"
epic_sources: "{PRD:CAP-006}"
---

# Feature Specification: Update Detection & Comparison

**Feature Branch**: `00010-update-detection-comparison`  
**Created**: 2026-06-10  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: clarified  
**Epic ID**: E010  
**Epic Sources**: {PRD:CAP-006}  
**Product Document**: specs/prd.md  

## Problem Statement

To keep offline devices secure and operational, operators must know when a vendor releases new firmware. Binocular has a device inventory and a module engine contract, but lacks the core orchestrator that brings them together. Without an update detection and version comparison service, the system cannot run a module's scraping logic against a device, analyze if the detected version is newer than the recorded one, and update the device status — making automated watcher functionality impossible.

## Scope

### Included

- Core check service `CheckService` orchestrating the full flow: loading a module, executing its check via the runner, and comparing versions.
- Version comparison utility `VersionCompare` supporting diverse format rules (SemVer, date-based, sub-version numbers, leading 'v', mixed alphabetic prefixes).
- Updating device status in the database (`has_update`, `latest_detected_version`, and `last_checked` timestamp) on completed checks.
- Generating a rich execution result (`DeviceCheckResult`) event/shape for downstream audit logging and notification epics.
- Graceful error boundary: mapping module timeouts, HTTP scrape failures, or parse errors into a failed check result containing an error message without crashing the application.
- Comprehensive unit and integration test coverage for the comparison logic and orchestration.

### Excluded

- Manual check endpoints or bulk trigger controllers (E012) — E010 provides the internal service method, not the API routers or UI triggers.
- Cron scheduling or scheduler integrations (E013) — downstream consumer.
- Notification dispatch or alerting integration (E014) — downstream consumer.
- Log viewing UI or activity log repository storage (E015) — downstream consumer.

### Edge Cases & Boundaries

- **Equal Versions**: If the latest version matches the current version, `has_update` is set/maintained as `False`.
- **Downgraded/Older Version**: If the scraped version is older than the current version (e.g. rollbacks or special pre-release versions), `has_update` is set/maintained as `False`.
- **Invalid version string format**: If the scraped or current version cannot be parsed by any comparison rule, fall back to simple string comparison (and if unequal, treat as a potential new version or log warning).
- **Module failure**: If the module raises an exception or times out, the service updates `last_checked` but leaves `has_update` unchanged, producing a failed check result.

## User Scenarios & Testing

### User Story 1 - Automatic Version Parsing and Comparison (Priority: P1)

The system compares the detected firmware version from a manufacturer with the device's currently installed version using a flexible comparison algorithm. It must correctly identify new updates for standard SemVer, date-based versions (e.g. `20260304-01` vs `20260305-01`), and mixed-format versions (e.g. `v1.2a` vs `v1.2b`).

**Why this priority**: Core value proposition — without robust comparison, operators will either get false alarms or miss updates due to diverse vendor versioning strategies.

**Independent Test**: Provide `VersionCompare.is_newer(current, latest)` with a list of historical firmware versions from Sony, Godox, and Panasonic, verifying correct boolean outcomes for all edge cases.

**Acceptance Scenarios**:

1. **Given** current version is `1.0.0`, **When** the latest detected version is `1.0.1`, **Then** the comparison returns `True` (has update).
2. **Given** current version is `20260601-01`, **When** the latest detected version is `20260610-01`, **Then** the comparison returns `True` (has update).
3. **Given** current version is `v2.0` and latest is `v2.0`, **When** compared, **Then** the comparison returns `False`.
4. **Given** current version is `1.1a`, **When** latest is `1.1b`, **Then** the comparison returns `True`.

### User Story 2 - Device Status Update on Success (Priority: P1)

When a check runs successfully, the system records the result. If a newer version is found, the device record is updated with `has_update = True` and `latest_detected_version` populated with the new version. The `last_checked` timestamp must be updated.

**Why this priority**: The inventory and dashboard depend on the device table state to show alerts.

**Independent Test**: Trigger a check service execution for a device, verify database updates reflect the new version and update flag.

**Acceptance Scenarios**:

1. **Given** a device with current version `1.0.0` and `has_update = False`, **When** the check service detects version `1.1.0`, **Then** the device's `has_update` becomes `True`, its `latest_detected_version` becomes `"1.1.0"`, and `last_checked` is set to the current time.
2. **Given** a device with current version `1.0.0`, **When** the check service detects version `1.0.0`, **Then** the device's `has_update` remains `False` and `last_checked` is updated.

### User Story 3 - Graceful Handling of Scraping/Module Errors (Priority: P1)

If a module execution fails (e.g. target website is offline or scraping contract broke), the check orchestrator captures the failure, saves a failed check result, and leaves the device's update flag unchanged.

**Why this priority**: Prevents a single failing module from crashing the check sequence or the entire daemon (Core Principle VI).

**Independent Test**: Trigger a check service execution with a mock module that raises a `TimeoutError`, and verify the system catches the error, updates `last_checked`, and returns a failed status.

**Acceptance Scenarios**:

1. **Given** a device is scheduled for a check, **When** the module runner throws a connection error, **Then** the check service catches it, returns a result with `success = False` and `error_message` containing the failure detail, and the device's `has_update` is not modified.

## Requirements

### Functional Requirements

- **FR-001**: System MUST provide a `VersionCompare.compare(v1, v2)` utility that parses and compares two version strings, returning positive if `v2 > v1`, zero if `v2 == v1`, and negative if `v2 < v1`.
- **FR-002**: `VersionCompare` MUST support parsing SemVer formats, numeric dot-delimited formats, date-based formats, and suffix-based updates (e.g., `1.0a` vs `1.0b`).
- **FR-003**: System MUST provide a `CheckService.check_device(device_id)` async method.
- **FR-004**: `CheckService` MUST load the device's assigned module, instantiate the zentral Scraping Client, and run the module via `ModuleRunner`.
- **FR-005**: If the module run is successful, `CheckService` MUST compare the returned version with the device's `current_version`.
- **FR-006**: If the returned version is newer, the system MUST set the device's `has_update = True` and `latest_detected_version` to the returned version.
- **FR-007**: Regardless of version comparison outcome, the system MUST update the device's `last_checked` timestamp to the check completion time.
- **FR-008**: If the module run fails (exception, timeout, parse failure), `CheckService` MUST return a failed execution result and NOT modify the device's `has_update` status.
- **FR-009**: `CheckService` MUST return a `DeviceCheckResult` containing: `device_id`, `module_id`, `latest_version`, `current_version`, `has_update`, `checked_at`, `success`, and `error_message`.

### Key Entities

- **DeviceCheckResult**: The data shape representing the execution outcome of an update check. Attributes:
  - `device_id` (integer)
  - `module_id` (integer)
  - `latest_version` (text, nullable)
  - `current_version` (text)
  - `has_update` (boolean)
  - `checked_at` (ISO datetime string)
  - `success` (boolean)
  - `error_message` (text, nullable)

## Assumptions & Risks

### Assumptions

- The centralized scraping client (`ScrapeClient`) is fully functional and handles rate limits/robots.txt as implemented in E005.
- Extension modules conform to the V1 contract defined in E007.
- Devices can be loaded from the existing repository implemented in E006.

### Risks

- **Diverse Version Formats** *(likelihood: medium, impact: medium)*: Vendors use non-standard version schemas that might fail clean parsing. Mitigation: Fall back to direct string comparison if parser fails, and log/store warnings.
- **Database Lock Conflicts** *(likelihood: low, impact: low)*: SQLite single-writer pattern might block if multiple checks write concurrently. Mitigation: Downstream scheduling runs sequential checks or uses standard serial transaction boundaries.

## Implementation Signals

- `NEW-ENTITY` — `DeviceCheckResult` model/shape
- `NEW-API` — `CheckService` and `VersionCompare` classes under `backend/src/binocular/services/`
- `MIGRATION` — Add any necessary repository helper methods to update device checked status (or modify `DeviceRepository` to support updating check fields)

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: `VersionCompare.is_newer` returns correct outputs for a test suite of at least 15 diverse real-world firmware version formats.
- **SC-002** [US2]: Successfully run check updates `has_update = True` when a newer version is scraped and updates `last_checked` timestamp.
- **SC-003** [US3]: Failed checks return a structured error result without throwing unhandled exceptions to the core application loop.

## Compliance Check

### Instructions Check Report
**Target**: spec.md
**Status**: PASS

| Principle | Verdict | Notes |
|-----------|---------|-------|
| I. Honest Failure | PASS | Unparseable/failed scrapers produce visible error message in `DeviceCheckResult`, never silent fail. |
| II. Polite by Default | PASS | All checks run via `ModuleRunner` using centrally configured `ScrapeClient`. |
| III. Data Ownership | PASS | All updates written to SQLite volume, no external APIs used. |
| IV. Least-Privilege | N/A | No changes to container credentials or user context. |
| V. Type Safety | PASS | Uses explicit type annotations, passes strict verification. |
| VI. Set-and-Forget | PASS | Fault isolation ensures module exceptions do not crash check services. |
| VII. Agent Output Style | N/A | Spec is user-facing document. |
