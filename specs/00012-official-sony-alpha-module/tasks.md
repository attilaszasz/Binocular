# Tasks: Official Sony Alpha Module

**Input**: Design documents from `specs/00012-official-sony-alpha-module/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `checklists/`
**Tests**: Included because FR-005 and SC-001 require fixture-backed golden correctness tests.

## Project Mode

`Brownfield`

## Epic / Capability Map

- `[US1]` → Detect Sony Alpha updates
- `[US2]` → Surface Sony scrape failures

## Brownfield Notes

- Existing flows touched: module contract models, module runner expectations, version comparator service.
- Compatibility or migration concerns: no schema migration; no API changes; no direct HTTP client usage in module.
- Regression focus: official module fixture parsing, visible parser failure, version comparison for `2.00` -> `2.01`.

## Phase 1: Foundational (Cross-Work-Item Blockers)

- [X] T001 [P] {FR-001} Create official module package in backend/src/binocular/official_modules/__init__.py
- [X] T002 [P] {FR-005} Add Sony fixture HTML files in backend/tests/fixtures/sony_alpha/
- [X] T003 {FR-001,FR-003} Implement Sony Alpha module metadata and injected-client fetch path in backend/src/binocular/official_modules/sony_alpha.py → exports: check_firmware(input,client)

---

## Phase 2: Work Item 1 - Detect Sony Alpha Updates (Priority: P1) 🎯 MVP

- [X] T004 [US1] {FR-002,FR-005} Add A7CII golden tests in backend/tests/test_official_sony_alpha_module.py after:T003
- [X] T005 [US1] {FR-002} Implement Sony version extraction for ILCE-7CM2 in backend/src/binocular/official_modules/sony_alpha.py after:T004
- [X] T006 [US1] {FR-005} Add comparator assertion for current 2.00 vs latest 2.01 in backend/tests/test_official_sony_alpha_module.py after:T005

---

## Phase 3: Work Item 2 - Surface Sony Scrape Failures (Priority: P2)

- [X] T007 [US2] {FR-004} Add unparseable-fixture failure test in backend/tests/test_official_sony_alpha_module.py after:T005
- [X] T008 [US2] {FR-004} Implement visible Sony parse failure diagnostics in backend/src/binocular/official_modules/sony_alpha.py after:T007

---

## Phase 4: Polish & Cross-Cutting Concerns

- [X] T009 {FR-001,FR-003} Document official module trust and scraping rules in backend/src/binocular/official_modules/README.md after:T008
- [X] T010 {FR-005} Run focused backend validation for Sony official module fixtures

---

## Phase 5: Corrective Rerun - Alpha Universe Full Catalog

- [X] T011 {FR-002,FR-005} Replace single-model fixture with Alpha Universe camera/lens catalog fixture in backend/tests/fixtures/sony_alpha/
- [X] T012 {FR-002,FR-004} Generalize Sony parser to Alpha Universe catalog entries in backend/src/binocular/official_modules/sony_alpha.py after:T011
- [X] T013 {FR-002} [COMPLETES FR-002] Add camera, lens, alias, and comparator tests in backend/tests/test_official_sony_alpha_module.py after:T012
- [X] T014 {FR-004} [COMPLETES FR-004] Add unlisted and no-firmware failure tests in backend/tests/test_official_sony_alpha_module.py after:T012
- [X] T015 {FR-001} [COMPLETES FR-001] Update official module docs for Alpha Universe full-catalog support in backend/src/binocular/official_modules/README.md after:T012
- [X] T016 {FR-003} [COMPLETES FR-003] Verify official Sony module still uses only injected ScrapeClient in backend/tests/test_official_sony_alpha_module.py after:T012
- [X] T017 {FR-005} [COMPLETES FR-005] Run focused backend validation for Alpha Universe Sony fixtures after:T013

---

## Dependencies

Foundational → US1 P1 detection → US2 P2 failure behavior → Polish documentation/validation

- T003 depends on T001 and T002.
- T004 depends on T003.
- T005 depends on T004.
- T006 depends on T005.
- T007 depends on T005.
- T008 depends on T007.
- T009 depends on T008.
- T010 depends on T009.
- T012 depends on T011.
- T013, T014, T015, and T016 depend on T012.
- T017 depends on T013, T014, and T016.
- Tasks marked `[P]` can run in parallel within their phase.