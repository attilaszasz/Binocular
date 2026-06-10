# Tasks: Update Detection & Comparison

**Input**: Design documents from `specs/00011-update-detection-comparison/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/`
**Tests**: Included because SC-005 requires tests for update-available, up-to-date, and failed outcomes.

## Project Mode

`Brownfield`

## Epic / Capability Map

- `[US1]` → Detect device update status
- `[US2]` → Surface failed detection honestly
- `[US3]` → Provide shared detection contract

## Brownfield Notes

- Existing flows touched: `InventoryRepository`, module repository/loader/runner, route aggregator under `backend/src/binocular/routes/`
- Compatibility or migration concerns: no schema migration planned; keep `last_check_status` values within the existing SQLite CHECK constraint
- Regression focus: inventory list/update/confirm flows, module lifecycle API, module runner fault boundaries

## Phase 1: Foundational (Cross-Work-Item Blockers)

- [X] T001 [P] {FR-002,FR-006} Add comparator unit tests in backend/tests/test_version_compare.py
- [X] T002 {FR-002,FR-006} Implement version comparator in backend/src/binocular/services/version_compare.py → exports: compare_versions()
- [X] T003 [P] {FR-007} Add CheckResult model tests in backend/tests/test_checks_service.py
- [X] T004 {FR-003,FR-007} Define check result models in backend/src/binocular/services/checks.py → exports: CheckResult(status)
- [X] T005 [P] {FR-004,FR-005} Add repository status update tests in backend/tests/test_inventory_repository.py
- [X] T006 {FR-004,FR-005} Implement check status updates in backend/src/binocular/repositories/inventory.py

---

## Phase 2: Work Item 1 - Detect Device Update Status (Priority: P1) 🎯 MVP

- [X] T007 [US1] {FR-001,FR-003} Add service tests for newer, equal, and older versions in backend/tests/test_checks_service.py after:T002
- [X] T008 [US1] {FR-001,FR-003} [COMPLETES FR-003] Implement CheckService success flow in backend/src/binocular/services/checks.py
- [X] T009 [US1] {FR-004} [COMPLETES FR-004] Persist successful check state in backend/src/binocular/services/checks.py after:T006

---

## Phase 3: Work Item 2 - Surface Failed Detection Honestly (Priority: P1) 🎯 MVP

- [X] T010 [US2] {FR-006,FR-008} Add service tests for module, missing-version, and invalid-version failure paths in backend/tests/test_checks_service.py
- [X] T011 [US2] {FR-006,FR-008} [COMPLETES FR-006] Implement failed check classification in backend/src/binocular/services/checks.py after:T008
- [X] T012 [US2] {FR-005} [COMPLETES FR-005] Preserve last_success_at on failure in backend/src/binocular/services/checks.py after:T006

---

## Phase 4: Work Item 3 - Provide Shared Detection Contract (Priority: P2)

- [X] T013 [US3] {FR-007} Add route contract tests in backend/tests/test_checks_routes.py after:T011
- [X] T014 [US3] {FR-007} Implement checks API route in backend/src/binocular/routes/checks.py ← T004:CheckResult
- [X] T015 [US3] {FR-007} Register checks router in backend/src/binocular/routes/__init__.py after:T014
- [X] T016 [US3] {FR-001} [COMPLETES FR-001] Add missing-device route tests in backend/tests/test_checks_routes.py after:T015
- [X] T017 [US3] {FR-008} [COMPLETES FR-008] Add module error route tests in backend/tests/test_checks_routes.py after:T015
- [X] T018 [US3] {FR-007} [COMPLETES FR-007] Verify response schema in backend/tests/test_checks_routes.py after:T015

---

## Dependencies

Foundational → US1/US2 P1 delivery → US3 P2 contract route

- T002 depends on T001.
- T004 depends on T003.
- T006 depends on T005.
- T008 depends on T002 and T004.
- T009 depends on T006 and T008.
- T011 depends on T008 and T010.
- T012 depends on T006 and T011.
- T014 depends on T004 and T011.
- T015 depends on T014.
- T016, T017, and T018 depend on T015.
- Tasks marked `[P]` can run in parallel within their phase.
