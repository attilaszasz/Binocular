# Tasks: E011 — Official Sony Alpha Module

**Input**: Design documents from `specs/00011-official-sony-alpha-module/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`

## Project Mode

Brownfield

## Epic / Capability Map

- `[US1]` → Detect Firmware Version
- `[US2]` → Handle Parse Failures

## Brownfield Notes

- Existing flows touched: None (Sony Alpha is a new official module)
- Compatibility or migration concerns: None
- Regression focus: None

## Phase 1: Work Item 1 - Detect Firmware Version (Priority: P1) 🎯 MVP

- [x] T001 [P] [US1] {FR-005} Create Sony fixture HTML files in backend/tests/fixtures/sony_alpha/
- [x] T002 [US1] {FR-001,FR-002,FR-003} Implement official Sony Alpha module in backend/src/binocular/official_modules/sony_alpha.py → exports: check_firmware(url,model,http_client)
- [x] T003 [US1] {FR-005} [COMPLETES FR-005] Add parsing and model mapping tests in backend/tests/test_official_sony_alpha_module.py after:T002 ← T002:check_firmware

---

## Phase 2: Work Item 2 - Handle Parse Failures (Priority: P2)

- [x] T004 [US2] {FR-004} Implement failure diagnostic states in backend/src/binocular/official_modules/sony_alpha.py
- [x] T005 [US2] {FR-005} [COMPLETES FR-004] Implement failure test cases in backend/tests/test_official_sony_alpha_module.py after:T003

---

## Phase 3: Polish & Cross-Cutting Concerns

- [x] T006 [P] Create backend/src/binocular/official_modules/__init__.py and README.md
- [x] T007 [P] Run mypy and pytest to check compliance

---

## Dependencies

Delivery Work Items (by priority) → Polish

- Tasks marked `[P]` can run in parallel within their phase.
- Tasks with `after:T###` depend on the referenced task.
