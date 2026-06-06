# Tasks: Official Panasonic Lumix Lenses Module

**Input**: Design documents from `specs/00024-official-panasonic-lumix-lenses-module/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `checklists/` (complete)

**Tests**: Included — golden tests and failure-mode tests mandated by spec Success Criteria SC-001 through SC-006 and plan Testing Strategy.

**Organization**: Product spec grouped by user story (`US#`). Single module file serves all stories; tasks split by implementation unit and test focus.

## Project Mode

`Brownfield` — extends existing codebase; adds one module file + test file + two fixtures. No repo-wide scaffolding changes.

## Brownfield Notes

- Reference implementation: `backend/src/binocular/official_modules/panasonic_lumix.py` (E020)
- Existing `FakeScrapeClient` pattern in `backend/tests/test_official_panasonic_lumix_mft_cameras_module.py` to reuse
- Seeder (`binocular/services/seeder.py`) auto-discovers `.py` files in `official_modules/` — no changes needed
- Module engine and authoring contract (`binocular/extensions/`) are unchanged
- Compatibility: lens module uses dedicated URL (`index5.html`) and distinct model regex (`^[SH]-[A-Z0-9]+$`); no collision with existing cameras module (E020)

---

## Phase 1: US1 - Lens Firmware Version Detection (Priority: P1) 🎯 MVP

- [x] T001 [P] [US1] {FR-001} Create main lens fixture HTML at backend/tests/fixtures/panasonic_lumix_lenses/panasonic_firmware_index.html
- [x] T002 [P] [US1] {FR-001} Create unparseable fixture HTML at backend/tests/fixtures/panasonic_lumix_lenses/unparseable.html
- [x] T003 [US1] {FR-001,FR-002,FR-005,FR-007} Create panasonic_lumix_lenses.py with FirmwareEntry, parse_firmware_entries, _download_handlers → exports: FirmwareEntry,parse_firmware_entries
- [x] T004 [US1] {FR-003,FR-004,FR-006,FR-008} Implement check_firmware, _failed, extract_latest_version, find_firmware_entry after:T003 ← T003:parse_firmware_entries → exports: check_firmware
- [x] T005 [P] [US1] {FR-001,FR-002,FR-003,FR-005} Write golden tests for lens detection and download URL validation in test_official_panasonic_lumix_lenses_module.py after:T004

---

## Phase 2: US2 - Honest Failure Signaling (Priority: P2)

- [x] T006 [P] [US2] {FR-004} Write failure-mode tests for all 5 error_types in test_official_panasonic_lumix_lenses_module.py after:T004
- [x] T007 [US2] {FR-001,FR-004} Write edge-case tests for empty model input, camera body rejection, and concurrent safety after:T004

---

## Phase 3: US3 - Module Contract Compliance & Seeding (Priority: P2)

- [x] T008 [P] [US3] {FR-003,FR-007} Write contract-load, MODULE_METADATA, and seeder auto-discovery tests after:T004
- [x] T009 [US3] {FR-006} Write source-code compliance test verifying no direct HTTP imports or os.environ reads after:T004

---

## Dependencies

Phase 1 (T001–T005) → Phase 2 (T006–T007) → Phase 3 (T008–T009)

- **Setup**: omitted — brownfield project; no repo-wide tooling or config changes
- **Foundational**: omitted — module file is a single artifact; no cross-work-item infrastructure blockers
- **US1 (Phase 1)**: fixtures (T001–T002 in parallel) → module parsing core (T003) → check_firmware (T004) → golden tests (T005)
- **US2 (Phase 2)**: depends on T004 (module check_firmware complete); T006 runs in parallel
- **US3 (Phase 3)**: depends on T004; T008 runs in parallel
- Tasks marked `[P]` are parallel-safe within their phase
- Tasks with `after:T###` require the referenced task to be `[X]` before execution
