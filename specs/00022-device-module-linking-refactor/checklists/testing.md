# Testing Requirements Quality Checklist

**Feature**: E022 — Device-Module Linking & Refactor  
**Spec**: [spec.md](../spec.md)  
**Plan**: [plan.md](../plan.md)  
**Data Model**: [data-model.md](../data-model.md)  
**Contract**: [contracts/inventory-api.md](../contracts/inventory-api.md)  
**Generated**: 2026-06-04

---

## 1. Test Coverage Completeness — Functional Requirement Traceability

- [ ] CHK001 Do tests exist for the module selector dropdown rendering on both create and edit forms, covering the populated and disabled states? [Completeness, Spec §FR-001, Plan §Testing Strategy]
- [ ] CHK002 Is there a test verifying that the displayed device type is derived from the linked module's `display_name` and presented as a read-only field? [Completeness, Spec §FR-002, Spec §US2]
- [ ] CHK003 Does the test suite validate that the database migration `007_module_linking.sql` applies without errors and correctly backfills data? [Completeness, Spec §FR-003, Data-Model §4]
- [ ] CHK004 Are there tests confirming that the inventory view groups devices by module `display_name` and includes a separate "Unlinked" group for NULL `module_id`? [Completeness, Spec §FR-004, Spec §US3]
- [ ] CHK005 Do tests verify that all `DeviceType` entity surfaces — `device_types` table, `get_or_create_device_type()`, `normalize_device_type()`, Pydantic field `deviceTypeId` — are fully removed? [Completeness, Spec §FR-005, Data-Model §6.3]
- [ ] CHK006 Is the unlinked-device reassignment path tested — edit form opens for unlinked device, operator selects a module, device appears under new group? [Completeness, Spec §FR-006, Spec §US4]
- [ ] CHK007 Does a test exist that rejects device creation (400 or disabled UI) when no valid installed modules are present? [Completeness, Spec §FR-007, Spec §US1 Scenario 2]
- [ ] CHK008 Is module deletion tested end-to-end — referencing devices set to `module_id=NULL`, appear as "Unlinked", and no FK constraint violation occurs? [Completeness, Spec §FR-008, Data-Model §5.3]
- [ ] CHK009 Does each test tier (unit, integration, frontend) have at least one test per functional requirement, per the plan's coverage map? [Completeness, Plan §Requirement Coverage Map]
- [ ] CHK010 Are both the `LEFT JOIN modules` query path (unlinked devices included) and the `ORDER BY COALESCE(m.display_name, 'ZZZ_Unlinked')` ordering verified in repository tests? [Completeness, Data-Model §6.1]

## 2. Migration Testing — Safety & Correctness

- [ ] CHK011 Does a migration integration test execute `007_module_linking.sql` against a test database seeded with pre-migration schema, verifying no migration errors? [Safety, Data-Model §4.2, Plan §Testing Strategy]
- [ ] CHK012 Is the best-effort backfill tested with both matchable and unmatchable `device_type_id` values, confirming matched rows get a valid `module_id` and unmatched rows remain NULL? [Correctness, Data-Model §4.2 Step 2, Data-Model §8]
- [ ] CHK013 Does a migration test confirm that the `device_type_id` column is dropped and the `idx_devices_active_type_name` index is removed after migration? [Correctness, Data-Model §4.2 Steps 3–4]
- [ ] CHK014 Is the `device_type_schedules` table verified as empty after migration and the `device_types` table verified as dropped? [Correctness, Data-Model §4.2 Steps 6–7]
- [ ] CHK015 Does a rollback test confirm that restoring the pre-migration backup snapshot restores the database to a working pre-007 state? [Safety, Data-Model §4.4, Spec §Assumptions]
- [ ] CHK016 Are `schema_version` entries validated after migration to confirm version `007` is recorded as applied? [Correctness, Data-Model §4.3]
- [ ] CHK017 Does a migration idempotency test confirm that re-running migration 007 on an already-migrated database does not error (the migration runner skips it)? [Safety, Plan §Technical Context]
- [ ] CHK018 Is the case-insensitive backfill tested with different casing combinations (e.g., `device_types.name = "Sony Alpha"` matches `modules.display_name = "sony alpha"`)? [Correctness, Data-Model §4.2 Step 2, Spec §Edge Cases]

## 3. Edge Case & Boundary Testing

- [ ] CHK019 Does a test cover the scenario where all existing `device_type_id` values have no matching module — every device becomes unlinked and appears under the "Unlinked" group? [Edge Case, Spec §Edge Cases, Spec §US4 Scenario 3]
- [ ] CHK020 Is the scenario tested where a module is deleted while devices reference it — the application sets `module_id=NULL` before `DELETE` and no FK constraint violation occurs? [Edge Case, Spec §Edge Cases, Data-Model §5.3]
- [ ] CHK021 Is the negative case tested where a module is deleted but devices are NOT pre-unlinked, confirming the FK constraint error is surfaced correctly? [Edge Case, Data-Model §8]
- [ ] CHK022 Does a test cover module `display_name` changes — verifying linked devices immediately reflect the updated name on next read without stale cached values? [Edge Case, Spec §Edge Cases, Data-Model §8, Contracts §7]
- [ ] CHK023 Is the zero-valid-modules scenario tested both at the API layer (POST returns 400) and the frontend layer (dropdown disabled with guidance text)? [Edge Case, Spec §FR-007, Contracts §2.2, Spec §US1 Scenario 2]
- [ ] CHK024 Does a test cover device creation with a valid `moduleId` string that maps to a module where `status != 'installed'` or `validation_status != 'valid'` — confirming the 400 `module_not_valid` rejection? [Edge Case, Contracts §2.2, Spec §Clarifications Q2]
- [ ] CHK025 Is the ambiguous backfill match scenario tested — where multiple modules could match the same `device_types.name`, confirming `LIMIT 1` is deterministic? [Edge Case, Data-Model §8, Data-Model §D7]
- [ ] CHK026 Does a test verify that the `idx_devices_active_module_name` index is used for inventory queries after migration? [Boundary, Data-Model §4.2 Step 5]
- [ ] CHK027 Is the archived device path tested — confirming archived devices are excluded from grouped inventory output regardless of `module_id` value? [Edge Case, Data-Model §5.2, Contracts §2.4]
- [ ] CHK028 Does a test cover PATCH on an archived device, confirming the 404 `device_not_found` response? [Edge Case, Contracts §2.3]

