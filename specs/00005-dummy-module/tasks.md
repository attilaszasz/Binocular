# Tasks: Module Interface Contract & Mock Execution

**Input**: Design documents from `specs/00005-dummy-module/`
**Prerequisites**: [plan.md](plan.md) (required), [spec.md](spec.md) (required), [data-model.md](data-model.md), [contracts/openapi.yaml](contracts/openapi.yaml)

**Tests**: Required per project instruction Principle V (Test-First Development). Tests MUST be written and FAIL before implementation within each story phase.

**Organization**: Tasks grouped by user story to enable independent implementation and testing. US2 precedes US1 because module loading is a prerequisite for execution.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Paths are relative to repository root (`backend/`)

---

## Phase 1: Setup

**Purpose**: Migration, package scaffolding, and test fixtures

- [ ] T001 Create migration file backend/src/db/migrations/003_add_module_timeout.sql with ALTER TABLE app_config ADD COLUMN module_execution_timeout_seconds
- [ ] T002 [P] Create engine package init backend/src/engine/__init__.py
- [ ] T003 [P] Create test fixture module files in backend/tests/fixtures/modules/ (valid_module.py, missing_function.py, wrong_signature.py, syntax_error.py, missing_constants.py, raises_system_exit.py)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared models, protocols, schemas, and exception classes that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Create CheckResult Pydantic model in backend/src/models/check_result.py (latest_version required, optional: download_url, release_date, release_notes, raw_versions, metadata)
- [ ] T005 [P] Define ModuleProtocol (typing.Protocol) in backend/src/engine/protocol.py per AD-2
- [ ] T006 [P] Add module_execution_timeout_seconds field (default=30, ge=5, le=300) to AppConfig and AppConfigUpdate in backend/src/models/app_config.py
- [ ] T007 [P] Export CheckResult from backend/src/models/__init__.py
- [ ] T008 [P] Add ModuleExecutionError and NoModuleAssignedError exception classes to backend/src/services/exceptions.py
- [ ] T009 [P] Add MODULE_ERROR to ErrorCode literal type in backend/src/api/schemas/errors.py
- [ ] T010 [P] Create module API response schemas (ModuleResponse, ModuleReloadResponse, CheckExecutionResponse) in backend/src/api/schemas/modules.py per contracts/openapi.yaml
- [ ] T011 Create HTTP client factory in backend/src/engine/http_client.py (User-Agent header, connection/read timeouts per AD-4)

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 2 — Validate and Register a Module at Load Time (Priority: P1) 🎯 MVP

**Goal**: System discovers `.py` files in the modules directory, imports them safely via importlib, validates against the interface contract, and registers them in the extension_module table as active or inactive.

**Independent Test**: Place valid and broken module files in a temp directory → trigger scan → verify registry has correct active/inactive status and error messages.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T012 [P] [US2] Write Module Loader tests in backend/tests/test_engine/test_loader.py — cover: valid module loaded & registered, missing function → inactive, wrong signature → inactive, syntax error → inactive, missing constants → inactive, file hash change detection, _prefix and __init__.py exclusion, empty .py file handling
- [ ] T013 [P] [US2] Write HTTP client factory tests in backend/tests/test_engine/test_http_client.py — cover: User-Agent string format, connection timeout, read timeout

### Implementation for User Story 2

- [ ] T014 [US2] Implement Module Loader in backend/src/engine/loader.py — discover files (exclude _ prefix, __init__.py), import via importlib.util.spec_from_file_location, validate (hasattr check_firmware + inspect.signature for 3 params + MODULE_VERSION + SUPPORTED_DEVICE_TYPE constants), compute SHA-256 file hash, register/upsert via ExtensionModuleRepo, maintain private module dict (never pollute sys.modules per AD-9), structured logging per plan logging events table

**Checkpoint**: Module loading pipeline works — valid modules register as active, broken modules as inactive with descriptive errors

---

## Phase 4: User Story 1 — Execute a Module and Receive Version Data (Priority: P1) 🎯 MVP

**Goal**: Invoke a loaded module's check_firmware() function via asyncio.to_thread(), validate the return dict with CheckResult, and record the outcome in check_history.

