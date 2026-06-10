---
feature_branch: "00006-device-inventory-management"
created: "2026-06-10"
input: "E006 Device inventory management with module-linked devices, stored versions, update confirmation, full CRUD API + UI"
spec_type: "product"
spec_maturity: "clarified"
epic_id: "E006"
epic_sources: "{PRD:CAP-001}{SAD:ADR-0009}"
---

# Feature Specification: Device Inventory Management

**Feature Branch**: `00006-device-inventory-management`
**Created**: 2026-06-10
**Status**: Draft
**Spec Type**: product
**Spec Maturity**: clarified
**Epic ID**: E006
**Epic Sources**: {PRD:CAP-001}{SAD:ADR-0009}
**Product Document**: specs/prd.md

## Problem Statement

Binocular has a running application skeleton (E001), data layer (E002), frontend shell (E004), and scraping client (E005), but no way for operators to register the devices they want to monitor. Without a device inventory, no firmware-update checks can be configured, scheduled, or reported — the core value proposition is unreachable. Operators need to create, view, edit, and remove device records linked to detection modules, and to confirm when they have applied a detected update.

## Scope

### Included

- Device database table with `module_id` foreign key (module-derived device type per ADR-0009)
- Full CRUD REST API at `/api/v1/devices` (POST, GET list, GET by ID, PUT, DELETE)
- Dedicated update confirmation endpoint `PUT /api/v1/devices/{id}/confirm`
- Repository, service, and router layers following established backend patterns
- Pydantic request/response models with validation
- Frontend InventoryPage replacing the placeholder with live data
- DeviceCard component showing device name, model, module-derived type, version, update status
- StatCard component showing inventory summary counts (total devices, devices with updates, devices checked)
- DeviceForm component with module selection dropdown for add/edit workflows
- Empty-state UI when no devices exist

### Excluded

- Module CRUD (E009) — this epic consumes modules as read-only for the FK dropdown
- Firmware update detection logic (E010) — `has_update` and `latest_detected_version` are set by the detection engine, not by this epic
- Scheduled or manual check triggering (E012, E013) — inventory provides the device list, not the check flow
- Notification dispatch on update detection (E014) — downstream consumer
- Bulk import/export of devices — deferred to a future enhancement
- Device grouping or tagging — not part of initial inventory

### Edge Cases & Boundaries

