---
feature_branch: "00012-manual-on-demand-checks"
created: "2026-06-10"
input: "E012"
spec_type: "product"
spec_maturity: "draft"
epic_id: "E012"
epic_sources: "{PRD:CAP-005}"
---

# Feature Specification: Manual On-Demand Checks

**Feature Branch**: `00012-manual-on-demand-checks`  
**Created**: 2026-06-10  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: draft  
**Epic ID**: E012  
**Epic Sources**: {PRD:CAP-005}  
**Product Document**: [specs/prd.md](../prd.md)  
**Technical Context Document**: [specs/sad.md](../sad.md)

## Problem Statement *(mandatory)*

Operators of offline devices need to verify firmware updates immediately rather than waiting for scheduled runs. Without manual triggers, verifying whether a new device addition or module configuration works correctly is delayed, leading to a poor operator feedback loop. Providing manual, immediate checking capabilities for single and bulk devices ensures operators have instant confirmation of the update status.

## Scope *(mandatory)*

### Included

- **Single Device Trigger**: API endpoint `POST /api/v1/checks/device/{id}` to trigger an immediate check for a specific device.
- **Bulk Trigger**: API endpoint `POST /api/v1/checks/bulk` to trigger checks for all configured devices.
- **Check Outcomes**: API returns `DeviceCheckResult` matching the version check execution results (success/failure status, error messages, stored version, latest version, and checked timestamp).
- **UI Interaction**: "Check" button on each device card, and a global "Check All" button in the inventory header.
- **Loading States**: UI displays visual loading indicators (spinners, disabled buttons, or skeleton states) while checking is in progress.
- **Version Comparison**: Side-by-side comparison display in the UI of the current stored version versus the latest detected version.

### Excluded

- **Automatic Update Execution** — Binocular only detects and alerts; it never downloads or applies firmware to physical devices.
- **Background Worker Queue** — Checks are executed synchronously in the HTTP request handler context (with per-module timeouts) rather than dispatched to a separate background job queue system.

### Edge Cases & Boundaries

- **Scraper Failure**: If the scraping run fails (e.g., page format changed, timeout), the API returns a failed result state with an error message, and the UI displays this error badge/text without clearing the device's last known good check state.
- **Empty Inventory**: The bulk check endpoint returns an empty array immediately when no devices are registered.
- **Simultaneous Triggers**: Clicking "Check" while a check is already running for a device will be supported, but UI buttons are disabled during loading states to prevent redundant clicks.

## User Scenarios & Testing *(mandatory for product specs only)*

### User Story 1 - Single Device Check (Priority: P1)

As an operator, I want to trigger an update check for a single device immediately, so that I can verify its firmware status without waiting for the scheduled job.

**Why this priority**: Core value proposition — essential for confirming specific device module execution works and checking a single site quickly.

**Independent Test**: Trigger check on a single device, verify that the page loading indicator appears, and a successful check updates the "last checked" timestamp and version badges.

**Acceptance Scenarios**:

1. **Given** a registered device "A7R V" with current version "2.01", **When** the operator clicks the "Check" button on its card, **Then** a loading spinner is shown, the button is disabled, a POST request is sent to `/api/v1/checks/device/{id}`, and upon success, the spinner disappears and the last checked time is updated.
2. **Given** a device with an invalid module file path, **When** the operator triggers a check, **Then** the check fails, and the UI displays a failure badge/status containing the error message.

### User Story 2 - Bulk Inventory Check (Priority: P1)

As an operator, I want to trigger checks for all devices in bulk from the dashboard, so that I can see the overall update status of my entire inventory at once.

**Why this priority**: Fundamental usability requirement for homelab dashboards, allowing quick daily verification of all devices.

**Independent Test**: Click the global "Check All" button and verify that all device cards update their status and checked timestamps.

**Acceptance Scenarios**:

1. **Given** multiple devices registered in the inventory, **When** the operator clicks the "Check All" button, **Then** all devices enter a loading state, a POST request is sent to `/api/v1/checks/bulk`, and once complete, the loading state ends and all cards display their new statuses.

