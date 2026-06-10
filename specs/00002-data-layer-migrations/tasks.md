# Tasks: Data Layer & Migrations

**Project Mode**: Brownfield
**Epic**: E002 — Data Layer & Migrations
**Spec Type**: technical

## Phase 1: Setup

- [X] T001 {TR-014} Add `aiosqlite` dependency to `backend/pyproject.toml`

## Phase 2: OBJ1 — Async Database Connection Management 🎯 MVP

- [X] T002 [OBJ1] {TR-001,TR-004} Create `backend/src/binocular/db/__init__.py` and `backend/src/binocular/db/connection.py` with async open/close and pragma config → exports: get_connection(settings), close_connection(conn)
- [X] T003 [OBJ1] {TR-002,TR-003} Integrate DB lifecycle into `backend/src/binocular/app.py` lifespan and add `get_db()` dependency → exports: get_db()
- [X] T004 [OBJ1] Write connection tests in `backend/tests/test_connection.py` — pragma validation, auto-create, clean shutdown

## Phase 3: OBJ2 — Numbered Migration Runner 🎯 MVP

- [X] T005 [OBJ2] {TR-005,TR-006,TR-007,TR-008} Create `backend/src/binocular/db/migrations.py` — discover, compare, apply with per-migration transactions → exports: run_migrations(conn, migrations_dir)
- [X] T006 [OBJ2] {TR-013} Add structlog logging for migration events in `backend/src/binocular/db/migrations.py`
- [X] T007 [OBJ2] Create seed migration `backend/src/binocular/db/migrations/0001_init.sql`
- [X] T008 [OBJ2] Write migration runner tests in `backend/tests/test_migrations.py` — apply, skip, failure rollback, idempotency

## Phase 4: OBJ3 — Pre-Migration Backup 🎯 MVP

- [X] T009 [OBJ3] {TR-009,TR-010} Add VACUUM INTO backup logic to `backend/src/binocular/db/migrations.py` — backup before pending, skip when current after:T005
- [X] T010 [OBJ3] Write backup tests in `backend/tests/test_migrations.py` — backup created, skipped, failure blocks migration after:T008

## Phase 5: OBJ4 — Repository Base Class 🎯 MVP

- [X] T011 [P] [OBJ4] {TR-011,TR-012} Create `backend/src/binocular/db/repository.py` with RepositoryBase (execute, fetch_one, fetch_all) → exports: RepositoryBase
- [X] T012 [OBJ4] Write repository tests in `backend/tests/test_repository.py` — insert, fetch_one, fetch_all, named columns, None on missing

## Phase 6: Polish

- [X] T013 {TR-014} Run `mypy --strict` and `ruff check` on all new code, fix any issues
- [X] T014 Run full test suite with `pytest --cov` and verify ≥80% coverage on `db/` package
