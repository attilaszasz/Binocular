# Tasks: Module Lifecycle Management

**Project Mode**: brownfield
**Epic**: E009 | **Capability**: CAP-003 (Module Lifecycle Management)

## Phase 1: Backend Scaffolding & API Models

- [X] T001 [US1] {FR-001} Update `ModuleResponse` or create new Pydantic schema models in `backend/src/binocular/devices/models.py`
- [X] T002 [US2] {FR-002,FR-003} Implement base modules router configuration at `backend/src/binocular/routes/modules.py`
- [X] T003 [US1] {FR-001} Implement list registered modules route in `backend/src/binocular/routes/modules.py` after:T002
- [X] T004 [US2] {FR-002,FR-004} Implement upload and validation route in `backend/src/binocular/routes/modules.py` after:T002
- [X] T005 [US3] {FR-005,FR-006} Implement delete module route with device reference checking in `backend/src/binocular/routes/modules.py` after:T002
- [X] T006 [US1] {FR-007} Implement update module metadata route in `backend/src/binocular/routes/modules.py` after:T002
- [X] T007 [US1] {FR-001} Register the new modules router in `backend/src/binocular/routes/__init__.py` after:T002

## Phase 2: Backend Unit Tests

- [X] T008 [US2] {FR-002,FR-003} [COMPLETES FR-002] Write unit/integration tests for uploading valid and invalid modules in `backend/tests/routes/test_modules.py` after:T004
- [X] T009 [US3] {FR-005,FR-006} Write unit/integration tests for deleting unused and used modules in `backend/tests/routes/test_modules.py` after:T005
- [X] T010 [US1] {FR-001,FR-007} [COMPLETES FR-001] Write unit/integration tests for listing and updating modules in `backend/tests/routes/test_modules.py` after:T003,T006

## Phase 3: Frontend Layout & Components

- [X] T011 [US1] {FR-008} Implement `ModuleCard` and `ModuleStatusBadge` components in `frontend/src/components/modules/`
- [X] T012 [US2,US4] {FR-009,FR-010} Implement `ModuleUploadForm` with drag-and-drop, validation error displays, and Copy for AI button in `frontend/src/components/modules/` after:T011
- [X] T013 [US1,US2,US3] {FR-008,FR-009,FR-010} Rewrite `frontend/src/pages/modules.tsx` to query modules, render list/grid, mount upload forms, and show trust boundaries warnings after:T012

## Phase 4: Frontend Unit Tests & Quality Gates

- [X] T014 [US1,US2,US3] Write frontend unit tests for `ModulesPage`, `ModuleCard`, and `ModuleUploadForm` in `frontend/src/pages/modules.test.tsx` after:T013
- [X] T015 Run `mypy --strict` on backend code after:T010
- [X] T016 Run `tsc --noEmit` on frontend code after:T013
- [X] T017 Run backend tests and verify ≥80% coverage after:T010
- [X] T018 Run Vitest frontend tests and verify success after:T014