### User Story 3 - Side-by-Side Version Comparison (Priority: P1)

As an operator, I want to see the stored firmware version side-by-side with the latest detected version when an update is available, so that I can easily decide whether to apply the update.

**Why this priority**: Clarifies the update path for the operator and aligns with CAP-005.

**Independent Test**: Check a device with an update available and verify that both the "Current" and "Latest" versions are clearly displayed.

**Acceptance Scenarios**:

1. **Given** a device with current version "1.0.0" and a check that detects latest version "2.0.0", **When** the check completes, **Then** the device card shows a badge indicating "Update: v2.0.0" next to the current version "v1.0.0", displaying them side-by-side.

## Requirements *(mandatory)*

### Functional Requirements *(product specs only)*

- **FR-001**: The system MUST expose `POST /api/v1/checks/device/{device_id}` to trigger a check on a single device by ID.
- **FR-002**: The system MUST expose `POST /api/v1/checks/bulk` to trigger a check on all devices in the database.
- **FR-003**: The bulk check endpoint MUST execute checks concurrently using async I/O.
- **FR-004**: The check endpoints MUST return the `DeviceCheckResult` schema containing `device_id`, `module_id`, `latest_version`, `current_version`, `has_update`, `checked_at`, `success`, and `error_message`.
- **FR-005**: The UI MUST provide a check button on each device card that triggers the single device check.
- **FR-006**: The UI MUST provide a global check button in the inventory page header that triggers a bulk check.
- **FR-007**: The UI MUST show loading states (spinning icons, disabled actions, or progress overlays) for devices currently undergoing checking.
- **FR-008**: The UI MUST show current version and latest version side-by-side on the device card when an update is detected.

### Key Entities *(include for product or technical specs if feature involves data)*

- **DeviceCheckResult**: The execution record of a firmware check.
  - `device_id`: The ID of the device checked (integer)
  - `module_id`: The ID of the extension module used (integer)
  - `latest_version`: The latest version scraped from the vendor page (string or null)
  - `current_version`: The current version configured on the device (string)
  - `has_update`: Whether `latest_version` is newer than `current_version` (boolean)
  - `checked_at`: ISO datetime string when the check took place (string)
  - `success`: Whether the scrape and comparison succeeded (boolean)
  - `error_message`: Error details if `success` is false (string or null)

## Assumptions & Risks *(mandatory)*

### Assumptions

- **A-001**: Device checks do not take longer than the module timeout configuration (default 30 seconds).
- **A-002**: Operators have network connectivity from the Binocular host to the vendor pages.

### Risks

- **R-001** *(likelihood: medium, impact: low)*: Bulk checks to the same manufacturer domain could trigger rate-limiting or IP bans if executed too fast. Mitigation: Central ScrapeClient applies per-domain rate pacing.

## Implementation Signals *(mandatory)*

- `NEW-API` — Create checks router (`routes/checks.py`) and register it in `routes/__init__.py`.
- `NEW-UI` — Implement check triggers (button icons, loading states, and side-by-side comparison layouts) in `pages/inventory.tsx` and `components/inventory/device-card.tsx`.
- `NEW-API` — Expose endpoint hook client methods for `checksApi` in `frontend/src/lib/api.ts`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** [US1]: Triggering a single device check via the UI updates the card state, shows a loading state, and successfully reports the new firmware details on completion.
- **SC-002** [US2]: Triggering a bulk check runs checks for all inventory devices in parallel and updates their status cards without UI lockups.
- **SC-003** [US3]: Device cards display the stored vs. latest versions side-by-side when updates are detected.

## Glossary *(include when spec introduces 2+ domain-specific terms)*

| Term | Definition |
|------|------------|
| Bulk Check | Triggering version checks for all devices in the inventory concurrently. |
| Side-by-side Comparison | Visual layout showing the currently recorded version next to the newly detected latest version. |
