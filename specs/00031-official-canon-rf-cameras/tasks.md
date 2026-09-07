# Tasks: E028 — Official Canon RF Cameras

**Input**: Design documents from `specs/00031-official-canon-rf-cameras/`
**Prerequisites**: `plan.md`, `spec.md`, completed `checklists/`

**Tests**: Captured-fixture zero-FP/FN, integration, deterministic pacing, strict typing, lint, security, and coverage are mandatory.

## Project Mode

`Brownfield` — add one official module, fixtures, tests, and coverage documentation; reuse existing loader, runner, seeder, and scoped ScrapeClient.

## Epic / Capability Map

- `[US1]` → exact model-only EOS R discovery and deduplicated release result (P1 MVP).
- `[US2]` → visible unsupported, drift, denial, timeout, and cancellation outcomes (P1).
- `[US3]` → shared polite and bounded Canon-origin execution without configuration (P2).

## Phase 1: Setup

- [X] T001 [P] [US1] {FR-001} Add the official module contract skeleton and Canon source constants in backend/src/binocular/official_modules/canon_rf_cameras.py → exports: MODULE_VERSION,SUPPORTED_DEVICE_TYPE,check_firmware
- [X] T002 [P] [US1] {FR-009} Add captured Canon catalogue, product, firmware, no-firmware, and malformed fixture files under backend/tests/fixtures/canon_rf_cameras/

---

## Phase 2: Foundational

- [X] T003 [US1] {FR-002} Implement trimmed case-folded exact catalogue parsing and unique model resolution in backend/src/binocular/official_modules/canon_rf_cameras.py after:T001 → exports: _parse_catalog,_resolve_product
- [X] T004 [US1] {FR-003} Implement verbatim product-link resolution and unique firmware form-action discovery in backend/src/binocular/official_modules/canon_rf_cameras.py after:T003 → exports: _parse_firmware_action
- [X] T005 [US1] {FR-004} Implement firmware-row parsing, numeric version ordering, OS-package deduplication, and official detail-link resolution in backend/src/binocular/official_modules/canon_rf_cameras.py after:T004 → exports: _parse_releases,_select_latest

---

## Phase 3: Stories

- [X] T006 [US1] {FR-001,FR-003,FR-004,FR-008} [COMPLETES FR-001,FR-003,FR-004,FR-008] Wire the bounded catalogue-to-product-to-firmware flow through the injected client in check_firmware at backend/src/binocular/official_modules/canon_rf_cameras.py after:T005
- [X] T007 [US2] {FR-002,FR-005} [COMPLETES FR-002,FR-005] Add typed unsupported, no-firmware, source-drift, and network failure paths without inferred success in backend/src/binocular/official_modules/canon_rf_cameras.py after:T006
- [X] T008 [US3] {FR-006,FR-007} [COMPLETES FR-006,FR-007] Verify the module uses only the injected scoped client and preserves timeout/cancellation authority in backend/tests/test_official_canon_rf_cameras_module.py after:T006

---

## Phase 4: Verification & Documentation

- [X] T009 [P] [US1] {FR-009} Add contract, exact-match, action-discovery, EOS R5 golden, OS-deduplication, and newest-release tests in backend/tests/test_official_canon_rf_cameras_module.py after:T002,T006
- [X] T010 [US2] {FR-005,FR-009} Add unknown, near-name, R5 C, no-firmware, malformed, denied, timeout, and cancellation tests in backend/tests/test_official_canon_rf_cameras_module.py after:T007,T009
- [X] T011 [US3] {FR-006,FR-007,FR-009} Add deterministic shared Canon-origin concurrency/retry pacing and no-late-request integration coverage in backend/tests/scraping/test_client.py after:T008,T010
- [X] T012 [P] [US3] {FR-010} [COMPLETES FR-010] Document Canon Asia region, EOS R boundary, release semantics, 30-second pacing, and Cinema EOS/EOS R5 C exclusion in backend/src/binocular/official_modules/README.md after:T006
- [X] T013 {FR-001,FR-009} [COMPLETES FR-001,FR-009] Run module/seeder tests, full backend tests with coverage, Ruff, mypy strict, and pip-audit; fix regressions after:T010,T011,T012

---

## Dependencies

Setup → Foundational → Stories → Verification & Documentation

- T001 and T002 are parallel; T003 → T004 → T005 → T006 is the source-flow chain.
- T007 and T008 depend on the complete happy path; T009 joins fixtures with T006.
- T010 joins failure handling with golden tests; T011 follows module integration coverage.
- T012 can run after T006 in parallel with test expansion; T013 is the final verification gate.
- Every `after:T###` reference must resolve to `[X]` before the dependent task runs.

## Validation

- FR-001 through FR-010 and US1 through US3 are covered.
- Parallel tasks touch independent files or run only after their shared-file prerequisite.
- Requirement completion markers appear on the final task in each multi-task chain.
