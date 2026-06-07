---
feature_branch: "00027-per-module-frequency-on-modules"
created: "2026-06-07"
input: "E026 Per-Module Frequency on Modules Page"
spec_type: "product"
spec_maturity: "clarified"
epic_id: "E026"
epic_sources: "{PRD:CAP-004}"
---

# Feature Specification: Per-Module Frequency on Modules Page

**Feature Branch**: `00027-per-module-frequency-on-modules`  
**Created**: 2026-06-07  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: clarified  
**Epic ID**: E026  
**Epic Sources**: {PRD:CAP-004}  
**Product Document**: specs/prd.md

## Problem Statement

The Modules page displays module metadata (name, version, validation status) but hides check frequency. An operator reviewing or managing modules cannot see at a glance how often each module's devices are checked, nor change that frequency without navigating to a separate location. This fragments the module-management workflow and adds unnecessary friction to a common tuning action.

## Scope

### Included

- Display each module's current automatic check frequency (interval and enabled/disabled status) on the Modules page card
- Allow the operator to edit the check frequency inline from each module card via a preset picker (1h, 6h, 12h, 24h, Custom minutes)
- Enable or disable automatic checking per module from the Modules page
- Changes persist immediately, survive container restarts, and take effect in the running scheduler

### Excluded

- Per-device frequency configuration — the module defines the device type; per-module frequency is the canonical setting per ADR-0009
- Bulk editing of multiple module frequencies at once — single-module inline editing only
- Custom cron-like scheduling expressions — interval minutes with presets covers the use case

### Edge Cases & Boundaries

- A module with no existing schedule row (never been configured) displays the system default (24h / disabled) and creates the row on first edit
- Changing frequency while a scheduled check is in progress does not interrupt the running check; the new interval takes effect on the next trigger
- Toggling the enabled switch while a check is in progress does not interrupt the running check; the disabled state takes effect by preventing the next scheduled trigger
- Rapid frequency changes in succession apply the most recent value via last-write-wins (the PUT endpoint is idempotent); the data-fetching layer updates the display on the next query invalidation cycle
- Deleting a module removes its schedule row via existing cascade or cleanup logic
- If a module is deleted (by another tab or admin action) while its frequency editor is open, a subsequent save attempt returns a 404; the editor displays an error toast ("Module no longer exists"), reverts the editor to display mode, and the module card is removed from the page on the next data refresh

## User Scenarios & Testing

### User Story 1 - View Check Frequency on Modules Page (Priority: P1)

The operator opens the Modules page and sees, for each installed module, the current automatic check interval and whether scheduled checking is enabled. This gives an at-a-glance view of the monitoring configuration without navigating elsewhere.

**Why this priority**: Without visible frequency, the operator cannot know the current configuration. Display is the prerequisite for editing.

**Independent Test**: Open the Modules page — each module card shows its check interval label and enabled/disabled status.

**Acceptance Scenarios**:

1. **Given** a module with an existing schedule (enabled, 360 min), **When** the operator views the Modules page, **Then** the module card displays "6h" and an enabled indicator.
2. **Given** a module with no existing schedule row, **When** the operator views the Modules page, **Then** the module card displays the default interval ("24h") and a disabled indicator.
3. **Given** the Modules page is loading schedule data, **When** the operator views the page, **Then** a loading skeleton is shown for the frequency field until data arrives.
4. **Given** schedule data fails to load, **When** the operator views the Modules page, **Then** an error indicator ("Failed to load") appears inline in the frequency field area of all module cards on the current page with a retry button that reloads the full module list.

### User Story 2 - Edit Check Frequency Inline (Priority: P1)

The operator clicks the frequency display on a module card and changes the automatic check interval using preset buttons (1h, 6h, 12h, 24h) or a custom minute value. The change persists immediately and the scheduler adopts the new interval.

**Why this priority**: This is the core action the feature exists to enable. Without editing, the display alone has no operational value.

