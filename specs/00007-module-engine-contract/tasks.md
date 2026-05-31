# Tasks: Module Engine & Contract

## Project Mode

Brownfield — extend the existing FastAPI backend, SQLite migration layer, ScrapeClient, and extensions package.

## Epic / Capability Map

- [OBJ1] → Stable contract and importlib loader.
- [OBJ2] → Invocation boundary and timeout handling.
- [OBJ3] → Two-phase validation pipeline.
- [OBJ4] → Module metadata persistence.

## Brownfield Notes

- Existing flows touched: `backend/src/binocular/extensions/`, `repositories/`, `db/migrations/`, `config.py`.
- Compatibility concerns: append migration `003_modules.sql`; never renumber existing migrations.
- Regression focus: ScrapeClient tests, migration startup, strict mypy, no sandboxing claims.

## Phase 1: Foundational

- [X] T001 {TR-001} Define module contract models in backend/src/binocular/extensions/contract.py → exports: ModuleMetadata,ModuleCheckInput
- [X] T002 {TR-008} Add module metadata migration in backend/src/binocular/db/migrations/003_modules.sql
- [X] T003 {TR-008} Add module repository tests in backend/tests/test_modules_repository.py after:T002
- [X] T004 {TR-008} Implement module repository in backend/src/binocular/repositories/modules.py after:T003 → exports: ModuleRepository
- [X] T005 {TR-004,TR-006} Add modules_dir and timeout settings in backend/src/binocular/config.py

## Phase 2: OBJ1 — Stable Contract And Loader (Priority: P1) 🎯 MVP

- [X] T006 [OBJ1] {TR-001,TR-002} Add loader tests in backend/tests/test_module_loader.py after:T001
- [X] T007 [OBJ1] {TR-002} Implement importlib loader in backend/src/binocular/extensions/loader.py after:T006 ← T001:ModuleMetadata → exports: ModuleLoader
- [X] T008 [OBJ1] {TR-001,TR-009} Update authoring contract docs in backend/src/binocular/extensions/README.md after:T007 [COMPLETES TR-001]

## Phase 3: OBJ2 — Invocation Boundary (Priority: P1) 🎯 MVP

- [X] T009 [OBJ2] {TR-003,TR-004,TR-005} Add runner tests in backend/tests/test_module_runner.py after:T001
- [X] T010 [OBJ2] {TR-003,TR-004,TR-005} Implement runner in backend/src/binocular/extensions/runner.py after:T009 ← T001:ModuleCheckInput → exports: ModuleRunner
- [X] T011 [OBJ2] {TR-003,TR-004,TR-005} Add runner cancellation/injection tests in backend/tests/test_module_runner.py after:T010 [COMPLETES TR-003] [COMPLETES TR-004] [COMPLETES TR-005]

## Phase 4: OBJ3 — Two-Phase Validation (Priority: P1) 🎯 MVP

- [X] T012 [OBJ3] {TR-006,TR-007} Add validator tests in backend/tests/test_module_validator.py after:T007
- [X] T013 [OBJ3] {TR-006,TR-007} Implement static validator in backend/src/binocular/extensions/validator.py after:T012 ← T007:ModuleLoader
- [X] T014 [OBJ3] {TR-006,TR-007} Implement runtime proof validation in backend/src/binocular/extensions/validator.py after:T013 ← T010:ModuleRunner
- [X] T015 [OBJ3] {TR-006,TR-007} Add validator integration cases in backend/tests/test_module_validator.py after:T014 [COMPLETES TR-006] [COMPLETES TR-007]

## Phase 5: OBJ4 — Module Metadata Persistence (Priority: P2)

- [X] T016 [OBJ4] {TR-008} Wire validation status serialization in backend/src/binocular/repositories/modules.py after:T014
- [X] T017 [OBJ4] {TR-008} Add migration/repository integration tests in backend/tests/test_modules_repository.py after:T016 [COMPLETES TR-008]

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T018 {TR-009} Add unsandboxed documentation regression test in backend/tests/test_module_contract_docs.py after:T008 [COMPLETES TR-009]
- [X] T019 Run backend Ruff, mypy, pytest coverage, and pip-audit for module engine changes

## Dependencies

- Foundational tasks precede all objective phases.
- OBJ1 loader work precedes OBJ3 validation.
- OBJ2 runner work precedes OBJ3 runtime proof validation.
- OBJ4 persistence depends on validation result shape from OBJ3.
- Polish validation depends on all delivery phases.
