# Tasks: Official Godox Flashes Module

**Input**: Design documents from `specs/00025-official-godox-flashes-module-godox/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `checklists/` (complete)

**Tests**: Included — golden tests and failure-mode tests mandated by spec Success Criteria SC-001 through SC-008 and plan Testing Strategy.

**Organization**: Product spec grouped by user story (`US#`). Single module file serves all stories; tasks split by implementation unit and test focus.

## Project Mode

`Brownfield` — extends existing codebase; adds one module file + test file + five fixtures. No repo-wide scaffolding changes. No modified files (zero brownfield changes).

## Brownfield Notes

- Reference implementation: `backend/src/binocular/official_modules/panasonic_lumix_lenses.py` (E023) — reuse FirmwareEntry, _failed pattern, ModuleCheckInput/ModuleCheckResult contract
- Reference test: `backend/tests/test_official_panasonic_lumix_lenses_module.py` — reuse FakeScrapeClient pattern, ModuleLoader contract validation, source-code compliance checks
- Multi-URL FakeScrapeClient: extend the existing single-URL FakeScrapeClient to accept a `url_map: dict[str, str]` for pagination simulation (plan HINT-001)
- Seeder (`binocular/services/seeder.py`) auto-discovers `.py` files in `official_modules/` — no changes needed
- Module engine and authoring contract (`binocular/extensions/`) are unchanged
- LIGHTWEIGHT mode: no analysis phase, no repo-wide scaffolding, single-file module
- Godox uses a paginated listing (`/firmware-flash_N/`) with early termination, inert next-link detection, and 30-page circuit breaker — fundamentally multi-page unlike the single-page Panasonic module

---

## Phase 1: US1 - Flash Firmware Version Detection (Priority: P1) 🎯 MVP

- [X] T001 [P] [US1] {FR-001} Create page_1.html fixture at backend/tests/fixtures/godox_flashes/page_1.html with iT32 at V1.17, version format variations (V1.17, v2.6, V1.02, V1.3, V2.2), and inert next-link (javascript:;)
- [X] T002 [P] [US1] {FR-001} Create page_2.html fixture at backend/tests/fixtures/godox_flashes/page_2.html with additional flash entries for multi-page traversal
- [X] T003 [P] [US1] {FR-001} Create page_3.html fixture at backend/tests/fixtures/godox_flashes/page_3.html with V100S at V1.06, camera-brand suffix variants (V100C, V100N, V100F, V100O, V100P), and inert next-link
- [X] T004 [P] [US1] {FR-001} Create parse_error.html fixture at backend/tests/fixtures/godox_flashes/parse_error.html with zero parseable firmware entries (page structure changed)
- [X] T005 [P] [US1] {FR-001} Create empty_page.html fixture at backend/tests/fixtures/godox_flashes/empty_page.html with no firmware entries (for consecutive-empty termination testing)
- [X] T006 [US1] {FR-001,FR-004,FR-005} Create godox_flashes.py with MODULE_METADATA, FirmwareEntry dataclass, parse_page_entries, normalize_version, _build_page_url, extract_next_page_url, find_firmware_entry, _failed → exports: FirmwareEntry, parse_page_entries
- [X] T007 [US1] {FR-002,FR-003,FR-005,FR-006,FR-007} Implement check_firmware with full pagination loop (early termination on match, inert next-link detection, consecutive-empty fallback, 30-page circuit breaker) after:T006 → exports: check_firmware
- [X] T008 [P] [US1] {FR-001,FR-003} Write golden tests for page-1 hit (iT32 → "1.17") and multi-page detection (V100S on page 3 → "1.06") in test_official_godox_flashes_module.py after:T007

---

## Phase 2: US2 - Multi-Page Traversal & Honest Failure (Priority: P2)

- [X] T009 [P] [US2] {FR-005} Write failure-mode tests for all 4 error_types (product_not_found with full traversal, parse_error on page 1, firmware_page_unavailable with transport error, page_limit_exceeded) and edge cases (empty/whitespace model, unsuffixed model rejection, case-insensitive match) after:T007
- [X] T010 [P] [US2] {FR-002,FR-005,FR-006} Write pagination verification tests (URL construction, early termination at page N, inert next-link stop, consecutive-empty termination, circuit breaker at 30 pages) after:T007

---

## Phase 3: US3 - Module Contract Compliance & Seeding (Priority: P2)

- [X] T011 [P] [US3] {FR-008} Write contract-load and MODULE_METADATA compliance tests (module_id, display_name, version, author, supported_device_hints) after:T007
- [X] T012 [US3] {FR-007} Write source-code compliance test verifying no direct HTTP imports (httpx, requests, aiohttp, urllib.request) and no banned imports (subprocess, eval, exec, pickle, ctypes) in module source after:T006

---

## Dependencies

Phase 1 (T001–T008) → Phase 2 (T009–T010) → Phase 3 (T011–T012)

- **Setup**: omitted — brownfield project; no repo-wide tooling or config changes
- **Foundational**: omitted — module file is a single artifact; no cross-work-item infrastructure blockers
- **US1 (Phase 1)**: fixtures (T001–T005 in parallel) → module core (T006) → check_firmware (T007) → golden tests (T008)
- **US2 (Phase 2)**: depends on T007 (module check_firmware complete); T009 and T010 run in parallel
- **US3 (Phase 3)**: T011 depends on T007; T012 depends on T006 (module file must exist for source scan)
- Tasks marked `[P]` are parallel-safe within their phase
- Tasks with `after:T###` require the referenced task to be `[X]` before execution
