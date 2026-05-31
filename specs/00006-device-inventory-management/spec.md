---
spec_type: product
epic_id: E005
epic_sources: [PRD:CAP-001]
spec_maturity: clarified
---

# Feature Specification: Device Inventory Management

## Problem Statement

Binocular cannot watch firmware without durable records of owned devices and recorded firmware versions. The SPA shell currently shows mock inventory only, so later checking, comparison, notification, and update-confirmation workflows have no reliable source of truth.

## Scope

### Included

- Create, view, edit, and delete offline device records.
- Group inventory by device type for later module/check workflows.
- Store user-recorded current firmware versions as opaque strings.
- Reuse device type groups by trimmed, case-insensitive display name matching.
- Confirm that a device has been physically updated and sync the recorded version to the known latest version when available.
- Show honest empty, validation, and not-yet-checked states in the UI.

### Excluded

- Module selection and execution — E006 owns module contracts.
- Automated latest-version detection — E009 owns comparison semantics.
- Scheduled or manual checks — E010 and E011 own check execution.
- Notifications — E012 owns outbound alerting.

### Edge Cases & Boundaries

- A device may have no latest version yet; the UI must not call it up to date.
- Firmware versions may contain letters, punctuation, leading zeroes, or labels.
- Deleting archives a device out of active inventory for future auditability.
- Duplicate names are allowed when model or serial-like details differ, but required fields must be validated.
- The initial UI and API should behave predictably for at least 50 active devices without pagination.

## User Scenarios & Testing

### User Story 1 - Maintain Device Records (Priority: P1)

The operator can add owned offline devices with name, model, type, and current firmware version, then edit mistakes later.

**Why this priority**: P1 because all later check, comparison, and notification value depends on persistent device records.

**Independent Test**: Create a device, reload the app, edit the device, and verify the updated record remains visible in the grouped inventory.

**Acceptance Scenarios**:

1. **Given** an empty inventory, **When** the operator creates a valid device, **Then** the device appears under its device type with the recorded firmware version.
2. **Given** an existing device, **When** the operator edits its name, model, type, or recorded version, **Then** the updated values persist after refresh.
3. **Given** a required field is blank, **When** the operator submits the form, **Then** the UI identifies the field error and does not create an invalid record.
4. **Given** the operator enters an existing device type with different capitalization or surrounding spaces, **When** the device is saved, **Then** it appears in the existing group rather than creating a duplicate group.

### User Story 2 - Scan Grouped Inventory (Priority: P1)

The operator can see devices grouped by type with status context that distinguishes tracked, never-checked, and checked devices.

**Why this priority**: P1 because grouped inventory is the operator's main mental model and the dependency contract for module-based checks.

**Independent Test**: Add devices across multiple device types and verify the inventory presents stable groups, counts, versions, and unknown check states.

**Acceptance Scenarios**:

1. **Given** devices of several types, **When** the operator opens inventory, **Then** devices are grouped by type with counts and recorded versions.
2. **Given** a device has never been checked, **When** it appears in the inventory, **Then** the status clearly says it has not been checked rather than up to date.

### User Story 3 - Confirm Physical Updates (Priority: P2)

After installing firmware, the operator can confirm the update so the recorded version matches the latest known version.

**Why this priority**: P2 because it completes the inventory lifecycle but depends on latest-version information that later detection epics enrich.

**Independent Test**: Set a device with a known latest version, confirm update, and verify the recorded version changes to the latest value.

**Acceptance Scenarios**:

1. **Given** a device has a latest detected version different from its recorded version, **When** the operator confirms the physical update, **Then** the recorded version becomes the latest detected version.
2. **Given** no latest detected version exists, **When** the operator views the device, **Then** update confirmation is unavailable or clearly explains why it cannot run.

## Requirements

### Functional Requirements