**Independent Test**: Load a mock module → execute check_firmware via the engine → verify CheckResult validation → confirm check_history entry created.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T015 [P] [US1] Write Execution Engine tests in backend/tests/test_engine/test_executor.py — cover: successful execution → CheckResult validated → history recorded, module returns None → validation error recorded, exception during execution → error outcome recorded
- [ ] T016 [P] [US1] Write ModuleService tests in backend/tests/test_services/test_module_service.py — cover: list modules, reload modules, execute check (happy path), execute check with no module assigned, execute check with missing device model
- [ ] T017 [P] [US1] Write API endpoint tests in backend/tests/test_api/test_modules.py — cover: GET /api/v1/modules returns list, POST /api/v1/modules/reload returns updated counts, POST /api/v1/devices/{id}/check returns CheckExecutionResponse, 404 for unknown device, 404 for no module assigned, 422 for missing model field

### Implementation for User Story 1

- [ ] T018 [US1] Implement Execution Engine in backend/src/engine/executor.py — asyncio.to_thread() wrapping (AD-1), asyncio.wait_for() timeout (AD-7), error boundary catching SystemExit + Exception (AD-8), CheckResult.model_validate() on return dict (AD-5), record outcome via CheckHistoryRepo, structured logging per plan events table
- [ ] T019 [US1] Implement ModuleService in backend/src/services/module_service.py — orchestrate loader + executor + repos, resolve device → device_type → module chain, list/reload/execute_check methods
- [ ] T020 [US1] Add get_module_service factory to backend/src/api/dependencies.py
- [ ] T021 [US1] Implement module API routes in backend/src/api/routes/modules.py — GET /api/v1/modules, POST /api/v1/modules/reload, POST /api/v1/devices/{id}/check per contracts/openapi.yaml
- [ ] T022 [US1] Wire module router, module directory seeding (AD-6: copy _modules → modules if empty), and initial module scan into lifespan in backend/src/main.py

**Checkpoint**: Core execution pipeline works end-to-end — load module, invoke, validate result, record history, expose via API

---

## Phase 5: User Story 3 — Run the Built-In Mock Module (Priority: P2)

**Goal**: Verify the pre-existing mock_module.py (backend/_modules/mock_module.py) is seeded, discovered, loaded, and produces correct deterministic results through the full pipeline.

**Independent Test**: Fresh start → mock_module.py seeded → scan discovers it → execute check for MOCK-001 → get version "2.0.0" back.

**Note**: mock_module.py and seed data already exist from prior work. This phase focuses on integration verification.

### Tests for User Story 3 ⚠️

- [ ] T023 [US3] Write mock module integration test — cover: mock module seeded on empty directory, discovered and registered as active with correct metadata, execution returns deterministic data per model (MOCK-001→2.0.0, MOCK-002→1.5.0, MOCK-003→3.1.0-beta), MOCK-NOTFOUND returns None → validation error path, check_history entries recorded correctly

### Verification for User Story 3

- [ ] T024 [US3] Validate mock_module.py contract compliance — verify MODULE_VERSION, SUPPORTED_DEVICE_TYPE, check_firmware(url, model, http_client) signature, docstrings, and deterministic response map match spec requirements (FR-011, FR-012)

**Checkpoint**: Mock module works end-to-end on fresh install — seeded, loaded, executable, results validated

---

## Phase 6: User Story 4 — Protect the System from Broken Modules (Priority: P2)

**Goal**: Verify the error boundary correctly isolates failures — exceptions, timeouts, SystemExit, invalid data — and that one broken module cannot affect others.

**Independent Test**: Run deliberately broken fixture modules through the executor → verify each failure mode produces correct error records without affecting other modules.

### Tests for User Story 4 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation (extend test_executor.py)**

- [ ] T025 [P] [US4] Write fault isolation tests in backend/tests/test_engine/test_executor.py — cover: SystemExit caught (not propagated), configurable timeout via app_config (asyncio.TimeoutError → error record), GeneratorExit and KeyboardInterrupt propagate normally, error description format matches spec guidance (prefix patterns: "Validation failed:", "Module error:", "Timeout:")
- [ ] T026 [P] [US4] Write batch isolation test — execute multiple modules in sequence where one raises an exception, verify remaining modules execute normally and produce correct history entries

