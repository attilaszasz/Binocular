# Tasks: Data Layer & Migrations

**Input**: Design documents from `specs/00004-data-layer-migrations/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/repository-base.md`
**Tests**: Required by TR-010 and project instructions.

## Project Mode

`Brownfield`

## Epic / Capability Map

- [OBJ1] -> SQLite connection lifecycle and settings
- [OBJ2] -> Numbered migration runner with atomic version tracking
- [OBJ3] -> Pre-migration backup snapshot hook
- [OBJ4] -> Repository base for parameterized raw SQL

## Brownfield Notes

- Existing flows touched: `backend/src/binocular/app.py`, `backend/src/binocular/config.py`, `backend/pyproject.toml`
- Compatibility concerns: zero-config startup must keep `/healthz` and static serving behavior intact
- Regression focus: existing backend tests must remain green

## Phase 1: Setup (Repository / Workspace Delta)

- [X] T001 Add `aiosqlite` runtime dependency in backend/pyproject.toml

---

## Phase 2: Work Item 1 - SQLite connection lifecycle and settings (Priority: P1) 🎯 MVP

- [X] T002 [P] [OBJ1] {TR-001} Add database settings defaults in backend/src/binocular/config.py
- [X] T003 [OBJ1] {TR-002} Add connection manager in backend/src/binocular/db/connection.py after:T001
- [X] T004 [OBJ1] {TR-002,TR-010} Add connection pragma tests in backend/tests/test_db_connection.py after:T003

---

## Phase 3: Work Item 2 - Numbered migration runner with atomic version tracking (Priority: P1) 🎯 MVP

- [X] T005 [P] [OBJ2] {TR-003} Add initial schema migration in backend/src/binocular/db/migrations/001_initial.sql
- [X] T006 [OBJ2] {TR-003,TR-004,TR-005,TR-008} Implement migration runner in backend/src/binocular/db/migrations.py after:T003,T005
- [X] T007 [OBJ2] {TR-006,TR-008} Wire migration runner into FastAPI lifespan in backend/src/binocular/app.py after:T006
- [X] T008 [OBJ2] {TR-010} Add migration tests in backend/tests/test_db_migrations.py after:T007

---

## Phase 4: Work Item 3 - Pre-migration backup snapshot hook (Priority: P1) 🎯 MVP

- [X] T009 [P] [OBJ3] {TR-007} Implement SQLite backup helper in backend/src/binocular/db/backup.py after:T003
- [X] T010 [OBJ3] {TR-007,TR-008} [COMPLETES TR-008] Integrate backup gate in backend/src/binocular/db/migrations.py after:T009
- [X] T011 [OBJ3] {TR-010} Add backup gate tests in backend/tests/test_db_migrations.py after:T010

---

## Phase 5: Work Item 4 - Repository base for parameterized raw SQL (Priority: P2)

- [X] T012 [P] [OBJ4] {TR-009,TR-011} Add repository base in backend/src/binocular/repositories/base.py after:T003
- [X] T013 [OBJ4] {TR-009,TR-011,TR-010} [COMPLETES TR-010] Add repository tests in backend/tests/test_repositories.py after:T012

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T014 Run backend lint, type-check, tests, and coverage from backend/

---

## Dependencies

Setup -> OBJ1 -> OBJ2 -> OBJ3 -> OBJ4 -> Polish

- T001 must complete before DB modules import `aiosqlite`.
- T003 gates migration, backup, and repository work.
- T006 and T009 must complete before T010.
- T014 validates the full feature after all implementation tasks are complete.
