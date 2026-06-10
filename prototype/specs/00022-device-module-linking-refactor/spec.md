---
spec_type: product
spec_maturity: clarified
epic_id: E022
epic_sources: "{PRD:CAP-001}{SAD:ADR-0009}"
---

# Feature Specification: Device-Module Linking & Refactor

**Epic ID**: E022  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: clarified  
**Epic Sources**: {PRD:CAP-001}{SAD:ADR-0009}  
**Product Document**: specs/prd.md

## Problem Statement

Operators currently assign a free-text device type when creating devices, but the device type should derive from the extension module that knows how to check firmware for that device. The standalone DeviceType entity creates duplication, allows type drift (free-text entries that don't match any installed module), and complicates the check workflow which must later resolve a module anyway. Without this refactor, the module-device relationship remains implicit and the system cannot guarantee that every device has a compatible check module.

## Scope

### Included

- Replace the free-text device type field on device creation/edit with a module selector dropdown.
- Derive the displayed device type from the linked module's display name.
- Database migration: add `module_id` FK to `devices`, backfill from existing `device_type_id`→module match, drop `device_type_id` column.
- Update inventory grouping to use derived module type.
- Remove the `DeviceType` entity, its repository methods, service normalization logic, and related types.
- Show existing devices that cannot be mapped to a module as "unlinked" with reassignment path.

### Excluded

- Changing the module schema or module validation pipeline — E006 owns the module contract.
- Adding new fields to the module entity (e.g., explicit `device_type` field) — module `display_name` is the type.
- Creating a marketplace or module discovery — out of scope per PRD.
- Modifying check/scheduler logic beyond updating FK references — E009/E011 own check execution.

### Edge Cases & Boundaries

- Devices created before migration may have `device_type_id` values with no matching module — show as "unlinked".
- Module is deleted while devices still reference it — devices become unlinked, must be reassigned.
- Operator has no valid installed modules — device creation is blocked with clear guidance to install a module first. Inventory viewing with zero installed modules shows all existing devices under a single "Unlinked" group.
- Module `display_name` changes — device type display updates immediately through the JOIN.
- Schedule records reference `device_type_id` — migration clears schedule rows and drops `device_types` table, ensuring all referencing FKs are resolved before `DROP TABLE`.
- Migration applied against a database that already has `module_id` on `devices` — prevented by `schema_version` tracking; if manually forced, the `ALTER TABLE ADD COLUMN` would fail, requiring backup restore.

## User Scenarios & Testing

### User Story 1 - Create Device with Module Selector (Priority: P1)

The operator creates a new device by selecting an installed module from a dropdown instead of typing a free-text device type. The module determines what firmware source to check; selecting it at creation time makes the relationship explicit and ensures the device has a check-capable module.

**Why this priority**: Core value proposition — replaces the old free-text field with the correct entity relationship. Without this, devices cannot be linked to modules and the refactor fails its purpose.

**Independent Test**: Open the device creation form, observe a module dropdown populated with installed modules, select one, fill remaining fields, submit — device appears in inventory with type derived from the selected module.

**Acceptance Scenarios**:

1. **Given** at least one module with `status: 'installed'` and `validation_status: 'valid'` exists, **When** the operator opens the device creation form, **Then** a module selector dropdown shows all valid installed modules by display name, with a "Select a module..." placeholder.
2. **Given** no valid installed modules exist, **When** the operator opens the device creation form, **Then** the module selector is disabled with guidance to install and validate a module first.
3. **Given** the operator selects a module and submits valid device details, **When** the form is submitted, **Then** the device is created and appears in inventory with the module's display name as its device type.
4. **Given** the operator tries to submit without selecting a module, **When** the form is submitted, **Then** validation prevents creation and shows an error.

### User Story 2 - View Derived Device Type on Existing Devices (Priority: P1)

The operator views device details and sees the device type derived from the linked module, displayed as a read-only field. The device type is not editable — to change it, the device must be linked to a different module.

**Why this priority**: Ensures the refactor's output is visible and trustworthy — device type must always reflect the linked module, never a stale free-text value.

**Independent Test**: View any device in the inventory, observe that its device type matches the linked module's display name and is not an editable field.

**Acceptance Scenarios**:

1. **Given** a device is linked to a module with display name "Sony Alpha", **When** the operator views the device in inventory, **Then** the device type shows "Sony Alpha" as a read-only field.
2. **Given** a device is edited, **When** the operator views the edit form, **Then** the device type is shown as a read-only label next to the module selector (which can be changed).
3. **Given** a module's display name changes, **When** the operator views devices linked to that module, **Then** the displayed device type reflects the updated name.

### User Story 3 - Inventory Grouped by Derived Module Type (Priority: P1)

The inventory view groups devices by their derived module type (the linked module's display name), replacing the old device-type-based grouping. Devices linked to the same module appear together.

**Why this priority**: The inventory grouping is the operator's primary view of their device fleet — it must reflect the new module-derived type to be coherent.

**Independent Test**: View inventory with devices linked to different modules, observe them grouped under their respective module display names.

**Acceptance Scenarios**:

1. **Given** devices are linked to modules "Sony Alpha" and "Panasonic Lumix", **When** the operator views the inventory, **Then** devices appear under "Sony Alpha" and "Panasonic Lumix" group headers.
2. **Given** a device is created and linked to a new module, **When** the operator views the inventory, **Then** a new group appears for that module type.
3. **Given** a device becomes unlinked (module deleted), **When** the operator views the inventory, **Then** the device appears under an "Unlinked" group.

### User Story 4 - Handle Existing Unlinked Devices (Priority: P2)

After migration, devices whose old `device_type_id` could not be matched to an existing module appear as "unlinked". The operator can reassign them by editing and selecting a module.

**Why this priority**: Important for data integrity after migration, but the happy path (new devices) works without it. Most deployments will have matching modules.

**Independent Test**: After migration, verify that devices without a matching module show as "unlinked" and can be reassigned through the edit form.

**Acceptance Scenarios**:

1. **Given** a device's old device type cannot be matched to any module during migration, **When** the operator views inventory, **Then** the device appears with an "Unlinked" status indicator.
2. **Given** an unlinked device exists, **When** the operator edits it and selects a module, **Then** the device becomes linked and appears under that module's type group.
3. **Given** all devices were successfully matched during migration, **When** the operator views inventory, **Then** no "Unlinked" group appears.

## Requirements

### Functional Requirements

- **FR-001**: System MUST present a module selector dropdown (populated from the installed module list) on the device creation and edit forms, replacing the free-text device type field.
- **FR-002**: System MUST derive the displayed device type from the linked module's `display_name` and show it as a read-only field throughout the UI.
- **FR-003**: System MUST execute a database migration that adds `module_id INTEGER REFERENCES modules(id)` to the `devices` table, performs a best-effort backfill from `device_type_id`→module name matching (case-insensitive), drops the `device_type_id` column, drops existing `device_type_schedules` rows (operator reconfigures per-module schedules post-migration), and eventually drops the `device_types` table.
- **FR-004**: System MUST group devices in the inventory view by their derived module type (module `display_name`), with unlinked devices appearing under a separate "Unlinked" group.
- **FR-005**: System MUST remove the `DeviceType` entity — including `device_types` table, `get_or_create_device_type()` repository method, `_device_type_id()` and `normalize_device_type()` service methods, and related Pydantic model fields.
- **FR-006**: System MUST allow the operator to reassign an unlinked device to a module through the edit form.
- **FR-007**: System MUST reject device creation when no valid installed modules exist, with clear user-facing guidance.
- **FR-008**: System MUST handle module deletion gracefully — before deleting a module, the application MUST set `module_id = NULL` on all referencing devices within a single transaction alongside the `DELETE FROM modules`, so devices become unlinked rather than causing errors. The FK constraint uses no `ON DELETE CASCADE` or `ON DELETE SET NULL` clause; application-level cascade gives control for logging. The number of devices unlinked during deletion MUST be logged.
- **FR-009**: System MUST create a verified pre-migration backup snapshot before executing destructive schema changes in migration 007; failure to create or verify the backup SHALL halt the migration. The rollback procedure is: restore the backup snapshot over the database file and restart the application. The `schema_version` table in the restored backup ensures the correct pre-007 schema state.
- **FR-010**: Migration 007 SHALL be forward-only (no DOWN script). The `MigrationRunner`'s `schema_version` tracking prevents re-application of migration 007 after a successful run — idempotency is enforced at the runner layer, not in the SQL itself. If applied to a database where the migration partially succeeded, the operator must restore the pre-migration backup and re-apply.
- **FR-011**: System MUST enable `PRAGMA foreign_keys = ON` during migration execution and at application runtime to enforce foreign key constraints at the database level.
- **FR-012**: System MUST reject device creation/update when the provided `moduleId` references a non-existent module with error code `module_not_found`, distinct from `module_not_valid` (module exists but is not installed+valid) and `module_id_required` (missing or empty `moduleId`).
- **FR-013**: The scheduler SHALL safely idle (no crash, no tight loop) when `list_schedules()` returns an empty list after migration 007 clears the `device_type_schedules` table.
- **FR-014**: Archived devices MUST preserve their `module_id` value; unarchiving a device SHALL restore its original module link without requiring operator reassignment.

## Key Entities

- **Device**: Updated to carry `module_id` (FK to `modules.id`) instead of `device_type_id`. Device type is derived at query time via JOIN with `modules.display_name`. The `DeviceRecord` and `DeviceResponse` carry `module_id` and `device_type` (derived string).
- **Module**: Existing entity from E006/E008. `id` (integer PK) becomes the FK target on `devices`. `display_name` provides the derived device type string. No schema changes to the modules table.

## Assumptions & Risks

### Assumptions

- The existing migration runner's pre-migration backup snapshot provides rollback safety; failure to create the backup is a hard stop per FR-009.
- Module `display_name` values are stable enough to serve as device type labels (renames are acceptable since they propagate through JOIN).
- The `module_id` in the backend `modules` table (`id` INTEGER PRIMARY KEY) is the correct FK target (not the string `module_id`). The `modules.id` PK is a stable auto-increment integer that does not change across module updates or re-installs.
- All existing devices in test/production databases can be best-effort matched to modules by comparing `device_types.name` to `modules.display_name`.
- At the expected scale of 5–50 devices, the in-transaction migration duration is negligible (sub-second); the single-transaction design is safe at this volume.
- The `device_type_schedules` table structure is retained (rows cleared) for future per-module scheduling; this avoids a later migration needing to recreate a dropped table.

### Risks

- **Some devices cannot be auto-matched during migration** *(likelihood: medium, impact: low)*: Devices with type names that don't match any module will be unlinked. Mitigated by FR-006 (reassignment UI).
- **Module deletion breaks device links** *(likelihood: low, impact: medium)*: Deleting a module that devices reference requires handling. Mitigated by FR-008 (transactional unlinking before DELETE, logged).
- **Schedule FK migration conflicts** *(likelihood: low, impact: high)*: The `device_type_schedules` table references `device_types(id)`. Mitigated by clearing schedule rows before dropping `device_types`, with forward-only migration design and pre-migration backup (FR-009).

## Implementation Signals

- `MIGRATION` — New numbered migration (`007_module_linking.sql`) adding `module_id` FK, backfilling data, dropping old column, and updating schedule FK.
- `BREAKING-CHANGE` — `DevicePayload.device_type` field replaced by `module_id`; `DeviceResponse.device_type_id` replaced by `module_id`. Frontend types and API consumers must update.
- `NEW-UI` — Module selector dropdown replaces free-text device type input on device create/edit form.
- `NEW-API` — Updated `/api/v1/inventory` endpoints with new request/response shapes.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: Operator can create a device by selecting a module from a dropdown populated with installed modules, and the device appears in inventory with the correct derived type.
- **SC-002** [US2]: All device type displays show the linked module's name as a read-only value, with zero stale or free-text type values.
- **SC-003** [US3]: The inventory view groups all devices under their derived module type headers, with no orphaned groups.
- **SC-004** [US3]: Devices with unlinked modules appear under an "Unlinked" group and can be reassigned via the edit form.
- **SC-005** [US4]: Database migration applies without errors and all backfill-able devices are correctly linked to modules, with unmatchable devices appearing as unlinked.
- **SC-006** [US1]: The old device-type text field and any standalone DeviceType API surfaces are completely removed — the operator interacts only with the module selector for device type.

## Glossary

| Term | Definition |
|------|------------|
| Module Selector | A dropdown UI element on the device form that lists installed extension modules by `display_name`, replacing the free-text device type field |
| Derived Device Type | The device type displayed to the operator, obtained by JOINing the `modules` table on `module_id` and reading `display_name` |
| Unlinked Device | A device whose `module_id` is NULL — either from migration when no match was found, or after its linked module was deleted |
| Device-Module Link | The explicit FK relationship (`devices.module_id → modules.id`) that replaces the standalone `device_type_id` |

## Compliance Check

**Target**: `specs/00022-device-module-linking-refactor/spec.md`  
**Date**: 2026-06-04  
**Auditor**: PolicyAuditor  

**Verdict: PASS** — No CRITICAL violations. Two MEDIUM findings addressed (F1: Key Entities section present per spec-authoring guide allowance; F2: reworded SC-002 to remove implementation-level detail).

### Per-Document Results

| Document | Verdict |
|----------|---------|
| `.github/sddp-config.md` | PASS |
| `AGENTS.md` | PASS |
| `.github/skills/artifact-conventions/SKILL.md` | PASS |
| `specs/prd.md` (CAP-001 alignment) | PASS |
| `specs/sad.md` (ADR-0009 alignment) | PASS |
| `project-instructions.md` | PASS |

## Clarifications

### Session 2026-06-04

- Q: How should migration handle device_type_schedules FK when replacing device_type_id? → A: Drop existing schedule rows; operator reconfigures per-module schedules post-migration.
- Q: Which modules appear in the device form selector? → A: Only modules with status='installed' AND validation_status='valid'.

## Stress-Test Findings

### Session 2026-06-04

- **STF-001** (MEDIUM, boundary-scale-stress): Module selector dropdown may become unwieldy when >10 valid installed modules exist. Affected: US1 acceptance scenario. Resolution: deferred to plan — implement client-side filter/search on module selector dropdown as a P2 enhancement. MVP supports up to ~10 modules without search.
