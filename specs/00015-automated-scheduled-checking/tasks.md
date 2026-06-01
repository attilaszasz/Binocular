# Tasks: Automated Scheduled Checking

**Input**: Design documents from `specs/00015-automated-scheduled-checking/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/`
**Tests**: Included because SC-001 through SC-007 require lifecycle, API, scheduler, and UI verification.

## Project Mode

`Brownfield`

## Epic / Capability Map

- `[US1]` → Configure device-type schedules
- `[US2]` → Run unattended checks reliably
- `[US3]` → Resume after restart
- `[US4]` → View schedule health

## Brownfield Notes

- Existing flows touched: inventory device types, E009/E010 `CheckService`, route aggregator, app lifespan, inventory UI.
- Compatibility or migration concerns: add migration `004_schedules.sql`; add `apscheduler` backend dependency.
- Regression focus: inventory CRUD, manual checks, module execution, migration runner, app startup/shutdown.

## Phase 1: Setup (Repository / Workspace Delta)

- [X] T001 Add APScheduler backend dependency in backend/pyproject.toml

---

## Phase 2: Foundational (Cross-Work-Item Blockers)

- [X] T002 [P] {FR-003} Add schedule migration tests in backend/tests/test_schedules_repository.py
- [X] T003 {FR-003} Add device type schedule migration in backend/src/binocular/db/migrations/004_schedules.sql
- [X] T004 {FR-003,FR-009} Add schedule repository in backend/src/binocular/repositories/schedules.py → exports: ScheduleRepository
- [X] T005 {FR-005,FR-006,FR-007,FR-008,FR-010} Add scheduler service tests in backend/tests/test_scheduler_service.py after:T004
- [X] T006 {FR-005,FR-006,FR-007,FR-008,FR-010} Add scheduler service in backend/src/binocular/services/scheduler.py after:T005 ← T004:ScheduleRepository → exports: SchedulerService

---

## Phase 3: Work Item 1 - Configure Device-Type Schedules (Priority: P1) 🎯 MVP

- [X] T007 [US1] {FR-001,FR-002,FR-009} Add schedule route tests in backend/tests/test_schedules_routes.py after:T004
- [X] T008 [US1] {FR-001,FR-002,FR-009} Add schedule route models in backend/src/binocular/routes/schedules.py after:T007
- [X] T009 [US1] {FR-001,FR-002,FR-009} Register schedule routes in backend/src/binocular/routes/__init__.py after:T008
- [X] T010 [US1] {FR-001,FR-002} Add frontend schedule API tests in frontend/src/api/schedules.test.ts
- [X] T011 [US1] {FR-001,FR-002,FR-009} Add frontend schedule API in frontend/src/api/schedules.ts after:T010 → exports: listSchedules(), updateSchedule()
- [X] T012 [US1] {FR-001,FR-002} [COMPLETES FR-001] Add schedule controls in frontend/src/App.tsx after:T011
- [X] T013 [US1] {FR-002} [COMPLETES FR-002] Add interval validation UI tests in frontend/src/App.test.tsx after:T012

---

## Phase 4: Work Item 2 - Run Unattended Checks Reliably (Priority: P1) 🎯 MVP

- [X] T014 [US2] {FR-005,FR-006} Add type-device listing helper in backend/src/binocular/repositories/inventory.py
- [X] T015 [US2] {FR-005,FR-006,FR-007} Wire scheduled run execution in backend/src/binocular/services/scheduler.py after:T014
- [X] T016 [US2] {FR-007,FR-010} Record overlap skips in backend/src/binocular/services/scheduler.py after:T015
- [X] T017 [US2] {FR-005,FR-006,FR-007} [COMPLETES FR-005] Verify scheduled success/failure tests in backend/tests/test_scheduler_service.py after:T016
- [X] T018 [US2] {FR-006,FR-007} [COMPLETES FR-006] [COMPLETES FR-007] Verify CheckService reuse in backend/tests/test_scheduler_service.py after:T017

---

## Phase 5: Work Item 3 - Resume After Restart (Priority: P1) 🎯 MVP

- [X] T019 [US3] {FR-004,FR-008,FR-011} Add lifespan scheduler tests in backend/tests/test_app.py after:T006
- [X] T020 [US3] {FR-004,FR-008,FR-011} Wire scheduler startup/shutdown in backend/src/binocular/main.py after:T019 ← T006:SchedulerService
- [X] T021 [US3] {FR-004,FR-008} [COMPLETES FR-004] Rebuild jobs from SQLite in backend/src/binocular/services/scheduler.py after:T020
- [X] T022 [US3] {FR-008,FR-011} [COMPLETES FR-008] [COMPLETES FR-011] Verify no-backlog restart behavior in backend/tests/test_scheduler_service.py after:T021

---

## Phase 6: Work Item 4 - View Schedule Health (Priority: P2)

- [X] T023 [US4] {FR-009,FR-010} Export schedule API types in frontend/src/api/index.ts after:T011
- [X] T024 [US4] {FR-009,FR-010} Add schedule health UI tests in frontend/src/App.test.tsx after:T023
- [X] T025 [US4] {FR-009,FR-010} Render schedule health fields in frontend/src/App.tsx after:T024
- [X] T026 [US4] {FR-009,FR-010} [COMPLETES FR-009] [COMPLETES FR-010] Display failure and skip diagnostics in frontend/src/App.tsx after:T025

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T027 Run scheduled-check backend test slice in backend
- [X] T028 Run scheduled-check frontend test slice in frontend

---

## Dependencies

Setup → Foundational → US1 P1 configuration → US2 P1 execution → US3 P1 restart → US4 P2 health → Polish.

- T003 depends on T002.
- T004 depends on T003.
- T006 depends on T005.
- T008 depends on T007.
- T009 depends on T008.
- T011 depends on T010.
- T012 depends on T011.
- T013 depends on T012.
- T015 depends on T014.
- T016 depends on T015.
- T017 depends on T016.
- T018 depends on T017.
- T020 depends on T019.
- T021 depends on T020.
- T022 depends on T021.
- T024 depends on T023.
- T025 depends on T024.
- T026 depends on T025.
- T027 and T028 depend on T026.
- Tasks marked `[P]` can run in parallel within their phase.