- Creating a device with a non-existent `module_id` returns 422 with a clear error message
- Deleting a device that has pending update notifications is allowed (cascade cleanup is the notifier's responsibility in E014)
- Device names need not be unique — operators may have multiple identical devices
- Confirming an update on a device with `has_update = false` is a no-op returning 200
- Maximum device count is not enforced (SQLite handles practical limits)
- Module deletion while devices reference it: the modules table does not yet exist (E007 creates it) — the FK constraint uses `ON DELETE RESTRICT` so module deletion is blocked while devices reference it

## User Scenarios & Testing

### User Story 1 - Register a New Device (Priority: P1)

The operator opens the Inventory page, clicks "Add Device", fills in the device name and model, selects the monitoring module from a dropdown, enters the current firmware version, and saves. The device appears in the inventory list with its module-derived device type displayed.

**Why this priority**: Core value proposition — without device registration, no monitoring can occur.

**Independent Test**: Create a device via the form and verify it appears in the inventory list with correct details.

**Acceptance Scenarios**:

1. **Given** the operator is on the Inventory page, **When** they click "Add Device" and submit the form with valid data, **Then** the new device appears in the list with name, model, module-derived type, and current version displayed.
2. **Given** the operator submits the device form without a name, **When** the form validates, **Then** a validation error is shown and no device is created.
3. **Given** no modules exist in the system, **When** the operator opens the "Add Device" form, **Then** the module dropdown is empty and the form shows a message indicating modules must be added first.

### User Story 2 - View Device Inventory (Priority: P1)

The operator opens the Inventory page and sees a summary of their monitored devices at a glance: total count, how many have available updates, and when devices were last checked. Each device is displayed as a card showing key details.

**Why this priority**: Core value proposition — the inventory view is the primary dashboard for device monitoring status.

**Independent Test**: With several devices in the database, load the Inventory page and verify summary stats and device cards render correctly.

**Acceptance Scenarios**:

1. **Given** three devices exist (one with `has_update = true`), **When** the operator opens the Inventory page, **Then** stat cards show "3 Devices", "1 Update Available", and device cards display each device's details.
2. **Given** no devices exist, **When** the operator opens the Inventory page, **Then** an empty-state message is shown with a prompt to add the first device.

### User Story 3 - Edit Device Details (Priority: P1)

The operator selects an existing device, modifies its name, model, module assignment, or current version, and saves the changes.

**Why this priority**: Blocks day-one utility — operators need to correct registration errors and update device details as their setup evolves.

**Independent Test**: Edit a device's name and module, save, and verify the updated values appear in the inventory list.

**Acceptance Scenarios**:

1. **Given** a device exists, **When** the operator edits its name and saves, **Then** the updated name is displayed in the device card.
2. **Given** a device exists, **When** the operator changes its module assignment, **Then** the displayed device type updates to reflect the new module's type.

### User Story 4 - Remove a Device (Priority: P1)

The operator selects a device and deletes it. The device is removed from the inventory and no longer appears in future check cycles.

**Why this priority**: Core lifecycle — operators must be able to decommission devices they no longer want to monitor.

**Independent Test**: Delete a device and verify it no longer appears in the inventory list.

**Acceptance Scenarios**:

1. **Given** a device exists, **When** the operator clicks delete and confirms, **Then** the device is removed from the list and the stat cards update.

### User Story 5 - Confirm a Firmware Update (Priority: P2)

When the detection engine (E010) finds a newer firmware version, the device card shows an update indicator. The operator clicks "Confirm Update" to acknowledge they have applied the update, which sets the device's current version to the detected version and clears the update flag.

**Why this priority**: Enhances P1 flows — without confirmation, the inventory would perpetually show stale update alerts. MVP works with manual version editing as a workaround.

**Independent Test**: Set a device to `has_update = true` with a `latest_detected_version`, confirm the update, and verify `current_version` equals the detected version and `has_update` is cleared.

**Acceptance Scenarios**:

1. **Given** a device has `has_update = true` and `latest_detected_version = "2.0"`, **When** the operator clicks "Confirm Update", **Then** `current_version` becomes "2.0", `has_update` becomes false, and the update indicator disappears.
2. **Given** a device has `has_update = false`, **When** the confirm endpoint is called, **Then** the response is 200 with no changes.

## Requirements

### Functional Requirements

- **FR-001**: System MUST store devices with fields: `id`, `name`, `model`, `module_id`, `current_version`, `has_update`, `latest_detected_version`, `last_checked`, `last_notified_version`, `created_at`, `updated_at`.
- **FR-002**: System MUST provide `POST /api/v1/devices` to create a device, validating that `module_id` references an existing module.
- **FR-003**: System MUST provide `GET /api/v1/devices` to list all devices with `module_id`, `module_name`, and `device_type` as flat fields on the response.
- **FR-004**: System MUST provide `GET /api/v1/devices/{id}` to retrieve a single device.
- **FR-005**: System MUST provide `PUT /api/v1/devices/{id}` to update device fields.
- **FR-006**: System MUST provide `DELETE /api/v1/devices/{id}` to remove a device.
- **FR-007**: System MUST provide `PUT /api/v1/devices/{id}/confirm` to set `current_version = latest_detected_version`, `has_update = false`.
- **FR-008**: System MUST return 404 for operations on non-existent device IDs.
- **FR-009**: System MUST return 422 when `module_id` references a non-existent module.
- **FR-010**: System MUST display an InventoryPage with StatCard summary and DeviceCard list.
- **FR-011**: System MUST provide a DeviceForm with module selection dropdown for creating and editing devices.
- **FR-012**: System MUST show an empty-state view when no devices exist.

### Key Entities

- **Device**: A firmware-tracked hardware item. Attributes: `id` (integer PK), `name` (text, required), `model` (text, optional), `module_id` (FK to modules), `current_version` (text), `has_update` (boolean, default false), `latest_detected_version` (text, nullable), `last_checked` (ISO datetime, nullable), `last_notified_version` (text, nullable), `created_at` (ISO datetime), `updated_at` (ISO datetime). Device type is derived from the linked module's `device_type` field — not stored on the device itself.

## Assumptions & Risks

### Assumptions

- The E006 migration creates a minimal `modules` table (`id`, `name`, `device_type`, `created_at`) using `CREATE TABLE IF NOT EXISTS`, so E006 can be implemented before E007. E007 will extend this table with additional columns via `ALTER TABLE`.
- Device names are free-text and need not be unique across the inventory.
- The `has_update`, `latest_detected_version`, and `last_checked` fields are written by the detection engine (E010) and read-only from the inventory UI perspective (except for the confirm action).
- Frontend uses TanStack Query for data fetching and React Hook Form for the DeviceForm, consistent with the tech stack established in E004.

### Risks

- **Module table dependency** *(likelihood: low, impact: low)*: Resolved — E006 migration creates the minimal modules table with `CREATE TABLE IF NOT EXISTS`. E007 extends it.
- **Schema migration ordering** *(likelihood: low, impact: medium)*: E006 and E007 both add migrations. Non-overlapping migration numbers must be allocated. Mitigation: E006 uses `0002_devices.sql`.
- **Large inventories** *(likelihood: low, impact: low)*: Unbounded device lists may slow page loads for operators with many devices. Mitigation: defer pagination to a future enhancement; practical device counts for self-hosters are low.

## Implementation Signals

- `MIGRATION` — new `devices` table migration (`0002_devices.sql`)
- `NEW-ENTITY` — Device domain entity with Pydantic models
- `NEW-API` — `/api/v1/devices` CRUD routes and `/api/v1/devices/{id}/confirm`
- `NEW-UI` — InventoryPage with DeviceCard, StatCard, DeviceForm components

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: An operator can register a new device linked to a module and see it in the inventory within one page interaction.
- **SC-002** [US2]: The Inventory page displays accurate summary statistics and all registered devices upon loading.
- **SC-003** [US3]: An operator can edit any device field and see the change reflected immediately.
- **SC-004** [US4]: An operator can delete a device and it no longer appears in the inventory.
- **SC-005** [US5]: Confirming an update sets `current_version` to the detected version and clears the update indicator.
- **SC-006** [US1]: All CRUD endpoints return appropriate HTTP status codes (201, 200, 404, 422) and are covered by automated tests.

## Glossary

| Term | Definition |
|------|------------|
| Device | A firmware-tracked hardware item registered in Binocular's inventory, linked to a detection module. |
| Module-derived device type | The device category (e.g., "Camera", "Flash") determined by the detection module the device is linked to, per ADR-0009. |
| Update confirmation | The operator action acknowledging a detected firmware update has been applied, clearing the update flag. |

## Clarifications

### Session 2026-06-10

- Q: Should E006 create a minimal modules seed table or use deferred FK? -> A: E006 migration creates a minimal modules table (id, name, device_type, created_at) using CREATE TABLE IF NOT EXISTS.
- Q: Should the device list API response include full module object or flat fields? -> A: Include module_id, module_name, and device_type as flat fields on the device response (JOIN in query).
- Q: What non-functional expectations apply to API endpoints? -> A: Standard local-network expectations (< 500ms for list, < 200ms for single), no explicit SLA — consistent with trusted-LAN deployment model.

## Compliance Check

### Instructions Check Report
**Target**: spec.md
**Status**: PASS

| Principle | Verdict | Notes |
|-----------|---------|-------|
| I. Honest Failure | N/A | No runtime behavior specified at spec level |
| II. Polite by Default | N/A | No outbound scraping in inventory epic |
| III. Data Ownership | PASS | SQLite storage, no external dependencies |
| IV. Least-Privilege | N/A | No container/permission changes |
| V. Type Safety | PASS | Pydantic models + strict typing implied |
| VI. Set-and-Forget | PASS | Auto-migration, zero-config defaults |
| VII. Agent Output Style | N/A | Spec is user-facing artifact |
