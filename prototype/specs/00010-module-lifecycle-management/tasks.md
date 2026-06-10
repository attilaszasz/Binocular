# Tasks: Module Lifecycle Management

**Input**: Design documents from `specs/00010-module-lifecycle-management/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`
**Tests**: Include focused backend and frontend regression tasks from `plan.md` testing strategy.

## Project Mode

`Brownfield`

## Epic / Capability Map

- `US1` -> upload valid module and list installed modules
- `US2` -> reject invalid module with validation feedback
- `US3` -> update installed module safely
- `US4` -> delete installed module

## Brownfield Notes

- Existing flows touched: `backend/src/binocular/routes/`, `backend/src/binocular/repositories/modules.py`, `frontend/src/App.tsx`.
- Compatibility concerns: preserve E006 validator contract and existing inventory routes.
- Regression focus: static SPA navigation, inventory page, module engine tests.

## Phase 1: Foundational (Cross-Work-Item Blockers)

- [X] T001 {FR-005,FR-007} Extend ModuleRepository lifecycle helpers in backend/src/binocular/repositories/modules.py
- [X] T002 Create ModuleLifecycleService scaffolding in backend/src/binocular/services/modules.py

---

## Phase 2: Work Item 1 - Upload Valid Module (Priority: P1) 🎯 MVP

- [X] T003 [US1] {FR-002} Implement staged validation and install in backend/src/binocular/services/modules.py after:T002
- [X] T004 [US1] {FR-001,FR-005} Add module response schemas and GET/POST routes in backend/src/binocular/routes/modules.py after:T003
- [X] T005 [US1] {FR-001} Register modules router in backend/src/binocular/routes/__init__.py after:T004
- [X] T006 [P] [US1] {FR-005} Add module API helpers in frontend/src/api/modules.ts
- [X] T007 [US1] {FR-001,FR-005,FR-009} Replace static Modules page in frontend/src/App.tsx after:T006
- [X] T008 [US1] {FR-001,FR-002} [COMPLETES FR-001] Add valid upload API tests in backend/tests/test_modules_api.py after:T004
- [X] T009 [US1] {FR-005} [COMPLETES FR-005] Add module list/upload UI tests in frontend/src/App.test.tsx after:T007

---

## Phase 3: Work Item 2 - Reject Invalid Module (Priority: P1) 🎯 MVP

- [X] T010 [US2] {FR-003,FR-010} Enforce extension, empty, and size guards in backend/src/binocular/routes/modules.py after:T004
- [X] T011 [US2] {FR-004,FR-008} Return validation error summaries in backend/src/binocular/routes/modules.py after:T010
- [X] T012 [US2] {FR-004,FR-009} Render validation feedback and trust warning in frontend/src/App.tsx after:T011
- [X] T013 [US2] {FR-003,FR-004,FR-010} [COMPLETES FR-004] Add invalid upload tests in backend/tests/test_modules_api.py after:T011

---

## Phase 4: Work Item 3 - Update Existing Module (Priority: P1) 🎯 MVP

- [X] T014 [US3] {FR-006} Implement same-ID safe replacement in backend/src/binocular/services/modules.py after:T003
- [X] T015 [US3] {FR-006} Preserve prior module on failed replacement in backend/src/binocular/services/modules.py after:T014
- [X] T016 [US3] {FR-006} Update replacement status flow in frontend/src/App.tsx after:T015
- [X] T017 [US3] {FR-006} [COMPLETES FR-006] Add replacement preservation tests in backend/tests/test_modules_service.py after:T015

---

## Phase 5: Work Item 4 - Delete Module (Priority: P2)

- [X] T018 [US4] {FR-007} Implement module deletion service path in backend/src/binocular/services/modules.py after:T001
- [X] T019 [US4] {FR-007} Add DELETE module route in backend/src/binocular/routes/modules.py after:T018
- [X] T020 [US4] {FR-007,FR-008} Add UI delete action and not-found feedback in frontend/src/App.tsx after:T019
- [X] T021 [US4] {FR-007} [COMPLETES FR-007] Add delete and 404 API tests in backend/tests/test_modules_api.py after:T019

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T022 [P] {FR-009} [COMPLETES FR-009] Add trust-boundary UI regression test in frontend/src/App.test.tsx after:T012
- [X] T023 [P] {FR-008} [COMPLETES FR-008] Add frontend API error tests in frontend/src/api/modules.test.ts after:T006
- [X] T024 Run backend and frontend formatting/type-check fixes for module lifecycle changes

---

## Dependencies

Foundational -> US1 -> US2 -> US3 -> US4 -> Polish

- Tasks marked `[P]` can run in parallel within their phase when dependencies are satisfied.
- Tasks with `after:T###` depend on the referenced task.
- No task with `after:T###` should be batched with its dependency.