## 4. Acceptance Scenario Coverage

- [ ] CHK029 Does a test exist for US1 Scenario 1: module dropdown populated with all valid installed modules by display name with a "Select a module..." placeholder? [Acceptance, Spec §US1 Scenario 1]
- [ ] CHK030 Does a test exist for US1 Scenario 3: submitting the form with a selected module creates the device with the module's display name as device type in inventory? [Acceptance, Spec §US1 Scenario 3]
- [ ] CHK031 Does a test exist for US1 Scenario 4: submitting without selecting a module triggers validation and prevents creation? [Acceptance, Spec §US1 Scenario 4]
- [ ] CHK032 Does a test exist for US2 Scenario 1: viewing a linked device shows the module's display name as a read-only device type field? [Acceptance, Spec §US2 Scenario 1]
- [ ] CHK033 Does a test exist for US2 Scenario 2: the edit form shows device type as a read-only label next to a changeable module selector? [Acceptance, Spec §US2 Scenario 2]
- [ ] CHK034 Does a test exist for US3 Scenario 1: inventory groups devices under "Sony Alpha" and "Panasonic Lumix" headers by module display name? [Acceptance, Spec §US3 Scenario 1]
- [ ] CHK035 Does a test exist for US3 Scenario 3: devices with NULL module_id appear under an "Unlinked" group header? [Acceptance, Spec §US3 Scenario 3]
- [ ] CHK036 Does a test exist for US4 Scenario 1: unmatchable post-migration device shows an "Unlinked" status indicator? [Acceptance, Spec §US4 Scenario 1]
- [ ] CHK037 Does a test exist for US4 Scenario 2: editing an unlinked device and selecting a module relinks it and moves it to that module's group? [Acceptance, Spec §US4 Scenario 2]

## 5. Integration & Contract Testing

- [ ] CHK038 Is the frontend-to-backend API contract tested — verifying that the frontend sends `moduleId` (not `deviceType`) on POST/PATCH and parses `moduleId` (not `deviceTypeId`) from responses? [Integration, Contracts §4, Contracts §6.1-6.3]
- [ ] CHK039 Does an integration test verify that the `POST /api/v1/inventory` endpoint returns 201 with a `DeviceResponse` containing `moduleId` as a string (not integer) and `deviceType` derived from the module? [Integration, Contracts §2.2, Contracts §3.2]
- [ ] CHK040 Do tests validate all documented error response schemas — `module_not_found` (400), `module_not_valid` (400), `module_id_required` (400), `device_not_found` (404), `no_latest_version` (409)? [Integration, Contracts §2.2-2.5, Contracts §5]
- [ ] CHK041 Is the `PATCH /api/v1/inventory/{deviceId}` endpoint tested for successful module reassignment, including the response shape confirming the new `moduleId` and `deviceType`? [Integration, Contracts §2.3]
- [ ] CHK042 Is the `DELETE /api/v1/inventory/{deviceId}` endpoint tested for the breaking change — returning `204 No Content` instead of `{ "success": true, "message": "..." }`? [Integration, Contracts §6.4]
- [ ] CHK043 Is the `POST /api/v1/inventory/{deviceId}/confirm-update` endpoint tested with the new request body `{ "version": string }` and the 409 `no_latest_version` error case? [Integration, Contracts §2.5, Contracts §6.4]
- [ ] CHK044 Do TypeScript type tests confirm that `InventoryDevice.moduleId` is `string | null`, `DeviceInput.moduleId` is `string`, and `DeviceGroup.moduleId` is `string | null` per the contract? [Integration, Contracts §4]

## 6. Frontend Component & Rendering Tests

- [ ] CHK045 Does a frontend test verify that the module selector dropdown is rendered with a `<select>` element and populated from the module list API response? [Frontend, Spec §FR-001, Plan §Testing Strategy]
- [ ] CHK046 Is the module selector disabled state tested — confirming the dropdown is grayed out and the submit button shows guidance when no valid modules exist? [Frontend, Spec §FR-007, Spec §US1 Scenario 2]
- [ ] CHK047 Does a frontend test verify that the device card renders `deviceType` as plain text (not an input/editable field) derived from the module? [Frontend, Spec §FR-002, Spec §US2 Scenario 1]
- [ ] CHK048 Is the "Unlinked" badge rendering tested on device cards where `moduleId` is `null`? [Frontend, Spec §US4 Scenario 1, Contracts §3.2]

## 7. Success Criteria Validation

- [ ] CHK049 Does a test validate SC-001: the full user journey of creating a device with a module selector and seeing it in inventory with the correct derived type? [Success, Spec §SC-001]
- [ ] CHK050 Does a test validate SC-005: the migration applies without errors and all backfill-able devices are correctly linked? [Success, Spec §SC-005]
- [ ] CHK051 Does a test validate SC-006: the old device-type text field and any standalone DeviceType API surfaces are completely absent? [Success, Spec §SC-006]

---

**Total items**: 51  
**Items with traceability refs**: 51 (100%)  
**Status**: Draft — awaiting review
