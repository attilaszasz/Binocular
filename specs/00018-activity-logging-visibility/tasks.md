# Tasks: Activity Logging & Visibility

**Input**: Design documents from `specs/00018-activity-logging-visibility/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/`
**Tests**: Required because SC-001 through SC-003 must be verified in full.

## Project Mode

`Brownfield`

## Epic / Capability Map

- `[US1]` → View Check & Alert History
- `[US2]` → Diagnose Outbound Scrape & Alert Failures
- `[US3]` → Automatic Log Bounding & Rolling Retention

## Brownfield Notes

- Existing flows touched: Database migrations runner, router mappings aggregation, `CheckService` core scraping loop, `NotifierService` alerting flow, and SPA settings views layouts.
- Regression focus: Database connection WAL locking under concurrent writes, API routers registrations, checks schedules, and frontend SPA bundle builds.

## Phase 1: Setup (Repository / Workspace Delta)

- [x] T001 Verify standard `aiosqlite` and `structlog` dependencies are fully registered in `backend/pyproject.toml`

---

## Phase 2: Foundational (Cross-Work-Item Blockers)

- [x] T002 Add database migration `006_activity_log.sql` creating the `activity_log` table and `prune_activity_log` SQLite AFTER INSERT rolling pruning trigger in `backend/src/binocular/db/migrations/`
- [x] T003 {FR-003,FR-004} Add `ActivityLogRepository` tests in `backend/tests/test_activity_repository.py`
- [x] T004 {FR-003,FR-004,FR-009} Add `ActivityLogRepository` in `backend/src/binocular/repositories/activity.py` after:T002,T003 ← T002 ← T003 → exports: ActivityLogRepository

---

## Phase 3: Work Item 1 - Activity Logging & API Router (Priority: P1) 🎯 MVP

- [x] T005 [US1,US2] {FR-005,FR-006} Add activity REST endpoints tests in `backend/tests/test_activity_routes.py` after:T004
- [x] T006 [US1,US2] {FR-005,FR-006} Add activity API router in `backend/src/binocular/routes/activity.py` after:T005 → exports: router
- [x] T007 [US1,US2] Register activity router in `backend/src/binocular/routes/__init__.py` after:T006
- [x] T008 [US1,US2] {FR-001} Integrate `ActivityLogRepository` start/success/failed check logs hook inside `backend/src/binocular/services/checks.py` after:T004
- [x] T009 [US1,US2] {FR-002} Integrate `ActivityLogRepository` success/failed notification dispatches logs hook inside `backend/src/binocular/services/notifications.py` after:T004

---

## Phase 4: Work Item 2 - React Web SPA Activity Log View (Priority: P1) 🎯 MVP

- [x] T010 [US1,US2] Add frontend activity API client in `frontend/src/api/activity.ts` → exports: getActivity()
- [x] T011 [US1,US2] Register activity API client in `frontend/src/api/index.ts` after:T010
- [x] T012 [US1,US2] {FR-007,FR-008} Implement Activity Log route view, responsive table layout, status badges, filters, and expandable exception tracebacks cards in `frontend/src/App.tsx` after:T011

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T013 Verify 80%+ test statements coverage over new and modified backend files in `backend` after:T008,T009
- [x] T014 Verify frontend compilation and type-safety compiler checks pass cleanly in `frontend` after:T012

---

## Dependencies

Setup → Foundational → US1/US2 APIs and hooks → US1/US2 SPA components → Polish.

- T004 depends on T002, T003.
- T005 depends on T004.
- T006 depends on T005.
- T007 depends on T006.
- T008 depends on T004.
- T009 depends on T004.
- T011 depends on T010.
- T012 depends on T011.
- T013 depends on T008, T009.
- T014 depends on T012.
