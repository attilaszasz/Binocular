# Tasks: Per-Module Frequency on Modules Page

**Input**: Design documents from `specs/00027-per-module-frequency-on-modules/`
**Prerequisites**: `spec.md` (product, clarified), `plan.md`, `research.md`, `contracts/openapi.yaml`, `checklists/` (CHL001 UX, CHL002 API Quality, CHL003 Data Integrity — all evaluated)

**Tests**: Not requested — omit test tasks.

## Project Mode

`Brownfield` — extends existing Binocular codebase. No repo-level scaffolding needed.

## Epic / Capability Map

- `[US1]` → View check frequency on each module card (display only)
- `[US2]` → Edit check frequency inline via preset picker + toggle

## Brownfield Notes

- Existing flows touched: `ModuleRepository.list_modules()`, GET `/modules` route, PUT `/schedules/device-types/{id}` route, `ModuleLifecycleService.delete_module()`, `ModulesPage` component, `InstalledModule` type
- Compatibility: Backward-compatible unpaginated mode when `pageSize` omitted per AD-003/HINT-004; existing `updateSchedule()` client reused unchanged
- Regression focus: Module upload, delete, validation, and inventory workflows must keep working; schedule list endpoint unchanged

## Phase 1: Foundational (Backend API Extension + Data Integrity)

- [X] T001 [P] Add schedule fields (schedule_enabled, schedule_interval_minutes) to ModuleRecord dataclass and update _record_from_row in backend/src/binocular/repositories/modules.py
- [X] T002 {FR-006} Add LEFT JOIN device_type_schedules and pagination to list_modules in backend/src/binocular/repositories/modules.py after:T001
- [X] T003 [P] {FR-006} Add ModuleScheduleData model, extend ModuleResponse with schedule field and ModuleListResponse with pagination fields in backend/src/binocular/routes/modules.py
- [X] T004 {FR-006} [COMPLETES FR-006] Update GET /modules handler for page/pageSize params, pagination, and schedule field in backend/src/binocular/routes/modules.py after:T002 after:T003
- [X] T005 [P] Add DELETE FROM device_type_schedules cascade to delete_module() in backend/src/binocular/services/modules.py

## Phase 2: User Story 1 - View Check Frequency on Modules Page (P1) 🎯 MVP

- [X] T006 [P] [US1] {FR-001} Add formatFrequencyLabel utility (60→"1h", 90→"90m", null→"24h") in frontend/src/App.tsx
- [X] T007 [P] [US1] {FR-005,FR-006} Extend InstalledModule type with optional schedule field and update listModules for paginated response in frontend/src/api/modules.ts
- [X] T008 [US1] {FR-001,FR-005} [COMPLETES FR-005] Render frequency label + enabled indicator on each module card in frontend/src/App.tsx after:T004 after:T006 after:T007

## Phase 3: User Story 2 - Edit Check Frequency Inline (P1) 🎯 MVP

- [X] T009 [US2] {FR-002,FR-003} [COMPLETES FR-001] Create FrequencyEditor with presets, custom input, toggle, keyboard nav in frontend/src/components/FrequencyEditor.tsx
- [X] T010 [P] [US2] {FR-004} Wire SchedulerService.reschedule_type() into PUT /schedules/device-types route handler in backend/src/binocular/routes/schedules.py after:T004
- [X] T011 [US2] {FR-002,FR-003} Integrate FrequencyEditor into module cards with useMutation, save/cancel/blur, error toast, and external-change notification in frontend/src/App.tsx after:T009

## Phase 4: Bug Fixes (QC Iteration 1)

- [X] T012 [P] [BUG:MEDIUM] Fix backend test regressions — update ModuleResponse/ModuleListResponse test assertions for new schedule+pagination fields, fix FK constraint in test DB setup in backend/tests/
- [X] T013 [P] [BUG:MEDIUM] Fix frontend test regressions — mount QueryClientProvider in test renders that use TanStack Query hooks in frontend/src/__tests__/
- [X] T014 [BUG:MEDIUM] Add schedule_error field to ModuleResponse backend schema and InstalledModule frontend type per contracts/openapi.yaml and plan.md fail-soft handling in backend/src/binocular/routes/modules.py and frontend/src/api/modules.ts
- [X] T015 [BUG:LOW] Review bandit findings — examine B104 (bind-all acceptable for trusted LAN) and B608 (verify parameterized SQL in JOIN query) in backend/src/binocular/