**Independent Test**: Click the frequency on a module card, select "12h" — the card updates, the scheduler reschedules, and the change survives a page reload.

**Acceptance Scenarios**:

1. **Given** a module card showing "24h" frequency, **When** the operator clicks the frequency display, **Then** preset buttons (1h, 6h, 12h, 24h, Custom) appear as an inline editor.
2. **Given** the frequency editor is open, **When** the operator selects "6h", **Then** the preset is highlighted, a save indicator appears, and the card updates to "6h" after the API call succeeds.
3. **Given** the frequency editor is open, **When** the operator selects "Custom" and enters "90" minutes, **Then** the card updates to "90m" and the scheduler adopts a 90-minute interval.
4. **Given** the frequency editor is open, **When** the operator toggles the enabled/disabled switch, **Then** the scheduler enables or disables checking for that module synchronously within the API request.
5. **Given** the frequency editor is open, **When** the operator clicks outside the editor (blur), **Then** the editor closes without saving and the display reverts to the previous value.
6. **Given** the frequency editor is open with Custom selected, **When** the operator enters a value outside 1–10080 or a non-integer (e.g., "0", "abc"), **Then** an inline validation error is shown and save is blocked until a valid integer is provided.
7. **Given** the frequency editor is open, **When** the operator presses Escape, **Then** the editor closes without saving and the display reverts to the previous value.
8. **Given** an API error occurs during save, **When** the frequency change fails, **Then** the editor reverts to the previous value and an error toast is shown.
9. **Given** the frequency editor is open for module A, **When** the underlying schedule data changes externally (e.g., another tab saves a different value), **Then** the editor surfaces the updated value, closes, and the card refreshes to show the new value with a notification that auto-dismisses after 5 seconds.

## Requirements

### Functional Requirements

- **FR-001**: System MUST display each module's current check interval as a human-readable label and enabled/disabled status on the Modules page card. Label format: when intervalMinutes is evenly divisible by 60, display as hours (e.g., 60→"1h", 360→"6h", 1440→"24h"); otherwise display as minutes (e.g., 30→"30m", 90→"90m").
- **FR-002**: System MUST allow the operator to change a module's check interval via preset buttons mapping to standard intervals (1h=60, 6h=360, 12h=720, 24h=1440) and a custom minute input constrained to integers 1–10080. Values outside this range or non-integer inputs MUST show an inline validation error and block save until corrected.
- **FR-003**: System MUST allow the operator to enable or disable automatic checking per module from the Modules page card. Disabling retains the configured interval value; re-enabling restores the previously configured interval.
- **FR-004**: System MUST persist frequency changes via the existing schedule API and notify the running background scheduler to adopt the new interval using the existing synchronous reschedule mechanism.
- **FR-005**: System MUST show the system default interval (24 hours, disabled) for modules that have no existing schedule record, and create the record on first edit.
- **FR-006**: System MUST include each module's schedule data (interval, enabled status) in the Modules list response so the page can render frequency without additional per-module requests. For installations exceeding 100 modules, the response MUST be paginated with a default page size of 100.

## Assumptions & Risks

### Assumptions

- The `device_type_schedules` table FK to `device_types` has been semantically repurposed to `modules.id` per migration 007, so `device_type_id` in the schedule API is already a module identifier.
- The existing `PUT /api/v1/schedules/device-types/{id}` endpoint handles upsert (creates a row on first write), so no new API endpoint is needed.
- The Modules page card grid layout has enough space to accommodate the frequency control without a redesign.

### Risks

- **Schedule API naming gap** *(likelihood: low, impact: low)*: The schedule endpoints still use the parametric name `device_type_id` which is semantically `module_id` post refactor. This may confuse developers but does not block the feature; renaming is a separate cleanup concern.

## Implementation Signals

