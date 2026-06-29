# Tasks: E025 — Official Viltrox Lenses Module

**Input**: Design documents from `specs/00026-official-viltrox-lenses-module/`
**Prerequisites**: `plan.md` (required), `spec.md` (required)

**Tests**: Fixture-based tests are required by FR-008 and SC-002/SC-003/SC-004; tests are grouped in the Polish phase per the suggested layout.

**Organization**: Brownfield feature — adds a single new official module to an existing starter set. Delivery tasks span three user stories (US1, US2, US3) inside one "Stories" phase, each task carrying the dominant `[US#]` label. `after:T###` edges make cross-phase dependencies explicit.

## Project Mode

`Brownfield`

- Extends `backend/src/binocular/official_modules/` with one new module file conforming to the V1 authoring contract (ADR-0005).
- No project-root tooling, workspace config, or shared wiring changes.
- Reuses the sync-over-async pattern (`asyncio.new_event_loop` + `try/finally`) from `panasonic_lumix_lenses.py` / `godox_flashes.py`.
- Reuses the `FakeScrapeClient` + `read_fixture` test pattern from existing module test files.

## Epic / Capability Map

- `[US1]` → Detect Firmware Version (P1, MVP) — covered by T004 (index walk), T005 (lens page parse), T006 (top-entry extraction), T007 (model key resolution).
- `[US2]` → Reject Companion App Version (P1) — structurally enforced by T005 (section isolation) and T006 (defensive regex); verified by T009 fixture tests.
- `[US3]` → Handle Parse Failures (P2) — covered by T008 (typed diagnostic error paths).

## Brownfield Notes

- Existing flows touched: None. The new module plugs into the existing module engine (E007), scheduler (E013), and seeder (E016) without changes to those subsystems.
- Compatibility or migration concerns: None. No new external dependencies, no new storage, no schema changes.
- Regression focus: Other official modules must continue to pass `mypy --strict` and `Ruff`; the seeder must continue to auto-discover all `.py` files in `official_modules/`.

## Phase 1: Setup (Repository / Workspace Delta)

**Brownfield setup for the new module + test file skeletons. No project-root config touched.**

- [X] T001 [P] {FR-001,FR-002,FR-009,FR-010} Add viltrox_lenses.py skeleton (MODULE_VERSION, SUPPORTED_DEVICE_TYPE, check_firmware signature) at backend/src/binocular/official_modules/viltrox_lenses.py
- [X] T002 [P] {FR-008} Add test file skeleton (FakeScrapeClient, read_fixture helper, empty fixture dir) at backend/tests/test_official_viltrox_lenses_module.py and backend/tests/fixtures/viltrox_lenses/

---

## Phase 2: Foundational (Cross-Work-Item Blockers)

**Module-level URL constants, regexes, normalizers, and the section-scoped `### Document Download` parser — shared by all three user stories.**

- [X] T003 {FR-004,FR-005,FR-006} Add URL constants, normalizers, and Document Download section parser in backend/src/binocular/official_modules/viltrox_lenses.py → exports: _normalize_model,find_document_download_section

---

## Phase 3: Stories (US1 + US2 + US3) (Priority: P1 + P2)

**Five implementation units covering the three user stories. US1 (P1) is the MVP; US2 (P1) is structurally enforced inside T005/T006; US3 (P2) is the typed-error task T008.**

- [X] T004 [US1] {FR-003,FR-005} Implement index walk in backend/src/binocular/official_modules/viltrox_lenses.py using display name + page-slug fallback after:T003 → exports: parse_index_entries,find_lens_link
- [X] T005 [US1] {FR-004,FR-006} Implement lens page entries parser in backend/src/binocular/official_modules/viltrox_lenses.py using Document Download sub-tree from T003 after:T003 → exports: parse_lens_page_entries
- [X] T006 [US1] {FR-004,FR-006} [COMPLETES FR-004,FR-006] Add top-entry version extraction in backend/src/binocular/official_modules/viltrox_lenses.py with companion app guard after:T005 → exports: extract_top_entry_version
- [X] T007 [US1] {FR-005} [COMPLETES FR-005] Add model key resolution (display name primary, page-slug fallback) in backend/src/binocular/official_modules/viltrox_lenses.py after:T004
- [X] T008 [US3] {FR-007} Add typed diagnostic error paths (parse_error, product_not_found, firmware_not_available, download_url_not_found) in check_firmware in backend/src/binocular/official_modules/viltrox_lenses.py after:T006

---

## Phase 4: Polish & Cross-Cutting Concerns

**Fixture-based zero-FP/FN tests, static checks, and engine integration. Regression sweep against existing modules.**

- [X] T009 [P] {FR-008} Add golden/fixture-based tests using captured index + per-lens HTML fixtures in backend/tests/test_official_viltrox_lenses_module.py after:T006
- [X] T010 {FR-001,FR-009,FR-010} [COMPLETES FR-001,FR-010] Add mypy --strict + Ruff verification, seeder auto-discovery, ModuleRunner integration in backend/tests/test_official_viltrox_lenses_module.py after:T009

---

## Dependencies

Setup → Foundational → Stories (US1, US2, US3) → Polish

- **T001, T002** can run in parallel — different files, no shared dependencies.
- **T003** blocks **T004** and **T005** — both consume the section parser and normalizers.
- **T004** blocks **T007**; **T005** blocks **T006** — sequential T### ordering within the Stories phase carries the edge.
- **T006** blocks **T008** and **T009** — entry point must exist before error paths and tests.
- **T009** blocks **T010** — lint/seeder/runner sweep runs after tests are in place.
- **`[COMPLETES]` markers**: T006 ends the FR-004 / FR-006 chain (T003, T005, T006); T007 ends the FR-005 chain (T003, T004, T007); T010 ends the FR-001 / FR-010 chain (T001, T006, T010).
- **Parallel safety**: T001, T002, T009 are marked `[P]`; none has an `after:T###` or `← T###:Symbol` that would create a same-batch violation.
- **Cross-phase `after:T###` edges**: T004, T005 (`after:T003`); T006 (`after:T005`); T007 (`after:T004`); T008 (`after:T006`); T009 (`after:T006`); T010 (`after:T009`) — these are explicit for resume and parallel-safety checks.
- The implementing agent MUST verify each `after:T###` reference resolves to a `[X]` task before executing the dependent task.
