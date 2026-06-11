# Tasks: Activity Logging & Visibility

**Project Mode**: brownfield
**Epic**: E015 | **Capability**: CAP-010 (Activity Logging & Visibility)

## Phase 1: Database Setup

- [X] T001 [FR-001] Create SQLite migration `backend/src/binocular/db/migrations/0006_activity_log.sql` creating the `activity_log` table with indices.
- [X] T002 [FR-001] Implement `ActivityRepository` in `backend/src/binocular/db/activity_repository.py` with `log` (insert + prune) and `list_all` (filtered paginated query).
- [X] T003 [FR-001,FR-006] Write unit tests for `ActivityRepository` in `backend/tests/test_activity_repository.py` to verify pruning logic and basic CRUD operations.

## Phase 2: Services Auto-Logging

- [X] T004 [FR-002] Inject `ActivityRepository` and record check success and failure logs in `backend/src/binocular/services/checks.py`.
- [X] T005 [FR-003] Inject `ActivityRepository` and record notification dispatch attempts and failures in `backend/src/binocular/services/notifier.py`.
- [X] T006 [FR-002,FR-003] Write unit tests for services to verify check results and notification dispatches are logged.

## Phase 3: REST API Implementation

- [X] T007 [FR-004,FR-005] Create API router for activity logs in `backend/src/binocular/routes/activity.py` exposing `GET /api/v1/activity`.
- [X] T008 [FR-004,FR-005] Register the activity router in `backend/src/binocular/app.py`.
- [X] T009 [FR-004,FR-005] Write backend integration tests for the REST API in `backend/tests/test_activity_routes.py`.

## Phase 4: Frontend Implementation

- [X] T010 [FR-007,FR-008,FR-009,FR-010] Create Logs component page in `frontend/src/pages/logs.tsx` implementing a table of logs, filters (level, category, device), pagination, and traceback inspection drawer.
- [X] T011 [FR-008] Write frontend tests or verify LogsPage rendering using Vitest.

## Phase 5: QC & Verification

- [X] T012 Run type checking and linters on the modified backend files (`mypy --strict` and `ruff`).
- [X] T013 Run type checking on the modified frontend files (`tsc`).
- [X] T014 Run full backend test suite (`pytest`) to ensure test coverage is at least 80%.
- [X] T015 Verify the overall integration of the logging system and ensure `.qc-passed` is generated.