### Implementation for User Story 4

- [ ] T027 [US4] Verify and harden error boundary in backend/src/engine/executor.py — ensure SystemExit catch order is correct (before Exception), timeout error description includes configured seconds, batch execution continues after individual failure

**Checkpoint**: Fault isolation verified — no broken module can crash the app or prevent other modules from running

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validation, type safety, and integration verification

- [ ] T028 [P] Run mypy --strict on all new engine code (backend/src/engine/, backend/src/services/module_service.py, backend/src/api/schemas/modules.py, backend/src/api/routes/modules.py)
- [ ] T029 [P] Run quickstart.md validation scenarios end-to-end
- [ ] T030 Verify structured logging events match plan's logging events table (module.scan.start, module.load.success/failed/skipped, module.scan.complete, module.exec.start/success/error/timeout, module.seed.copy)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US2 (Phase 3)**: Depends on Foundational — Module Loader builds on CheckResult, Protocol, exceptions
- **US1 (Phase 4)**: Depends on Foundational + US2 — Execution Engine needs loaded modules from Loader
- **US3 (Phase 5)**: Depends on US1 + US2 — Mock module verification needs the full pipeline
- **US4 (Phase 6)**: Depends on US1 — Fault isolation tests target the Execution Engine
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **US2 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **US1 (P1)**: Can start after US2 (Phase 3) — Executor needs Loader for module resolution; API routes integrate both
- **US3 (P2)**: Can start after US1 (Phase 4) — Integration test needs full pipeline (loader + executor + API)
- **US4 (P2)**: Can start after US1 (Phase 4) — Fault isolation tests target the executor; can run in parallel with US3

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before services
- Services before endpoints/routes
- Core engine before API integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks T002–T003 marked [P] can run in parallel
- All Foundational tasks T005–T010 marked [P] can run in parallel (after T004)
- US2 tests T012–T013 can run in parallel
- US1 tests T015–T017 can run in parallel
- US3 and US4 can run in parallel (both depend on US1, independent of each other)
- All Polish tasks T028–T029 marked [P] can run in parallel

---

## Coverage Map

| Spec Requirement | Tasks |
|---|---|
| FR-001 (function signature) | T005, T014 |
| FR-002 (return validation) | T004, T018 |
| FR-003 (safe import) | T014 |
| FR-004 (load-time validation) | T012, T014 |
| FR-005 (register active) | T014 |
| FR-006 (register inactive) | T012, T014 |
| FR-007 (error boundary + SystemExit) | T018, T025, T027 |
| FR-008 (timeout) | T001, T006, T018, T025 |
| FR-009 (record outcomes) | T018 |
| FR-010 (file hash detection) | T012, T014 |
| FR-011 (mock module) | T023, T024 |
| FR-012 (reference implementation) | T024 |
| FR-013 (create directory) | T022 |
| FR-013a (seeding) | T022, T023 |
| FR-014 (manifest constants) | T005, T014 |
| FR-015 (scraping rules) | T011, T013 | User-Agent + timeouts now; robots.txt, rate limiting, backoff deferred per AD-10 |
| FR-016 (host httpx.Client) | T011, T013 | Enforcement point established; middleware enriched later |
| FR-017 (response caching) | — | SHOULD-level; deferred per AD-10 (mock module has no network needs) |
| FR-018 (prefer structured sources) | — | Guidance-only SHOULD; documented in spec, no task needed |
| FR-019 (list modules endpoint) | T021, T017 |
| FR-020 (reload endpoint) | T021, T017 |
| FR-021 (execute check endpoint) | T021, T017 |
| AD-11 (MODULE_ERROR code) | T009 |

| User Story | Tasks | Count |
|---|---|---|
| Setup | T001–T003 | 3 |
| Foundational | T004–T011 | 8 |
| US1 (P1) | T015–T022 | 8 |
| US2 (P1) | T012–T014 | 3 |
| US3 (P2) | T023–T024 | 2 |
| US4 (P2) | T025–T027 | 3 |
| Polish | T028–T030 | 3 |
| **Total** | | **30** |
