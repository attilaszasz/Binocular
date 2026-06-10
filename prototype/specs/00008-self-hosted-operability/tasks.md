# Tasks: Self-Hosted Operability

## Project Mode

Brownfield — extend the existing FastAPI backend settings/app factory, Docker deployment files, and backend test suites.

## Epic / Capability Map

- [US1] → Zero-config durable startup.
- [US2] → Docker-compatible secret loading.
- [US3] → Optional basic protection.
- [US4] → Copy-ready deployment examples.

## Brownfield Notes

- Existing flows touched: `backend/src/binocular/config.py`, `backend/src/binocular/app.py`, `Dockerfile`, backend pytest suites.
- Compatibility concerns: preserve no-env startup, `/healthz` unauthenticated, non-root image, and SQLite single-volume behavior.
- Regression focus: secret values never logged, static/SPA routes protected consistently when auth is enabled.

## Phase 1: Foundational

- [X] T001 {FR-003,FR-004,FR-005} Add secret-file settings tests in backend/tests/test_config.py → exports: secret_resolution_cases
- [X] T002 {FR-003,FR-004,FR-005} Implement `_FILE` secret resolution in backend/src/binocular/config.py after:T001 → exports: resolve_secret_setting()
- [X] T003 {FR-006,FR-007,FR-008} Add auth middleware tests in backend/tests/test_auth.py → exports: auth_client_cases
- [X] T004 {FR-006,FR-007,FR-008} Implement optional basic auth middleware in backend/src/binocular/auth.py after:T003 → exports: BasicAuthMiddleware
- [X] T005 {FR-006,FR-007} Register auth middleware in backend/src/binocular/app.py after:T004 ← T004:BasicAuthMiddleware

## Phase 2: US1 — Zero-Config Durable Startup (Priority: P1) 🎯 MVP

- [X] T006 [US1] {FR-001,FR-002} Add operability smoke tests in backend/tests/test_operability_smoke.py after:T002
- [X] T007 [US1] {FR-001,FR-002} Preserve zero-config data/module defaults in backend/src/binocular/config.py after:T006 [COMPLETES FR-001]
- [X] T008 [US1] {FR-002} Add persistence restart/upgrade smoke helper in backend/tests/test_operability_smoke.py after:T007 [COMPLETES FR-002]

## Phase 3: US2 — Docker-Compatible Secret Loading (Priority: P1) 🎯 MVP

- [X] T009 [US2] {FR-003,FR-004,FR-005} Add secret error redaction assertions in backend/tests/test_config.py after:T002
- [X] T010 [US2] {FR-003,FR-004,FR-005} Wire auth password `_FILE` support in backend/src/binocular/config.py after:T009 [COMPLETES FR-003] [COMPLETES FR-004]
- [X] T011 [US2] {FR-005} Add direct-plus-file conflict validation in backend/src/binocular/config.py after:T010 [COMPLETES FR-005]

## Phase 4: US3 — Optional Basic Protection (Priority: P1) 🎯 MVP

- [X] T012 [US3] {FR-006,FR-007,FR-008} Add API/UI/static auth route tests in backend/tests/test_auth.py after:T005
- [X] T013 [US3] {FR-006,FR-007} Ensure `/healthz` bypasses auth in backend/src/binocular/auth.py after:T012
- [X] T014 [US3] {FR-008} Add constant-time credential comparison in backend/src/binocular/auth.py after:T013 [COMPLETES FR-008]
- [X] T015 [US3] {FR-006,FR-007} Verify auth-off default and auth-on challenge behavior in backend/tests/test_auth.py after:T014 [COMPLETES FR-006] [COMPLETES FR-007]

## Phase 5: US4 — Copy-Ready Deployment Examples (Priority: P2)

- [X] T016 [US4] {FR-009,FR-010,FR-011} Add deployment docs tests in backend/tests/test_operability_docs.py
- [X] T017 [US4] {FR-009} Create compose.yaml with one port and data/modules volumes after:T016 [COMPLETES FR-009]
- [X] T018 [US4] {FR-010} Create .env.example with safe operability/auth defaults after:T017 [COMPLETES FR-010]
- [X] T019 [US4] {FR-011} Update README.md trust-boundary deployment wording after:T018 [COMPLETES FR-011]

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T020 Run backend Ruff, mypy strict, pytest coverage, and docs smoke checks for operability changes

## Dependencies

- Foundational tasks precede US1, US2, and US3 implementation.
- US2 depends on the shared secret resolver from T002.
- US3 depends on auth middleware registration from T005.
- US4 docs can run after checklist completion but before final QC.
- Final validation depends on all delivery phases.
