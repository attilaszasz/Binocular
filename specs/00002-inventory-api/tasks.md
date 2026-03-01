# Tasks: Inventory API (CRUD)

**Input**: Design documents from `specs/00002-inventory-api/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, quickstart.md, contracts/openapi.yaml

**Tests**: Required — project instructions mandate Test-First Development (Principle V). Integration tests use `httpx.AsyncClient` via FastAPI TestClient with isolated temp-file SQLite. Within each user story phase, tests are written first and expected to fail until implementation is complete.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `backend/src/`, `backend/tests/`
- API layer: `backend/src/api/` (schemas, routes, dependencies, exception handlers, middleware)
- Service layer: `backend/src/services/` (business logic, domain exceptions)
- Data layer: `backend/src/models/`, `backend/src/repositories/` (existing from Feature 00001)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add dependencies, create package structure, and configure developer tooling.

- [ ] T001 Add httpx and debugpy dev dependencies to pyproject.toml
- [ ] T002 [P] Create .vscode/launch.json with "Binocular: Debug API" configuration per quickstart.md
- [ ] T003 [P] Create backend/src/api/ package with __init__.py
- [ ] T004 [P] Create backend/src/api/schemas/ package with __init__.py
- [ ] T005 [P] Create backend/src/api/routes/ package with __init__.py
- [ ] T006 [P] Create backend/src/services/ package with __init__.py
- [ ] T007 [P] Create backend/tests/test_api/ package with __init__.py
- [ ] T008 [P] Create backend/tests/test_services/ package with __init__.py

**Checkpoint**: Package structure ready — foundational modules can now be created.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented. Includes domain exceptions, error handling, middleware, app factory, dependency injection, and test fixtures.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T009 Create domain exception hierarchy (BinocularError, NotFoundError, DuplicateNameError, ValidationError, CascadeBlockedError, NoLatestVersionError) in backend/src/services/exceptions.py (AD-2)
- [ ] T010 [P] Create ErrorResponse Pydantic schema with detail, error_code, and optional field in backend/src/api/schemas/errors.py (FR-016)
- [ ] T011 Create FastAPI exception handlers mapping domain exceptions to HTTP error envelope in backend/src/api/exception_handlers.py (AD-2, FR-016)
- [ ] T012 [P] Create correlation ID and structured request-logging middleware in backend/src/api/middleware.py (FR-020, FR-021)
- [ ] T013 Create FastAPI app factory with lifespan, middleware registration, exception handlers, and router mounts in backend/src/main.py (AD-6)
- [ ] T014 Create dependency injection factories (get_connection, repos, services) in backend/src/api/dependencies.py
- [ ] T015 [P] Create health check endpoint (GET /api/v1/health) in backend/src/api/routes/health.py
- [ ] T016 Create httpx.AsyncClient and test-app fixtures in backend/tests/test_api/conftest.py
- [ ] T017 Write integration tests for health endpoint and error envelope consistency in backend/tests/test_api/test_errors.py
- [ ] T049 Create Settings(BaseSettings) configuration model with BINOCULAR_DB_PATH, host, port, and log_level defaults in backend/src/config.py (Principle IV)

**Checkpoint**: Foundation ready — app starts, health responds, error envelopes are consistent. User story implementation can now begin.

---

## Phase 3: User Story 1 — Manage Device Types (Priority: P1) 🎯 MVP

**Goal**: Full CRUD for device types with duplicate-name detection and device count enrichment (FR-001, FR-009, FR-011, AD-5, AD-7, AD-8).

**Independent Test**: Create a device type, retrieve it, update a field, list all device types (with device counts), and delete it.

### Tests for User Story 1

> **Write these tests FIRST — they MUST fail until implementation is complete.**

- [ ] T018 [P] [US1] Write integration tests for device type CRUD (create, get, list, update, simple delete, duplicate name) in backend/tests/test_api/test_device_types.py
- [ ] T019 [P] [US1] Write unit tests for DeviceTypeService CRUD and error translation in backend/tests/test_services/test_device_type_service.py

### Implementation for User Story 1

- [ ] T020 [P] [US1] Add name field to DeviceTypeUpdate model in backend/src/models/device_type.py (AD-8)
- [ ] T021 [P] [US1] Add get_device_count() and get_all_with_counts() methods to DeviceTypeRepo in backend/src/repositories/device_type_repo.py (AD-5)
- [ ] T022 [P] [US1] Create DeviceTypeCreateRequest, DeviceTypeUpdateRequest, and DeviceTypeResponse schemas in backend/src/api/schemas/device_type.py (AD-7, FR-008, FR-008a–c)
- [ ] T023 [US1] Create DeviceTypeService with create, get, list, update, delete and duplicate-name error translation in backend/src/services/device_type_service.py (AD-2)
- [ ] T024 [US1] Implement device type routes (GET list, POST create, GET by id, PATCH update, DELETE simple) in backend/src/api/routes/device_types.py

**Checkpoint**: Device type CRUD fully functional. Tests from T018/T019 should now pass.

---

## Phase 4: User Story 2 — Manage Devices Within a Device Type (Priority: P1) 🎯 MVP

**Goal**: Full CRUD for devices with nested creation under device types, response enrichment (derived status + device_type_name), and duplicate-name-within-type detection (FR-002, FR-006, FR-009, AD-1, AD-4, AD-7).

**Independent Test**: Create a device type, add devices under it, retrieve individual devices (with status and parent type info), update fields, list all devices, and delete a device.

### Tests for User Story 2

> **Write these tests FIRST — they MUST fail until implementation is complete.**

- [ ] T025 [P] [US2] Write integration tests for device CRUD (nested create, get, list, update, delete, duplicate name within type, cross-type duplicate allowed) in backend/tests/test_api/test_devices.py
- [ ] T026 [P] [US2] Write unit tests for DeviceService CRUD and response enrichment in backend/tests/test_services/test_device_service.py

### Implementation for User Story 2

- [ ] T027 [P] [US2] Create DeviceCreateRequest, DeviceUpdateRequest, and DeviceResponse schemas with derived status and device_type_name in backend/src/api/schemas/device.py (AD-4, AD-7, FR-008, FR-008a–c)
- [ ] T028 [US2] Create DeviceService with create, get, list, update, delete, status derivation, and device_type_name enrichment in backend/src/services/device_service.py (AD-2, AD-4)
- [ ] T029 [US2] Implement device routes (POST nested create under type, GET list, GET by id, PATCH update, DELETE) in backend/src/api/routes/devices.py (AD-1)

**Checkpoint**: Device CRUD fully functional with enriched responses. Tests from T025/T026 should now pass.

---

## Phase 5: User Story 3 — Confirm a Firmware Update (Priority: P1) 🎯 MVP

**Goal**: Single-device confirm action that sets current_version = latest_seen_version, with idempotency and never-checked rejection (FR-003, FR-004, FR-005, AD-3).

**Independent Test**: Set up a device with version mismatch, confirm it, verify versions match. Confirm again (idempotent). Try to confirm a never-checked device (rejected).

### Tests for User Story 3

> **Write these tests FIRST — they MUST fail until implementation is complete.**

- [ ] T030 [US3] Write integration tests for single-device confirm (version sync, idempotency, never-checked rejection) in backend/tests/test_api/test_confirm.py

### Implementation for User Story 3

- [ ] T031 [P] [US3] Create confirm response and BulkConfirmResponse schemas in backend/src/api/schemas/actions.py
- [ ] T032 [US3] Add confirm_update method to DeviceService with idempotency and NoLatestVersionError in backend/src/services/device_service.py (FR-003–FR-005)
- [ ] T033 [US3] Implement POST /api/v1/devices/{id}/confirm route in backend/src/api/routes/actions.py (AD-3)

**Checkpoint**: Single-device confirm fully functional. Tests from T030 should now pass. MVP complete — all P1 stories delivered.

---

## Phase 6: User Story 4 — Safe Deletion of Device Types with Children (Priority: P2)

**Goal**: Cascade-safe deletion — reject device type deletion when children exist unless confirm_cascade=true is provided (FR-010, FR-011).

**Independent Test**: Create a type with devices, attempt delete without confirmation (rejected with count), retry with confirmation (type + children removed), delete empty type without confirmation (succeeds).

### Tests for User Story 4

> **Write these tests FIRST — they MUST fail until implementation is complete.**

- [ ] T034 [US4] Write integration tests for cascade deletion (reject without flag, accept with flag, empty type needs no flag) in backend/tests/test_api/test_device_types.py

### Implementation for User Story 4

- [ ] T035 [US4] Add cascade-safe delete logic to DeviceTypeService (check device count, raise CascadeBlockedError or delete with children) in backend/src/services/device_type_service.py (FR-010)
- [ ] T036 [US4] Update DELETE /api/v1/device-types/{id} route to accept confirm_cascade query parameter in backend/src/api/routes/device_types.py

**Checkpoint**: Cascade-safe deletion working. Tests from T034 should now pass.

---

## Phase 7: User Story 5 — Browse and Filter the Device Inventory (Priority: P2)

**Goal**: Filter device list by device_type_id and status, sort by name or last_checked_at with deterministic tie-breaking (FR-012, FR-013, FR-013b).

**Independent Test**: Create multiple types with devices in various states, filter by type (only matching returned), filter by status (only matching returned), sort by name and last_checked_at, verify deterministic ordering.

### Tests for User Story 5

> **Write these tests FIRST — they MUST fail until implementation is complete.**

- [ ] T037 [US5] Write integration tests for filtering (by type, by status) and sorting (name, -name, last_checked_at, -last_checked_at, invalid values rejected) in backend/tests/test_api/test_devices.py

### Implementation for User Story 5

- [ ] T038 [US5] Add get_all_filtered() with device_type_id, status, sort, and id tie-breaker to DeviceRepo in backend/src/repositories/device_repo.py (FR-012, FR-013, FR-013b)
- [ ] T039 [US5] Add filter/sort orchestration and status-based in-memory filtering to DeviceService list method in backend/src/services/device_service.py
- [ ] T040 [US5] Update GET /api/v1/devices route to accept device_type_id, status, and sort query parameters with validation in backend/src/api/routes/devices.py

**Checkpoint**: Filtering and sorting working. Tests from T037 should now pass.

---

## Phase 8: User Story 6 — Bulk Confirm All Pending Updates (Priority: P3)

**Goal**: Bulk confirm action that confirms all eligible devices with best-effort semantics and summary reporting (FR-014, FR-014a, FR-015).

**Independent Test**: Set up devices in various states, bulk confirm, verify summary counts. Run again (idempotent — 0 confirmations). Test with optional device_type_id filter.

### Tests for User Story 6

> **Write these tests FIRST — they MUST fail until implementation is complete.**

- [ ] T041 [US6] Write integration tests for bulk confirm (mixed states, idempotency, type filter, error reporting) in backend/tests/test_api/test_confirm.py

### Implementation for User Story 6

- [ ] T042 [US6] Add bulk_confirm() method with best-effort per-device processing to DeviceRepo in backend/src/repositories/device_repo.py (FR-014)
- [ ] T043 [US6] Add bulk_confirm_all method with summary generation to DeviceService in backend/src/services/device_service.py (FR-014, FR-014a, FR-015)
- [ ] T044 [US6] Implement POST /api/v1/devices/confirm-all route with optional device_type_id filter in backend/src/api/routes/actions.py

**Checkpoint**: Bulk confirm working. Tests from T041 should now pass. All user stories complete.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Observability, documentation, type safety, and validation of the complete feature.

- [ ] T045 [P] Add audit event logging for state-changing operations to backend/src/services/device_type_service.py and backend/src/services/device_service.py (FR-022)
- [ ] T046 [P] Configure OpenAPI metadata, tag descriptions, and response examples for interactive docs grouping in backend/src/main.py (FR-017)
- [ ] T047 Run mypy --strict on backend/src/api/ and backend/src/services/ and fix type errors
- [ ] T048 Validate specs/00002-inventory-api/quickstart.md integration scenarios against running API on localhost:8000
- [ ] T050 Run latency benchmarks for CRUD and list endpoints against test fixtures and validate SC-008 thresholds in backend/tests/test_api/

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on Foundational completion; may start in parallel with US1 (no shared files) but logically benefits from US1 being complete (device types must exist for device creation)
- **User Story 3 (Phase 5)**: Depends on US2 (devices must exist to confirm); adds to services and routes created in US2
- **User Story 4 (Phase 6)**: Depends on US1 (extends device type delete route); modifies service and route files from US1
- **User Story 5 (Phase 7)**: Depends on US2 (extends device list route); modifies service, repo, and route files from US2
- **User Story 6 (Phase 8)**: Depends on US3 (extends actions route file); can run in parallel with US4/US5 (different files)
- **Polish (Phase 9)**: Depends on all user stories being complete

### Recommended Execution Order (Single Developer)

```
Phase 1 → Phase 2 → Phase 3 (US1) → Phase 4 (US2) → Phase 5 (US3) → Phase 6 (US4) → Phase 7 (US5) → Phase 8 (US6) → Phase 9
```

### User Story Dependencies

- **US1 (P1)**: After Foundational — no dependencies on other stories
- **US2 (P1)**: After Foundational — logically after US1 (needs device types)
- **US3 (P1)**: After US2 — adds confirm method to DeviceService and actions route
- **US4 (P2)**: After US1 — modifies DeviceTypeService and device type delete route
- **US5 (P2)**: After US2 — modifies DeviceService, DeviceRepo, and device list route
- **US6 (P3)**: After US3 — adds bulk confirm to DeviceService and actions route

### Within Each User Story

1. Tests MUST be written and FAIL before implementation (Principle V)
2. Models/repo changes before services
3. Schemas before services
4. Services before routes
5. Story complete → checkpoint → next story

### Parallel Opportunities

- **Phase 1**: T002–T008 can all run in parallel (different files)
- **Phase 2**: T009+T010 in parallel (different files), then T011–T015 sequentially, T016–T017 after app factory
- **US1**: T018+T019 (tests) in parallel, then T020+T021+T022 (model/repo/schema) in parallel, then T023→T024 sequentially
- **US2**: T025+T026 (tests) in parallel, then T027 (schema) before T028→T029
- **US4 + US6**: Can run in parallel with each other (different files)

---

## Coverage Map

### User Story → Task Mapping

| Story | Priority | Tasks | Count |
|---|---|---|---|
| — (Setup) | — | T001–T008 | 8 |
| — (Foundational) | — | T009–T017, T049 | 10 |
| US1: Manage Device Types | P1 | T018–T024 | 7 |
| US2: Manage Devices | P1 | T025–T029 | 5 |
| US3: Confirm Update | P1 | T030–T033 | 4 |
| US4: Safe Cascade Delete | P2 | T034–T036 | 3 |
| US5: Filter & Sort | P2 | T037–T040 | 4 |
| US6: Bulk Confirm | P3 | T041–T044 | 4 |
| — (Polish) | — | T045–T048, T050 | 5 |
| **Total** | | | **50** |

### FR → Task Traceability

| Requirement | Tasks |
|---|---|
| FR-001 (Device type CRUD) | T018–T024 |
| FR-002 (Device CRUD) | T025–T029 |
| FR-003–005 (Confirm) | T030–T033 |
| FR-006 (Return full resource) | T022, T027 (response schemas) |
| FR-007 (Timestamps RFC 3339) | T022, T027 (response schemas) |
| FR-008, 008a–c (Validation) | T022, T027 (request schemas) |
| FR-009 (Uniqueness errors) | T023, T028 (services) |
| FR-010 (Cascade safety) | T034–T036 |
| FR-011 (Device count) | T021, T022 |
| FR-012–013b (Filter/sort) | T037–T040 |
| FR-014, 014a, 015 (Bulk confirm) | T041–T044 |
| FR-016 (Error envelope) | T009–T011 |
| FR-017 (OpenAPI docs) | T046 |
| FR-018 (No-op update) | T023, T028 |
| FR-019 (Not found) | T009, T011 |
| FR-020 (Correlation ID) | T012 |
| FR-021 (Request logging) | T012 |
| FR-022 (Audit events) | T045 |
| Principle IV (BaseSettings) | T049 |
| SC-008 (Latency thresholds) | T050 |

### AD → Task Traceability

| Decision | Tasks |
|---|---|
| AD-1 (Hybrid routing) | T029 |
| AD-2 (Service + exceptions) | T009, T011, T023, T028 |
| AD-3 (Confirm as POST) | T033, T044 |
| AD-4 (Device enrichment) | T027, T028 |
| AD-5 (DeviceType count) | T021, T022 |
| AD-6 (App factory + F5) | T002, T013 |
| AD-7 (Schema layering) | T022, T027, T031 |
| AD-8 (Name update) | T020 |
