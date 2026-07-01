# Tasks: E026 — Official Nikon Z-Series Module

**Input**: Design documents from `specs/00027-official-nikon-z-series-module/`
**Prerequisites**: `plan.md` (required), `spec.md` (required)

**Tests**: Fixture-based zero-FP/FN tests required by FR-011 and SC-002/SC-003/SC-004; tests are grouped in the Polish phase per the suggested layout.

**Organization**: Brownfield feature — adds a single new official module to an existing starter set. Delivery tasks span three user stories (US1, US2, US3) inside one "Stories" phase, each task carrying the dominant `[US#]` label. `after:T###` edges make cross-phase dependencies explicit.

## Project Mode

`Brownfield`

- Extends `backend/src/binocular/official_modules/` with one new module file conforming to the V1 authoring contract (ADR-0005).
- No project-root tooling, workspace config, or shared wiring changes.
- Reuses the sync-over-async pattern (`asyncio.new_event_loop` + `run_until_complete` in `try/finally`) from `panasonic_lumix_lenses.py` / `godox_flashes.py` / `viltrox_lenses.py`.
- Reuses the `FakeScrapeClient` + `read_fixture` test pattern and the `_ROW_RE`/`_CELL_RE` regex idiom from `panasonic_lumix.py`.
- Parses the XML catalog with stdlib `xml.etree.ElementTree` (no new external dependency; no BeautifulSoup).

## Epic / Capability Map

- `[US1]` → Detect Firmware Version (P1, MVP) — covered by T004 (XML catalog fetch + category filter), T005 (alias-set resolution), T006 (product-page fetch + pseudoTable parse), T007 (prefix strip + date norm + download_url resolution).
- `[US2]` → Model-Key Normalization (P1) — structurally enforced by T005 (alias-set intersection across display-name / no-space / slug / lowercase / Roman-numeral forms); verified by T010 model-normalization tests.
- `[US3]` → Handle Failures Honestly (P2) — covered by T008 (five typed `ValueError` error paths); verified by T011 failure-path tests.

## Brownfield Notes

- Existing flows touched: None. The new module plugs into the existing module engine (E007), scheduler (E013), seeder (E016), and health monitor (E020) without changes to those subsystems.
- Compatibility or migration concerns: None. No new external dependencies (stdlib `xml.etree.ElementTree` + `re` only), no new storage, no schema changes.
- Regression focus: Other official modules must continue to pass `mypy --strict` and Ruff; the seeder must continue to auto-discover all `.py` files in `official_modules/`; E020 must surface consistent Nikon failures like other official modules.

## Phase 1: Setup (Repository / Workspace Delta)

**Brownfield setup for the new module + test file skeletons. No project-root config touched. The module skeleton wires the sync-over-async pattern (`asyncio.new_event_loop` + `run_until_complete` in `try/finally`) per HINT-001.**

- [X] T001 [P] {FR-001,FR-002} Add nikon_z_series.py skeleton (MODULE_VERSION="1.0.0", SUPPORTED_DEVICE_TYPE="camera", check_firmware signature, event-loop scaffold) at backend/src/binocular/official_modules/nikon_z_series.py → exports: check_firmware,MODULE_VERSION,SUPPORTED_DEVICE_TYPE
- [X] T002 [P] {FR-011} Add test file skeleton (FakeScrapeClient, read_fixture helper, empty fixture dir) at backend/tests/test_official_nikon_z_series_module.py and backend/tests/fixtures/nikon_z_series/ → exports: FakeScrapeClient,read_fixture

---

## Phase 2: Foundational (Cross-Work-Item Blockers)

**Module-level URL constants, alias-set model normalizer, and the `#firmware` pseudoTable regex parsers (`_ROW_RE`/`_CELL_RE` idiom from `panasonic_lumix.py`) — shared by all three user stories. Class-agnostic `<token>:Ver.` strip regex is `^[A-Z]+:Ver\.` (HINT-003); alias-set normalization per FR-004.**

- [X] T003 {FR-003,FR-004,FR-005,FR-006} Add URL constants, alias-set model normalizer, and #firmware pseudoTable regex parsers in backend/src/binocular/official_modules/nikon_z_series.py → exports: _CATALOG_URL,_normalize_model,_ROW_RE,_CELL_RE

---

## Phase 3: Stories (US1 + US2 + US3) (Priority: P1 + P2)

**Five implementation units covering the three user stories. US1 (P1) is the MVP — two-step fetch order (HINT-002): catalog → model resolution → product page → row extraction. US2 (P1) is structurally enforced inside T005; US3 (P2) is the typed-error task T008.**