- **NEW-UI**: Frequency display and inline editor component on each module card — preset buttons, custom input, enabled toggle, save/error state.
- **NEW-API**: The Modules list endpoint response is extended to include per-module schedule data (interval, enabled status) alongside existing module metadata.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: Every module card on the Modules page displays a human-readable check frequency label that matches the persisted schedule interval.
- **SC-002** [US2]: Changing a module's frequency via the inline editor results in the scheduler adopting the new interval immediately (via the synchronous reschedule mechanism), and the change persists across page reload and container restart.
- **SC-003** [US2]: The inline editor opens, saves, cancels, and handles API errors without leaving the card in an inconsistent state.

## Compliance Check

### Instructions Check Report
**Target**: `spec.md`
**Status**: PASS

| Principle | Verdict |
|-----------|---------|
| I. Honest Failure | PASS |
| II. Polite by Default | N/A |
| III. Data Ownership & Self-Containment | PASS |
| IV. Least-Privilege & Explicit Trust Boundary | N/A |
| V. Type Safety & Correctness-First | N/A |
| VI. Set-and-Forget Reliability | PASS |
| VII. Agent Output Style | N/A |

**Artifact conventions**: All required sections present, IDs well-formed, size ≤ 10 KB. No violations.

## Clarifications

### Session 2026-06-07

- Q: How should the running background scheduler pick up the change? → A: Synchronous in-process: the API handler calls the scheduler's reschedule method directly after the DB write, and the request completes only after both succeed.
- Q: What formatting logic should the frontend use for frequency labels? → A: Hours when evenly divisible by 60, otherwise minutes: 60→"1h", 360→"6h", 1440→"24h", 30→"30m", 90→"90m".
- Q: What happens to the interval value when disabled and later re-enabled? → A: The interval is retained in the database; re-enabling restores the previously configured interval.
- Q: How should out-of-range or invalid custom input be handled? → A: Inline validation on blur/input: show error text below the field while keeping the editor open; save is blocked until input is valid.
- Q: What should happen when the operator clicks outside the open editor? → A: Close without saving (same as Escape) — the operator must explicitly click a preset or save button to commit changes.
- Q: What should the UI show when schedule data fails to load? → A: Show an error indicator inline in the frequency field area of each affected card, with a retry option.

## Stress-Test Findings

### Session 2026-06-07

- **STF-001** [HIGH] **Concurrent-trigger ambiguity: stale data during edit**: No conflict-resolution rule for viewing schedule data while inline editor is open. *Resolution*: Added acceptance scenario US2-9 — when underlying data changes externally while editor is open, the editor surfaces the updated value and closes with a notification.
- **STF-002** [HIGH] **Constraint impossibility: scheduler adoption timing**: Background scheduler adoption within one request cycle was architecturally ambiguous. *Resolution*: Clarified FR-004 to use the existing synchronous reschedule mechanism; relaxed SC-002 to "immediately (via the synchronous reschedule mechanism)".
- **STF-003** [MEDIUM] **Custom input validation gap**: Boundary validation and label format for non-preset values were unspecified. *Resolution*: Added FR-002 validation constraint and acceptance scenario US2-6 for out-of-range inputs; defined label format in FR-001.
- **STF-004** [MEDIUM] **Disable during running check**: Toggling enabled state while check in progress had undefined behavior. *Resolution*: Extended edge cases — the disabled state takes effect by preventing the next scheduled trigger, not interrupting the running check.
- **STF-005** [MEDIUM] **Unbounded modules list response**: FR-006 included per-module schedule data with no upper bound. *Resolution*: Added pagination requirement to FR-006 for installations exceeding 100 modules.

## Glossary

| Term | Definition |
|------|------------|
| Interval / Frequency | The time in minutes between automatic scheduled checks for devices linked to a module; persisted in `device_type_schedules.interval_minutes`. |
| Inline editor | A UI control that replaces a static display with interactive inputs (buttons, select, toggle) within the same card, without a modal or page navigation. |
