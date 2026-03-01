# Tasks: Database Schema & Data Models

**Input**: Design documents from `/specs/00001-db-schema-models/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, quickstart.md

**Tests**: Tests are REQUIRED — Principle V (Test-First Development) in project-instructions.md mandates Red-Green-Refactor. Tests MUST be written and FAIL before implementation in every phase.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Project type**: Web app (backend + frontend). This feature touches only `backend/`.
- Paths use the Source Code layout from plan.md: `backend/src/` for production code, `backend/tests/` for tests.

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Create project structure, install dependencies, configure tooling.

- [ ] T001 Create project directory structure per plan.md layout (backend/src/db/, backend/src/db/migrations/, backend/src/models/, backend/src/repositories/, backend/src/utils/, backend/tests/, backend/tests/test_models/, backend/tests/test_repositories/)
- [ ] T002 Initialize Python project with dependencies: FastAPI, Pydantic v2, aiosqlite, packaging, pytest, pytest-asyncio, structlog, ruff, mypy
- [ ] T003 [P] Configure linting (ruff), formatting (ruff format), and type checking (mypy --strict) in pyproject.toml
- [ ] T004 [P] Configure pytest and pytest-asyncio (asyncio_mode = "auto") in pyproject.toml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented — connection factory, migration runner, shared test fixtures, and version comparison utility.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T005 Create shared test fixtures in backend/tests/conftest.py — temp-file SQLite database with WAL mode, busy_timeout=5000, and foreign_keys=ON pragmas
- [ ] T006 [P] Write tests for SQLite connection pragmas in backend/tests/test_connection.py — verify WAL journal mode, busy_timeout value, and foreign_keys enforcement
- [ ] T007 [P] Write tests for migration runner in backend/tests/test_migration_runner.py — fresh DB applies schema, sequential migration ordering, idempotent re-run safety
- [ ] T008 [P] Write tests for version comparison in backend/tests/test_version_compare.py — semver ordered pairs, string fallback on parse failure, edge cases (dates, letters, build hashes)
- [ ] T009 [P] Implement SQLite connection factory in backend/src/db/connection.py — async context manager, PRAGMA journal_mode=WAL, PRAGMA busy_timeout=5000, PRAGMA foreign_keys=ON (AD-2)
- [ ] T010 [P] Implement version comparison utility in backend/src/utils/version_compare.py — semver parse via packaging.version.Version with string inequality fallback (AD-4)
- [ ] T011 Implement migration runner in backend/src/db/migration_runner.py — reads schema_version table, scans migrations/ for numbered SQL scripts, applies unapplied in order, wraps each in transaction (AD-3)
- [ ] T012 Write initial migration SQL in backend/src/db/migrations/001_initial.sql — all 6 tables (extension_module, device_type, device, check_history, app_config, schema_version) with constraints, seed data, per data-model.md DDL

**Checkpoint**: Foundation ready — connection factory, migration runner, version comparison, and test fixtures operational. User story implementation can now begin.

---

## Phase 3: User Story 1 — Register Device Type and Add Devices (Priority: P1) 🎯 MVP

**Goal**: Users can create device types, add individual devices under them, and persist the complete inventory across restarts.

**Independent Test**: Create a device type, add devices under it, restart, verify all records persist. Validate uniqueness constraints reject duplicates.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T013 [P] [US1] Write tests for DeviceType Pydantic model in backend/tests/test_models/test_device_type.py — field validation, required fields (name, firmware_source_url), defaults (check_frequency_minutes=360), empty-name rejection
- [ ] T014 [P] [US1] Write tests for Device Pydantic model in backend/tests/test_models/test_device.py — field validation, required fields (name, current_version, device_type_id), nullable latest_seen_version, version strings stored verbatim (FR-017)

### Implementation for User Story 1

- [ ] T015 [P] [US1] Implement DeviceType Pydantic model in backend/src/models/device_type.py — id, name (min_length=1, unique), firmware_source_url, extension_module_id (nullable), check_frequency_minutes (gt=0, default=360), timestamps
- [ ] T016 [P] [US1] Implement Device Pydantic model in backend/src/models/device.py — id, device_type_id, name (min_length=1), current_version (min_length=1), latest_seen_version (nullable), last_checked_at (nullable), notes (nullable), timestamps

### Repository Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T017 [P] [US1] Write tests for DeviceType repository in backend/tests/test_repositories/test_device_type_repo.py — create, get_by_id, get_all, update, delete with CASCADE verification
- [ ] T018 [P] [US1] Write tests for Device repository in backend/tests/test_repositories/test_device_repo.py — create, get_by_id, get_by_type, update, delete

### Repository Implementation for User Story 1

- [ ] T019 [US1] Implement DeviceType repository CRUD in backend/src/repositories/device_type_repo.py — create, get_by_id, get_all, update, delete with CASCADE awareness (FR-001, FR-003, FR-014)
- [ ] T020 [US1] Implement Device repository CRUD in backend/src/repositories/device_repo.py — create, get_by_id, get_by_type, update, delete (FR-002, FR-004)
- [ ] T021 [US1] Test unique constraints: duplicate device type names rejected (FR-003), duplicate device names within same type rejected (FR-004), identical device names across different types allowed

**Checkpoint**: User Story 1 complete — device types and devices can be created, read, updated, deleted with full constraint enforcement. MVP inventory is functional.

---

## Phase 4: User Story 2 — Confirm a Firmware Update (Priority: P1) 🎯 MVP

**Goal**: Users can confirm a firmware update with a single action, setting current_version to match latest_seen_version and clearing the update-available indicator.

**Independent Test**: Set up a device with version mismatch, confirm update, verify versions match. Verify never-checked devices reject confirmation. Verify derived status computation.

### Tests for User Story 2 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T022 [US2] Write tests for confirm_update operation in backend/tests/test_repositories/test_device_repo.py — happy path: current_version set to latest_seen_version (FR-005)
- [ ] T023 [US2] Write tests for never-checked rejection (FR-018) and derived status computation — "never checked" when latest_seen_version is NULL, "up to date" when versions match, "update available" when versions differ (FR-006, FR-007)

### Implementation for User Story 2

- [ ] T024 [US2] Implement confirm_update in backend/src/repositories/device_repo.py — sets current_version = latest_seen_version, updates updated_at timestamp (FR-005)
- [ ] T025 [US2] Add never-checked rejection guard to confirm_update in backend/src/repositories/device_repo.py — reject when latest_seen_version is NULL with clear validation error (FR-018)
- [ ] T026 [US2] Implement derived status computation with version_compare integration in backend/src/repositories/device_repo.py — semver comparison with string fallback for update-available detection (FR-006, FR-007, AD-4)

**Checkpoint**: User Story 2 complete — firmware update confirmation works end-to-end. Combined with US1, the MVP inventory now supports full device lifecycle (create → check → confirm update).

---

## Phase 5: User Story 3 — Manage Application Settings (Priority: P2)

**Goal**: Users can configure application behavior (notification channels, check frequency, feature toggles) with all settings persisted and sensible defaults active on fresh install.

**Independent Test**: Verify default settings on fresh DB, modify settings, restart, verify persistence. Clear settings and verify revert to defaults.

### Tests for User Story 3 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T027 [P] [US3] Write tests for AppConfig Pydantic model in backend/tests/test_models/test_app_config.py — typed defaults, boolean mapping for notifications_enabled, port range validation for smtp_port
- [ ] T028 [P] [US3] Write tests for AppConfig repository in backend/tests/test_repositories/test_app_config_repo.py — get_config returns defaults from seed row, update_config persists changes, clearing fields reverts to defaults

### Implementation for User Story 3

- [ ] T029 [US3] Implement AppConfig Pydantic model in backend/src/models/app_config.py — BaseSettings pattern with typed defaults: default_check_frequency_minutes=360, notifications_enabled=False, check_history_retention_days=90, nullable SMTP and Gotify fields (AD-6, FR-008, FR-009)
- [ ] T030 [US3] Implement AppConfig repository in backend/src/repositories/app_config_repo.py — get_config (SELECT from id=1, maps to model with defaults), update_config (UPSERT on id=1, updates only provided fields) (FR-008, FR-009)
- [ ] T031 [US3] Test sensible defaults on fresh database (FR-009), persistence of settings across multiple get/update cycles, clearing individual settings reverts to defaults

**Checkpoint**: User Story 3 complete — application settings are configurable, persistent, and default-safe.

---

## Phase 6: User Story 4 — Track Extension Module Registration (Priority: P2)

**Goal**: The system maintains a registry of installed extension modules with metadata, activation status, and error capture for troubleshooting.

**Independent Test**: Simulate successful module load (verify active state), failed load (verify error capture), file modification (verify hash update), module removal (verify SET NULL on device_type).

### Tests for User Story 4 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T032 [P] [US4] Write tests for ExtensionModule Pydantic model in backend/tests/test_models/test_extension_module.py — field validation, filename uniqueness, boolean mapping for is_active, nullable fields
- [ ] T033 [P] [US4] Write tests for ExtensionModule repository in backend/tests/test_repositories/test_extension_module_repo.py — register, update_hash, set_error, deactivate, get_all, get_by_filename

### Implementation for User Story 4

- [ ] T034 [US4] Implement ExtensionModule Pydantic model in backend/src/models/extension_module.py — id, filename (min_length=1, unique), module_version, supported_device_type, is_active (bool), file_hash, last_error, loaded_at, timestamps (FR-010, FR-011)
- [ ] T035 [US4] Implement ExtensionModule repository in backend/src/repositories/extension_module_repo.py — register, update_hash, set_error, deactivate, get_all, get_by_filename (FR-010, FR-011)
- [ ] T036 [US4] Test module lifecycle states: Loaded (is_active=1, last_error=NULL), Failed (is_active=0, last_error set), Deactivated (is_active=0, last_error=NULL) — verify transitions per state machine in data-model.md
- [ ] T037 [US4] Test ON DELETE SET NULL behavior: delete an extension module referenced by a device_type, verify device_type.extension_module_id is set to NULL and device_type is preserved (US4-AS4, FR-014)

**Checkpoint**: User Story 4 complete — extension module registry tracks load status, errors, and file changes. Module removal safely clears device type associations.

---

## Phase 7: User Story 5 — Review Check History (Priority: P3)

**Goal**: Users can view a log of firmware check events with timestamps, outcomes, and error descriptions. Old entries are automatically cleaned up to bound storage.

**Independent Test**: Simulate check events (success and failure), verify they appear in history. Insert old entries, trigger cleanup, verify retention enforcement. Delete a device and verify cascaded history removal.

### Tests for User Story 5 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T038 [P] [US5] Write tests for CheckHistoryEntry Pydantic model in backend/tests/test_models/test_check_history.py — field validation, outcome constrained to 'success'/'error', nullable version_found and error_description
- [ ] T039 [P] [US5] Write tests for CheckHistory repository in backend/tests/test_repositories/test_check_history_repo.py — create entry, get_by_device, get_all, piggyback deletion after insert

### Implementation for User Story 5

- [ ] T040 [US5] Implement CheckHistoryEntry Pydantic model in backend/src/models/check_history.py — id, device_id, checked_at (datetime), version_found (nullable), outcome (Literal['success', 'error']), error_description (nullable), created_at (FR-012)
- [ ] T041 [US5] Implement CheckHistory repository in backend/src/repositories/check_history_repo.py — create with piggyback retention cleanup (DELETE WHERE checked_at older than retention_days), get_by_device, get_all (AD-5, FR-012, FR-013)
- [ ] T042 [US5] Test retention cleanup: insert entries with timestamps older than 90 days, insert a new entry, verify old entries are deleted after insert (FR-013)
- [ ] T043 [US5] Test CASCADE from device deletion: delete a device_type, verify transitive cascade removes devices and their check_history entries (device_type → device → check_history)

**Checkpoint**: User Story 5 complete — check history is recorded, queryable, and automatically bounded by retention policy.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Package exports, logging, code quality enforcement, and documentation validation.

- [ ] T044 [P] Add __init__.py exports for backend/src/models/__init__.py and backend/src/repositories/__init__.py — re-export all public models and repository classes
- [ ] T045 [P] Add structlog configuration for migration runner (migration applied/skipped), connection lifecycle (opened/closed with pragmas), and repository errors (constraint violations, missing records)
- [ ] T046 Run mypy --strict across all backend/src/ and verify zero errors (Principle IV)
- [ ] T047 Run ruff check and ruff format across all backend/ code and resolve any findings
- [ ] T048 Validate quickstart.md scenarios against implementation — verify all integration scenarios from specs/00001-db-schema-models/quickstart.md execute successfully
- [ ] T049 Add module docstrings to all public modules in backend/src/db/, backend/src/models/, backend/src/repositories/, backend/src/utils/

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phases 3–7)**: All depend on Foundational phase completion
  - User stories can then proceed in priority order (P1 → P2 → P3)
  - US1 and US2 are both P1; US2 depends on US1 (operates on Device entity created in US1)
  - US3 and US4 are both P2; they are independent and can proceed in parallel
  - US5 is P3; depends on US1 (uses Device entity for check history FK)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational (Phase 2) — No dependencies on other stories
- **US2 (P1)**: Depends on US1 — extends Device repository with confirm_update and status derivation
- **US3 (P2)**: Can start after Foundational (Phase 2) — Independent of US1/US2, operates on standalone AppConfig entity
- **US4 (P2)**: Can start after Foundational (Phase 2) — Independent of US1/US2 for model and repo; T037 (SET NULL test) requires DeviceType from US1
- **US5 (P3)**: Depends on US1 — CheckHistory FK references Device entity

### Within Each User Story

- Tests MUST be written and FAIL before implementation (Principle V)
- Model tests → Model implementation → Repository tests → Repository implementation → Constraint/integration tests
- Core implementation before edge-case validation

### Parallel Opportunities

- **Phase 1**: T003 and T004 can run in parallel (different config sections)
- **Phase 2**: T006, T007, T008 (all test files) can run in parallel after T005. T009 and T010 (connection + version_compare) can run in parallel after their tests pass.
- **Phase 3**: T013, T014 (model tests) in parallel. T015, T016 (model impls) in parallel. T017, T018 (repo tests) in parallel.
- **Phase 5**: T027, T028 (model + repo tests) in parallel.
- **Phase 6**: T032, T033 (model + repo tests) in parallel.
- **Phase 7**: T038, T039 (model + repo tests) in parallel.
- **Phase 8**: T044, T045 (exports + logging) in parallel.

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 — device types and devices CRUD
4. Complete Phase 4: User Story 2 — confirm update + status derivation
5. **STOP and VALIDATE**: Test US1 + US2 independently — this is the MVP
6. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add US1 → Test independently → Inventory MVP
3. Add US2 → Test independently → Full MVP (create + check + confirm)
4. Add US3 → Test independently → Settings configurable
5. Add US4 → Test independently → Module registry operational
6. Add US5 → Test independently → Audit trail available
7. Polish → Code quality + documentation validated

### FR Coverage Map

| FR | Tasks |
|---|---|
| FR-001 | T012, T015, T019 |
| FR-002 | T012, T016, T020 |
| FR-003 | T012, T019, T021 |
| FR-004 | T012, T020, T021 |
| FR-005 | T022, T024 |
| FR-006 | T010, T023, T026 |
| FR-007 | T023, T026 |
| FR-008 | T029, T030 |
| FR-009 | T029, T030, T031 |
| FR-010 | T034, T035 |
| FR-011 | T035, T036 |
| FR-012 | T040, T041 |
| FR-013 | T041, T042 |
| FR-014 | T012, T019, T037 |
| FR-015 | T009, T011 |
| FR-016 | T011, T012 |
| FR-017 | T014, T016 |
| FR-018 | T023, T025 |

---

## Notes

- [P] tasks = different files, no dependencies on each other
- [US#] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (Red-Green-Refactor per Principle V)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- All file paths reference the Source Code layout from plan.md