- **FR-001**: System MUST allow operators to create device records with name, model, device type, and current firmware version.
- **FR-002**: System MUST allow operators to edit existing device records without changing the device identity.
- **FR-003**: System MUST allow operators to delete device records from the active inventory.
- **FR-004**: System MUST persist inventory records in the local SQLite data volume.
- **FR-005**: System MUST display inventory grouped by device type with per-group counts.
- **FR-006**: System MUST store firmware versions as opaque strings without numeric coercion.
- **FR-007**: System MUST distinguish never-checked, check-failed, update-available, and up-to-date states when that state data exists.
- **FR-008**: System MUST allow update confirmation only when a latest known version is available for the device.
- **FR-009**: System MUST update the recorded firmware version to the latest known version when the operator confirms a physical update.
- **FR-010**: System MUST show accessible validation errors for missing or invalid required fields.
- **FR-011**: System MUST reuse device type groups by trimmed, case-insensitive display name matching.
- **FR-012**: System MUST keep deleted devices out of active inventory views without requiring hard deletion of historical identity.

### Key Entities

- **Device Type**: User-visible group for devices sharing a firmware source or module boundary.
- **Device**: Owned hardware item with name, model, type, recorded version, and timestamps.
- **Firmware Version**: Vendor-specific version label recorded as text.
- **Update Confirmation**: User action recording a physical firmware update after it happens.

## Assumptions & Risks

### Assumptions

- Operators manage a modest single-user inventory of roughly 5-50+ devices.
- Device type can initially be user-entered text and later linked to modules.
- Latest-version fields may be absent until detection features land.
- SQLite migrations from E004 are available and append-only.

### Risks

- **Premature coupling to modules** *(likelihood: medium, impact: medium)*: Inventory could block on E006 if device type is over-modeled; keep grouping simple for this epic.
- **Version-format bugs** *(likelihood: medium, impact: high)*: Numeric coercion can corrupt vendor versions; store opaque strings.
- **Misleading status language** *(likelihood: low, impact: high)*: Unknown checks could appear successful; require explicit never-checked state.

## Implementation Signals

- `NEW-ENTITY` — Device type/group and device inventory records.
- `MIGRATION` — Append-only SQLite migration for inventory tables and indexes.
- `NEW-API` — CRUD endpoints and update-confirmation action under `/api/v1`.
- `NEW-UI` — Replace mock inventory with persisted grouped list and forms.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: Operators can create, edit, reload, and still see a device with the same recorded version.
- **SC-002** [US1]: Invalid inventory submissions identify the offending fields and create no device.
- **SC-003** [US2]: Inventory displays devices grouped by device type with accurate group counts.
- **SC-004** [US2]: Devices that have never been checked are visibly marked as not yet checked.
- **SC-005** [US3]: Confirming a physical update sets the recorded version to the latest known version and removes the update-needed state.
- **SC-006** [US1]: At least 50 active devices remain readable in grouped inventory without pagination.

## Glossary

| Term | Definition |
|------|------------|
| Device | A single owned offline hardware item tracked by Binocular. |
| Device Type | A user-visible group for devices that share a firmware source or module boundary. |
| Recorded Version | The firmware version the operator says is currently installed. |
| Latest Known Version | The newest firmware version Binocular has detected or been given for a device. |
| Update Confirmation | The operator action that records a physical firmware update after it is applied. |

## Clarifications

### Session 2026-05-31

- Q: Should deleting a device hard-delete it or archive it out of active inventory? -> A: Archive out of active inventory by default.
- Q: Should device type grouping be free-text exact match or normalized reuse? -> A: Reuse groups by trimmed, case-insensitive display name matching.
- Q: What scale boundary should Phase 1 planning validate? -> A: At least 50 active devices without pagination.

## Stress-Test Findings

### Session 2026-05-31

- STF-001: Boundary/Scale Stress (MEDIUM) — Affected: SC-006 — The original spec had no inventory-size validation boundary; resolved by adding SC-006 for at least 50 active devices.

## Compliance Check

### Instructions Check Report
**Target**: spec.md
**Status**: PASS

| Principle | Verdict | Notes |
|-----------|---------|-------|
| Honest Failure | PASS | Never-checked and failed states stay visible. |
| Polite by Default | N/A | No scraping. |
| Data Ownership & Self-Containment | PASS | SQLite local persistence required. |
| Least-Privilege & Explicit Trust Boundary | N/A | No module execution. |
| Type Safety & Correctness-First | PASS | Opaque versions and testable requirements. |
| Set-and-Forget Reliability | PASS | Inventory persists locally. |

**Violations**: None.