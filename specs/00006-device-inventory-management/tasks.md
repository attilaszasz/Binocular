# Tasks: Device Inventory Management

## Project Mode

Brownfield — extend the existing FastAPI backend, SQLite migration layer, and React SPA shell.

## Epic / Capability Map

- [US1] → Maintain persistent device records.
- [US2] → Scan grouped inventory with honest status.
- [US3] → Confirm physical firmware updates.

## Brownfield Notes

- Existing flows touched: `backend/src/binocular/routes/`, `repositories/`, `services/`, `frontend/src/App.tsx`, `frontend/src/api/`.
- Compatibility concerns: append migration `002_inventory.sql`; never renumber `001_initial.sql`.
- Regression focus: `/healthz`, SPA static serving, theme/navigation, strict type checks.

## Phase 1: Foundational

- [X] T001 {FR-004,FR-006} Add inventory tables in backend/src/binocular/db/migrations/002_inventory.sql
- [X] T002 {FR-005,FR-011,FR-012} Implement inventory repository in backend/src/binocular/repositories/inventory.py → exports: InventoryRepository
- [X] T003 {FR-007,FR-008,FR-009} Implement inventory service in backend/src/binocular/services/inventory.py ← T002:InventoryRepository → exports: InventoryService
- [X] T004 {FR-010} Implement inventory API routes in backend/src/binocular/routes/inventory.py ← T003:InventoryService
- [X] T005 Register inventory router in backend/src/binocular/routes/__init__.py after:T004

## Phase 2: US1 — Maintain Device Records (Priority: P1) 🎯 MVP

- [X] T006 [US1] {FR-001,FR-002,FR-010} Add create/update backend tests in backend/tests/test_inventory_routes.py after:T005
- [X] T007 [US1] {FR-001} Add typed inventory API client in frontend/src/api/inventory.ts
- [X] T008 [US1] {FR-001,FR-002} Wire create/edit forms in frontend/src/App.tsx after:T007 [COMPLETES FR-001]
- [X] T009 [US1] {FR-011} Add frontend create/edit tests in frontend/src/App.test.tsx after:T008

## Phase 3: US2 — Scan Grouped Inventory (Priority: P1) 🎯 MVP

- [X] T010 [US2] {FR-003,FR-005} Add grouped/archive backend tests in backend/tests/test_inventory_routes.py after:T005
- [X] T011 [US2] {FR-005,FR-007,FR-012} Render API-backed grouped inventory in frontend/src/App.tsx after:T007 [COMPLETES FR-005]
- [X] T012 [US2] {FR-003} Add archive and status UI tests in frontend/src/App.test.tsx after:T011 [COMPLETES FR-003]

## Phase 4: US3 — Confirm Physical Updates (Priority: P2)

- [X] T013 [US3] {FR-008} Add confirm-update backend tests in backend/tests/test_inventory_routes.py after:T005
- [X] T014 [US3] {FR-009} Wire confirm-update API action in frontend/src/api/inventory.ts after:T013
- [X] T015 [US3] {FR-008,FR-009} Implement confirm-update UI flow in frontend/src/App.tsx after:T014 [COMPLETES FR-009]

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T016 Add inventory repository unit tests in backend/tests/test_inventory_repository.py after:T003 [COMPLETES FR-004]
- [X] T017 Run backend Ruff, mypy, pytest coverage, pip-audit, and frontend lint/typecheck/test

## Dependencies

- Foundational tasks before US1-US3 delivery tasks.
- US1 and US2 can proceed after T005; US3 depends on backend route/service from T005 and frontend API from T007.
- Polish validation depends on all delivery phases.
- Tasks with `after:T###` depend on the referenced task being complete.