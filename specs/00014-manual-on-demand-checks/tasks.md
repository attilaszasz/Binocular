# Tasks: Manual On-Demand Checks

**Input**: Design documents from `specs/00014-manual-on-demand-checks/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/`
**Tests**: Included because SC-001 through SC-005 require verifiable manual check outcomes and responsive UI states.

## Project Mode

`Brownfield`

## Epic / Capability Map

- `[US1]` → Check one device now
- `[US2]` → Check all devices now
- `[US3]` → Keep manual checks responsive

## Brownfield Notes

- Existing flows touched: E009 `CheckService`, `/api/v1/checks/devices/{device_id}`, inventory UI, frontend API barrel exports.
- Compatibility or migration concerns: no schema migration; bulk responses are transient and reuse existing device status fields.
- Regression focus: E009 single-device checks, inventory CRUD/confirm-update flows, module lifecycle list/upload/delete flows.

## Phase 1: Foundational (Cross-Work-Item Blockers)

- [X] T001 [P] {FR-003} Add frontend check API contract tests in frontend/src/api/checks.test.ts → exports: check API tests
- [X] T002 {FR-003} Add typed manual check API client in frontend/src/api/checks.ts → exports: runDeviceCheck(), runAllChecks()
- [X] T003 {FR-003} Export manual check API types in frontend/src/api/index.ts after:T002 ← T002:runAllChecks

---

## Phase 2: Work Item 1 - Check One Device Now (Priority: P1) 🎯 MVP

- [X] T004 [US1] {FR-001,FR-004,FR-005} Add single-device UI tests in frontend/src/App.test.tsx after:T002
- [X] T005 [US1] {FR-001} Wire single-device check handler in frontend/src/App.tsx ← T002:runDeviceCheck
- [X] T006 [US1] {FR-004,FR-005} Render manual result status and diagnostics in frontend/src/App.tsx after:T005
- [X] T007 [US1] {FR-001} [COMPLETES FR-001] Add per-device check controls in frontend/src/App.tsx after:T006

---

## Phase 3: Work Item 2 - Check All Devices Now (Priority: P1) 🎯 MVP

- [X] T008 [P] [US2] {FR-002,FR-006,FR-007} Add bulk backend route tests in backend/tests/test_manual_checks.py
- [X] T009 [US2] {FR-002,FR-006,FR-007} Add bulk check service method in backend/src/binocular/services/checks.py → exports: CheckService.run_all_device_checks()
- [X] T010 [US2] {FR-002,FR-006,FR-007} Add all-device route models in backend/src/binocular/routes/checks.py after:T009
- [X] T011 [US2] {FR-002,FR-006,FR-007} [COMPLETES FR-002] Implement POST /api/v1/checks/all in backend/src/binocular/routes/checks.py after:T010
- [X] T012 [US2] {FR-006,FR-007} [COMPLETES FR-006] Verify partial failure and archived exclusion in backend/tests/test_manual_checks.py after:T011

---

## Phase 4: Work Item 3 - Keep Manual Checks Responsive (Priority: P2)

- [X] T013 [US3] {FR-009} Add bulk UI running-state tests in frontend/src/App.test.tsx after:T003
- [X] T014 [US3] {FR-002,FR-009} [COMPLETES FR-002] Add module selector and all-device action in frontend/src/App.tsx after:T003
- [X] T015 [US3] {FR-003,FR-008,FR-009} Display bulk result summary in frontend/src/App.tsx after:T014
- [X] T016 [US3] {FR-008,FR-009} [COMPLETES FR-008] Refresh inventory after manual checks in frontend/src/App.tsx after:T015
- [X] T017 [US3] {FR-009} [COMPLETES FR-009] Keep controls usable during delayed checks in frontend/src/App.tsx after:T016

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T018 {FR-003} [COMPLETES FR-003] Run manual check regression tests across backend and frontend
- [X] T019 {FR-007} [COMPLETES FR-007] Confirm archived devices are excluded from all-device manual checks

---

## Dependencies

Foundational → US1 P1 UI → US2 P1 bulk API → US3 P2 responsiveness → Polish.

- T002 depends on T001.
- T003 depends on T002.
- T005 depends on T002 and T004.
- T006 depends on T005.
- T007 depends on T006.
- T009 depends on existing E009 CheckService.
- T010 depends on T009.
- T011 depends on T010.
- T012 depends on T011.
- T014 depends on T003.
- T015 depends on T014.
- T016 depends on T015.
- T017 depends on T016.
- T018 and T019 depend on T017.
- Tasks marked `[P]` can run in parallel within their phase.
