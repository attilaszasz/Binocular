# Tasks: Application Skeleton & Container

**Input**: [spec.md](spec.md), [plan.md](plan.md), [data-model.md](data-model.md), [contracts/](contracts/)
**Project Mode**: greenfield

## Dependencies

| Phase | Depends On | Parallel Notes |
|-------|------------|----------------|
| Phase 1 Setup | — | Root and package scaffolding. |
| Phase 2 🎯 MVP OBJ1 | Phase 1 | App factory and health route. |
| Phase 3 🎯 MVP OBJ2 | Phase 1 | Settings can proceed after package scaffold. |
| Phase 4 🎯 MVP OBJ3 | Phase 1 | Logging can proceed after package scaffold. |
| Phase 5 🎯 MVP OBJ4 | Phases 2-4 | Docker needs runnable app command. |
| Phase 6 Cross-Cutting | Phases 2-5 | Tests/docs verify full skeleton. |

## Phase 1: Setup

- [X] T001 Create backend project metadata in backend/pyproject.toml → exports: project config
- [X] T002 Create backend package directories and __init__.py files under backend/src/binocular/ after:T001
- [X] T003 Create .dockerignore for Python, test, cache, and local artifact exclusions

## Phase 2: 🎯 MVP Objective 1 - Runnable FastAPI Application Skeleton

- [X] T004 [OBJ1] {TR-001} Implement app factory in backend/src/binocular/app.py after:T002 → exports: create_app(settings)
- [X] T005 [OBJ1] {TR-002} Create route aggregator in backend/src/binocular/routes/__init__.py after:T004 → exports: api_router
- [X] T006 [OBJ1] {TR-003} Implement health route in backend/src/binocular/routes/health.py after:T005 → exports: router
- [X] T007 [OBJ1] {TR-001,TR-003} Add ASGI entrypoint in backend/src/binocular/main.py after:T006 [COMPLETES TR-001]

## Phase 3: 🎯 MVP Objective 2 - Zero-Config Runtime Settings

- [X] T008 [OBJ2] {TR-004} Implement typed settings in backend/src/binocular/config.py after:T002 → exports: Settings,get_settings()
- [X] T009 [OBJ2] {TR-004} Add settings tests in backend/tests/test_config.py after:T008 [COMPLETES TR-004]

## Phase 4: 🎯 MVP Objective 3 - Structured Logging Baseline

- [X] T010 [OBJ3] {TR-005} Implement structlog setup in backend/src/binocular/logging.py after:T002 → exports: configure_logging()
- [X] T011 [OBJ3] {TR-005} Wire logging into app construction in backend/src/binocular/app.py after:T010
- [X] T012 [OBJ3] {TR-005} Add logging tests in backend/tests/test_logging.py after:T011 [COMPLETES TR-005]

## Phase 5: 🎯 MVP Objective 4 - Non-Root Container Image

- [X] T013 [OBJ4] {TR-006,TR-007,TR-008} Create multi-stage non-root Dockerfile with /healthz HEALTHCHECK after:T007
- [X] T014 [OBJ4] {TR-006,TR-007,TR-008} Validate Docker command and healthcheck documentation in README.md after:T013 [COMPLETES TR-006]

## Phase 6: Cross-Cutting Verification and Trust Boundary

- [X] T015 {TR-002,TR-009} Document unsandboxed extension seam in backend/src/binocular/extensions/README.md after:T002 [COMPLETES TR-009]
- [X] T016 {TR-001,TR-003} Add app and health integration tests in backend/tests/test_app.py after:T007
- [X] T017 {TR-003} Add dedicated health contract tests in backend/tests/test_health.py after:T006 [COMPLETES TR-003]
- [X] T018 Run backend lint, type, unit, integration, and coverage checks for backend/ after:T017