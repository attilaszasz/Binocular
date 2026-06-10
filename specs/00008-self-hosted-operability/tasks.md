# Tasks: Self-Hosted Operability

**Project Mode**: brownfield
**Epic**: E008 | **Capability**: CAP-009 (Self-Hosted Operability)

## Phase 1: Setup

- [X] T001 Create backend package scaffolding for utilities at `backend/src/binocular/utils/__init__.py`
- [X] T002 Create `.env.example` at the repository root containing documentation and default environment values

## Phase 2: Configuration & Settings

- [X] T003 [US1] {FR-001,FR-002} Add configurable fields (`db_path`, `basic_auth_enabled`, `basic_auth_username`, `basic_auth_password`, `smtp_password`, `gotify_token`) to `Settings` in `backend/src/binocular/config.py`
- [X] T004 [US2] {FR-003,FR-004} Implement `load_secret_files` model validator in `Settings` to process `*_FILE` Docker-secret pattern paths in `backend/src/binocular/config.py`
- [X] T005 [US3] {FR-007} Implement `validate_basic_auth` model validator in `Settings` to ensure non-empty password when basic auth is enabled in `backend/src/binocular/config.py`
- [X] T006 [US1,US2,US3] Write unit tests for custom Settings loading, validation, and secret file resolving in `backend/tests/test_config.py` after:T003,T004,T005

## Phase 3: DB Path Integration

- [X] T007 [US1] {FR-002} [COMPLETES FR-002] Update `get_db_path` and `open_connection` in `backend/src/binocular/db/connection.py` to use settings-resolved `db_path` after:T003

## Phase 4: Structured Log Masking

- [X] T008 [US4] {FR-008} Implement log masking utility `mask_secrets_processor` and `set_secrets_to_mask` in `backend/src/binocular/utils/masking.py`
- [X] T009 [US4] {FR-008} Update `setup_logging` in `backend/src/binocular/logging.py` to accept settings and include `mask_secrets_processor` in the structlog pipeline after:T008
- [X] T010 [US4] {FR-008} Call `setup_logging` passing settings object in `backend/src/binocular/app.py` after:T009
- [X] T011 [US4] Write unit tests for log secret masking in `backend/tests/test_masking.py` after:T008
- [X] T012 [US4] Update logging tests in `backend/tests/test_logging.py` to adapt to the new `setup_logging` signature after:T009

## Phase 5: Optional Basic Authentication

- [X] T013 [US3] {FR-005,FR-006} Implement `BasicAuthMiddleware` in `backend/src/binocular/auth.py`
- [X] T014 [US3] {FR-005} Register the basic auth middleware in `backend/src/binocular/app.py` after:T013
- [X] T015 [US3] [COMPLETES FR-005] Write unit/integration tests for the basic auth middleware in `backend/tests/test_auth.py` after:T014

## Phase 6: Quality Gates & Verification

- [X] T016 Run `mypy --strict` on all new and modified backend modules to ensure type safety after:T010,T013
- [X] T017 Run `ruff check` on the backend code after:T010,T013
- [X] T018 Run `uv run pytest` and verify all tests pass with ≥80% coverage after:T015
