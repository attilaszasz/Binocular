# Tasks: Application Skeleton & Container

**Project Mode**: greenfield

## Epic / Capability Map

| Objective | Priority | Requirements |
|-----------|----------|-------------|
| OBJ1 — FastAPI Application Factory | P1 | TR-001, TR-002 |
| OBJ2 — Pydantic Settings Configuration | P1 | TR-003, TR-004 |
| OBJ3 — Structured Logging | P1 | TR-005, TR-006 |
| OBJ4 — Non-Root Docker Container | P1 | TR-007, TR-008, TR-009, TR-010 |
| Cross-cutting | — | TR-011, TR-012 |

## Phase 1: Setup

- [X] T001 Initialize `backend/pyproject.toml` with project metadata, dependencies, and tool config (ruff, mypy) {TR-012}
- [X] T002 Create `backend/src/binocular/__init__.py` and `backend/src/binocular/py.typed` marker
- [X] T003 Create `.env.example` with documented env vars

## Phase 2: OBJ2 — Pydantic Settings Configuration 🎯 MVP

- [X] T004 [OBJ2] {TR-003,TR-004} Implement Settings class in `backend/src/binocular/config.py` → exports: Settings(log_format,host,port,data_dir,modules_dir)
- [X] T005 [OBJ2] Write tests for Settings in `backend/tests/test_config.py` ← T004:Settings

## Phase 3: OBJ3 — Structured Logging 🎯 MVP

- [X] T006 [OBJ3] {TR-005,TR-006} Implement structlog configuration in `backend/src/binocular/logging.py` ← T004:Settings → exports: setup_logging()
- [X] T007 [OBJ3] Write tests for logging in `backend/tests/test_logging.py` ← T006:setup_logging

## Phase 4: OBJ1 — FastAPI Application Factory 🎯 MVP

- [X] T008 [OBJ1] Create router aggregator in `backend/src/binocular/routes/__init__.py` → exports: router
- [X] T009 [OBJ1] {TR-002} Implement /healthz endpoint in `backend/src/binocular/routes/health.py` ← T008:router → exports: health_router
- [X] T010 [OBJ1] {TR-001} Implement app factory in `backend/src/binocular/app.py` ← T004:Settings ← T006:setup_logging ← T008:router → exports: create_app()
- [X] T011 [OBJ1] Create test fixtures in `backend/tests/conftest.py` ← T010:create_app
- [X] T012 [OBJ1] Write tests for /healthz in `backend/tests/test_health.py` ← T011:conftest

## Phase 5: OBJ4 — Non-Root Docker Container 🎯 MVP

- [X] T013 [OBJ4] {TR-008,TR-009} Create `entrypoint.sh` with PUID/PGID support via su-exec
- [X] T014 [OBJ4] {TR-007} Create `Dockerfile` using python:3.13-slim with su-exec build and non-root exec ← T013:entrypoint.sh
- [X] T015 [OBJ4] {TR-010} Create `compose.yaml` with service definition and volume mounts ← T014:Dockerfile

## Phase 6: Polish & Cross-Cutting

- [X] T016 {TR-011} Verify `mypy --strict` passes on all backend source
- [X] T017 Verify `ruff check` and `ruff format --check` pass on all backend source
- [X] T018 Run full test suite with `pytest --cov` and verify ≥80% coverage
