# Tasks: Module Validation Engine

## Phase 1: Setup

- [X] T001 Create test fixture modules for all 9 error code scenarios plus a valid module in `backend/tests/fixtures/modules/`

---

## Phase 2: Foundational (Pydantic Result Models)

- [X] T002 {FR-008} Define `ValidationErrorCode`, `ValidationError`, `PhaseResult`, and `ValidationResult` Pydantic models in `backend/src/models/validation_result.py`
- [X] T003 Export validation models from `backend/src/models/__init__.py`

---

## Phase 3: User Story 1 — Validate Module Structure Before Saving (Priority: P1) 🎯 MVP

- [X] T004 [US1] Write static validation tests covering all 6 static error codes and valid-module pass in `backend/tests/test_engine/test_validator.py`
- [X] T005 [US1] {FR-001,FR-002,FR-003,FR-004} Implement `validate_static()` with file pre-validation and AST-based structural analysis in `backend/src/engine/validator.py`

---

## Phase 4: User Story 2 — Prove a Module Works Against a Real Target (Priority: P2)

- [X] T006 [US2] Write runtime and orchestrator tests covering 3 runtime error codes, pass case, and static-fail skip in `backend/tests/test_engine/test_validator.py`
- [X] T007 [US2] {FR-005,FR-006,FR-007,FR-010} Implement `validate_runtime()` with timeout, error boundary, and HTTP client injection in `backend/src/engine/validator.py`
- [X] T008 [US2] {FR-008,FR-011} Implement `validate()` orchestrator (static → runtime pipeline, result assembly) in `backend/src/engine/validator.py`

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T009 [P] {FR-012} Refactor `ModuleLoader.scan()` to call `validate_static()` before `_safe_import()` and remove `_validate_module()` in `backend/src/engine/loader.py`
- [X] T010 [P] {FR-009} Export validation functions and `create_http_client` from `backend/src/engine/__init__.py`
- [X] T011 Update loader tests to verify static validator integration in `backend/tests/test_engine/test_loader.py`

---

## Dependencies

Setup → Foundational (blocks all stories) → US1 (P1) → US2 (P2) → Polish
Tasks marked [P] can run in parallel within their phase.
