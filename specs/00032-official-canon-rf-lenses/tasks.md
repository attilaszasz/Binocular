# Tasks: E029 — Official Canon RF Lenses

**Input**: Design documents from `specs/00032-official-canon-rf-lenses/`
**Prerequisites**: `plan.md`, `spec.md`, completed `checklists/`

**Tests**: Captured-fixture zero-FP/FN, integration, deterministic pacing, strict typing, lint, security, and coverage are mandatory.

## Project Mode

`Brownfield` — add one official module, fixtures, tests, and coverage documentation; reuse the camera-module patterns, loader, runner, seeder, and scoped ScrapeClient.

## Epic / Capability Map

- `[US1]` → exact classified model-only RF/RF-S discovery and deduplicated release result (P1 MVP).
- `[US2]` → visible exclusions, no-firmware, drift, denial, timeout, and cancellation outcomes (P1).
- `[US3]` → shared polite and bounded Canon-origin execution without configuration (P2).

## Phase 1: Setup

- [X] T001 [P] [US1] {FR-001} Add the official lens module contract skeleton and Canon catalogue constants in backend/src/binocular/official_modules/canon_rf_lenses.py → exports: MODULE_VERSION,SUPPORTED_DEVICE_TYPE,check_firmware
- [X] T002 [P] [US1] {FR-010} Add captured RF/RF-S catalogue, product, firmware, no-firmware, and malformed fixtures under backend/tests/fixtures/canon_rf_lenses/

---

## Phase 2: Foundational

- [X] T003 [US1] {FR-002} Implement both-catalogue parsing and trimmed case-folded exact model resolution in backend/src/binocular/official_modules/canon_rf_lenses.py after:T001 → exports: _parse_catalog,_resolve_product
- [X] T004 [US2] {FR-003} Implement conservative RF/RF-S lens classification with accessory, extender, cinema, and unrelated-mount exclusion in backend/src/binocular/official_modules/canon_rf_lenses.py after:T003 → exports: _is_supported_lens
- [X] T005 [US1] {FR-004} Implement verbatim product-link resolution and unique firmware form-action discovery in backend/src/binocular/official_modules/canon_rf_lenses.py after:T004 → exports: _parse_firmware_action
- [X] T006 [US1] {FR-005} Implement firmware-row parsing, numeric version ordering, OS-package deduplication, and official detail-link resolution in backend/src/binocular/official_modules/canon_rf_lenses.py after:T005 → exports: _parse_releases,_select_latest

---

## Phase 3: Stories

- [X] T007 [US1] {FR-001,FR-004,FR-005,FR-009} [COMPLETES FR-001,FR-004,FR-005,FR-009] Wire the bounded RF/RF-S catalogue-to-product-to-firmware flow through the injected client in check_firmware at backend/src/binocular/official_modules/canon_rf_lenses.py after:T006
- [X] T008 [US2] {FR-002,FR-003,FR-006} [COMPLETES FR-002,FR-003,FR-006] Add typed unsupported, no-firmware, source-drift, and network failure paths without inferred success or positive RF-S claims in backend/src/binocular/official_modules/canon_rf_lenses.py after:T007
- [X] T009 [US3] {FR-007,FR-008} [COMPLETES FR-007,FR-008] Verify the module uses only the injected scoped client and preserves timeout/cancellation authority in backend/tests/test_official_canon_rf_lenses_module.py after:T007

---

## Phase 4: Verification & Documentation

- [X] T010 [P] [US1] {FR-010} Add contract, classification, exact-match, action-discovery, RF24-105mm golden, OS-deduplication, and newest-release tests in backend/tests/test_official_canon_rf_lenses_module.py after:T002,T007
- [X] T011 [US2] {FR-006,FR-010} Add accessory, unrelated-mount, near-name, RF-S no-firmware, malformed, denied, timeout, and cancellation tests in backend/tests/test_official_canon_rf_lenses_module.py after:T008,T010
- [X] T012 [US3] {FR-007,FR-008,FR-010} Add deterministic shared camera/lens Canon-origin concurrency/retry pacing and no-late-request integration coverage in backend/tests/scraping/test_client.py after:T009,T011
- [X] T013 [P] [US3] {FR-011} [COMPLETES FR-011] Document Canon Asia region, RF/RF-S classification, release semantics, 30-second pacing, exclusions, and RF-S evidence status in backend/src/binocular/official_modules/README.md after:T007
- [X] T014 {FR-001,FR-010} [COMPLETES FR-001,FR-010] Run module/seeder tests, full backend tests with coverage, Ruff, mypy strict, and dependency audit; fix regressions after:T011,T012,T013

---

## Dependencies

Setup → Foundational → Stories → Verification & Documentation

- T001 and T002 are parallel; T003 → T004 → T005 → T006 → T007 is the source-flow chain.
- T008 and T009 depend on the complete happy path; T010 joins fixtures with T007.
- T011 joins failure handling with golden tests; T012 follows module integration coverage.
- T013 can run after T007 in parallel with test expansion; T014 is the final verification gate.
- Every `after:T###` reference must resolve to `[X]` before the dependent task runs.

## Validation

- FR-001 through FR-011 and US1 through US3 are covered.
- Parallel tasks touch independent files or run only after their shared-file prerequisite.
- Requirement completion markers appear on the final task in each multi-task chain.
