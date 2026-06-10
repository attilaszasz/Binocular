# Tasks: Module Engine & Contract

**Project Mode**: brownfield
**Epic**: E007 | **Capability**: CAP-002 (Extension Module Engine & Authoring Contract)

## Phase 1: Setup

- [X] T001 Create extensions package scaffolding at `backend/src/binocular/extensions/__init__.py`
- [X] T002 Add `MODULE_TIMEOUT` setting to `backend/src/binocular/config.py` → exports: Settings.module_timeout

## Phase 2: OBJ1 — Authoring Contract Definition 🎯 MVP

- [X] T003 [P] [OBJ1] {TR-001} Define CheckResult Pydantic model in `backend/src/binocular/extensions/contract.py` → exports: CheckResult(latest_version, release_date, download_url, release_notes_url)
- [X] T004 [P] [OBJ1] {TR-001} [COMPLETES TR-001] Define contract constants and check_firmware protocol in `backend/src/binocular/extensions/contract.py` → exports: MODULE_VERSION_ATTR, SUPPORTED_DEVICE_TYPE_ATTR, CHECK_FIRMWARE_FUNC
- [X] T005 [OBJ1] Write unit tests for contract types in `backend/tests/extensions/test_contract.py` after:T003

## Phase 3: OBJ5 — Module Database Schema & Repository 🎯 MVP

- [X] T006 [OBJ5] {TR-009} Create migration `backend/src/binocular/db/migrations/0003_modules_engine.sql` — ALTER TABLE modules ADD COLUMN version, author, file_path, is_official, status
- [X] T007 [OBJ5] {TR-010} [COMPLETES TR-010] Implement ModuleRepository extending RepositoryBase in `backend/src/binocular/extensions/repository.py` ← T002:Settings → exports: ModuleRepository(create, get, list_all, update, delete)
- [X] T008 [OBJ5] Write unit tests for ModuleRepository in `backend/tests/extensions/test_repository.py` after:T007

## Phase 4: OBJ2 — Module Loader 🎯 MVP

- [X] T009 [OBJ2] {TR-002} Create test fixtures in `backend/tests/extensions/fixtures/` — valid_module.py, missing_function.py, missing_constant.py, syntax_error.py
- [X] T010 [OBJ2] {TR-002} [COMPLETES TR-002] Implement ModuleLoader with importlib discovery and loading in `backend/src/binocular/extensions/loader.py` ← T004:CHECK_FIRMWARE_FUNC → exports: ModuleLoader(discover, load, load_all)
- [X] T011 [OBJ2] Write unit tests for ModuleLoader in `backend/tests/extensions/test_loader.py` after:T010

## Phase 5: OBJ3 — Module Runner with Error Boundary 🎯 MVP

- [X] T012 [OBJ3] Create runner test fixtures in `backend/tests/extensions/fixtures/` — slow_module.py, raising_module.py, systemexit_module.py
- [X] T013 [OBJ3] {TR-003,TR-004,TR-005} [COMPLETES TR-003] Implement ModuleRunner in `backend/src/binocular/extensions/runner.py` ← T004:CHECK_FIRMWARE_FUNC ← T002:Settings.module_timeout → exports: ModuleRunner(run)
- [X] T014 [OBJ3] Write unit tests for ModuleRunner error boundary and timeout in `backend/tests/extensions/test_runner.py` after:T013

## Phase 6: OBJ4 — Two-Phase Validation Pipeline 🎯 MVP

- [X] T015 [OBJ4] {TR-006} Implement Phase 1 AST validator using ast.NodeVisitor in `backend/src/binocular/extensions/validator.py` ← T004:MODULE_VERSION_ATTR,SUPPORTED_DEVICE_TYPE_ATTR → exports: ASTValidator.validate(source_path)
- [X] T016 [OBJ4] {TR-007} Implement Phase 2 runtime proof validator in `backend/src/binocular/extensions/validator.py` after:T015 → exports: RuntimeValidator.validate(module, test_inputs)
- [X] T017 [OBJ4] {TR-008} [COMPLETES TR-008] Define ValidationResult with per-phase detail in `backend/src/binocular/extensions/validator.py` → exports: ValidationResult, ValidationCheck
- [X] T018 [OBJ4] Write unit tests for validator phases in `backend/tests/extensions/test_validator.py` after:T017

## Phase 7: Polish

- [X] T019 {TR-011} Update `backend/src/binocular/extensions/__init__.py` with public API exports after:T017
- [X] T020 {TR-011} [COMPLETES TR-011] Run `mypy --strict` on extensions package — fix all type errors after:T019
- [X] T021 Run full test suite and verify ≥80% coverage for extensions package after:T020