- [X] T004 [US1] {FR-003,FR-010} Implement XML catalog fetch (via injected http_client) + Mirrorless Cameras / Z Series category filter using xml.etree.ElementTree in backend/src/binocular/official_modules/nikon_z_series.py after:T003 → exports: _fetch_catalog,_select_z_series_products
- [X] T005 [US1] {FR-004} [COMPLETES FR-004] Implement alias-set model resolution (display/no-space/slug forms, Roman-numeral variants) against Z Series products in backend/src/binocular/official_modules/nikon_z_series.py after:T004 → exports: _resolve_product
- [X] T006 [US1] {FR-005,FR-010} Implement product-page fetch (via injected http_client) + #firmware pseudoTable first-row parse in backend/src/binocular/official_modules/nikon_z_series.py after:T005 → exports: _fetch_product_page,_parse_first_firmware_row
- [X] T007 [US1] {FR-006,FR-007,FR-008} [COMPLETES FR-003,FR-006] Add class-agnostic prefix strip + YYYY/MM/DD→YYYY-MM-DD date norm + relative→absolute download_url resolution in backend/src/binocular/official_modules/nikon_z_series.py after:T006 → exports: _strip_version_prefix,_normalize_date,_resolve_download_url
- [X] T008 [US3] {FR-009} [COMPLETES FR-009] Add five typed ValueError error paths (network_error, firmware_index_not_found, product_not_found, firmware_not_available, download_url_not_found; NOT parse_error) in check_firmware in backend/src/binocular/official_modules/nikon_z_series.py after:T007

---

## Phase 4: Polish & Cross-Cutting Concerns

**Fixture capture, golden/fixture-based zero-FP/FN tests, static checks, and engine integration. Regression sweep against existing modules. Golden: `Z 30` → `latest_version "1.20"`, `release_date "2025-05-07"`, `download_url https://downloadcenter.nikonimglib.com/en/download/fw/556.html`.**

- [X] T009 [P] {FR-011} Capture fixtures (product_data.xml, Z_30.html, empty_firmware_page.html, no_firmware_section_page.html, no_z_series_catalog.xml, unlisted_model_catalog.xml) under backend/tests/fixtures/nikon_z_series/ after:T002
- [X] T010 {FR-011} Add golden happy-path + model-normalization tests (Z 30/Z30/Z_30/z 30/z30/z_30; Z 6II/Z6II/Z_6II/Z 6 II) in backend/tests/test_official_nikon_z_series_module.py after:T008,T009
- [X] T011 {FR-011} [COMPLETES FR-011] Add failure-path tests (5 standardized error codes) against captured failure-mode fixtures in backend/tests/test_official_nikon_z_series_module.py after:T010
- [X] T012 {FR-010,FR-012,FR-013} [COMPLETES FR-010,FR-012,FR-013] Verify mypy --strict + Ruff clean (no direct HTTP imports), ≥80% coverage, seeder auto-discovery (E016) + E020 monitoring in backend/tests/test_official_nikon_z_series_module.py after:T011

---

## Dependencies

Setup → Foundational → Stories (US1, US2, US3) → Polish

- **T001, T002** can run in parallel — different files, no shared dependencies.
- **T003** blocks **T004** — T004 consumes the URL constants, normalizer, and regex parsers.
- **T004** blocks **T005**; **T005** blocks **T006**; **T006** blocks **T007** — sequential T### ordering within the Stories phase carries the edge (two-step fetch order: catalog → model resolution → product page → row extraction).
- **T007** blocks **T008** — entry point must produce a contract-shaped dict before error paths wrap it.
- **T009** depends only on **T002** (fixture dir skeleton) and can run in parallel with the Stories phase.
- **T010** blocks on **T008** (error paths) and **T009** (fixtures) — golden + normalization tests need both the complete entry point and the captured fixtures.
- **T011** blocks **T012** — lint/seeder/coverage sweep runs after the full test suite is in place.
- **`[COMPLETES]` markers**: T005 ends the FR-004 chain (T003, T005); T007 ends the FR-003 / FR-006 chain (T003, T004, T006, T007); T008 ends the FR-009 chain (T008); T011 ends the FR-011 chain (T002, T009, T010, T011); T012 ends the FR-010 / FR-012 / FR-013 chain (T004, T006, T001, T008, T012).
- **Parallel safety**: T001, T002, T009 are marked `[P]`; none has an `after:T###` or `← T###:Symbol` that would create a same-batch violation (T009's `after:T002` is in a different phase from T002).
- **Cross-phase `after:T###` edges**: T004 (`after:T003`); T005 (`after:T004`); T006 (`after:T005`); T007 (`after:T006`); T008 (`after:T007`); T009 (`after:T002`); T010 (`after:T008,T009`); T011 (`after:T010`); T012 (`after:T011`) — these are explicit for resume and parallel-safety checks.
- The implementing agent MUST verify each `after:T###` reference resolves to a `[X]` task before executing the dependent task.

---

## Validation

- All 13 functional requirements (FR-001 through FR-013) covered by at least one task; FR-005 is covered by T003 + T006 (spans 2 tasks, no `[COMPLETES]` needed); FR-007 and FR-008 are single-task (T007); FR-010 spans T004 + T006 + T012 (3 tasks, `[COMPLETES]` on T012).
- All three user stories mapped: US1 (T004–T007), US2 (T005 structurally, T010 verified), US3 (T008, T011 verified).
- Every `→ exports:` annotation introduces a symbol defined in the named file; no `← T###:Symbol` consumers are used in this WBS (description-only cross-task edges via `after:T###`).
- Task line density matches the `specs/00026-official-viltrox-lenses-module/tasks.md` gold-standard shape (single long file path + `→ exports:` list dominates length); the `task-generation` overflow skill is absent from this repo, so no further folding is applied beyond matching the reference density.
- Empty optional phases omitted (no standalone Polish-only cross-cutting beyond Phase 4).
