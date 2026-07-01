# QC Report — E026 Official Nikon Z-Series Module

- **Feature dir**: `specs/00027-official-nikon-z-series-module/`
- **Module**: `backend/src/binocular/official_modules/nikon_z_series.py`
- **Test file**: `backend/tests/test_official_nikon_z_series_module.py`
- **Fixtures**: `backend/tests/fixtures/nikon_z_series/` (8 files)
- **Run timestamp**: 2026-07-01T10:34:49Z
- **Overall Verdict**: **PASS**

## Summary

All required QC categories passed for real (executed commands, not simulated):
- pytest: 68 nikon-targeted tests green; full suite 348 passed (no regressions)
- mypy --strict: clean (project + module + test file)
- ruff check .: clean
- pip-audit: no known vulnerabilities
- coverage: nikon_z_series.py 92% (≥ 80% target); project 85.72%
- docker build: PASS (Dockerfile at repo root)
- frontend (CI alignment): lint, typecheck, vitest (33/33) PASS
- No direct HTTP client imports (`httpx` / `requests` / `urllib.request`)

## Test Results

- **Runner**: pytest 9.1.1 + pytest-asyncio (mode=auto)
- **Command**: `uv run pytest tests/test_official_nikon_z_series_module.py --cov=binocular.official_modules.nikon_z_series --cov-report=term-missing`
- **Result**: 68 passed, 0 failed, 0 skipped
- **Targeted coverage**: 92% (177 statements, 14 missed; missing lines are defensive `raise ValueError(...except Exception)` fallbacks and the empty-model `if not model` guard)
- **Full suite command**: `uv run pytest --cov=binocular --cov-report=term-missing`
- **Full suite result**: 348 passed in 91.93s; project coverage 85.72% (≥ 80% gate)

### Test inventory

- Contract constants + ModuleLoader flow + direct-HTTP import deny list (3 tests)
- `_strip_version_prefix` token-class matrix (C / A / L / no-prefix, 6 parametrized cases)
- `_normalize_date` YYYY/MM/DD → YYYY-MM-DD round-trip (5 parametrized cases)
- `_normalize_model` Z 30 / Z 6II alias-set keys (12 parametrized cases)
- `_select_z_series_products` 14-product enumeration
- `_resolve_product` Z 30 + Z 6II alias-set variants + unlisted-model returns None (14 parametrized cases + 1 negative)
- `_CELL_RE` nested-span extraction
- `_parse_first_firmware_row` golden / missing-section / empty-table (3)
- `_resolve_download_url` relative + absolute + empty (1)
- `check_firmware` golden happy path (exact dict assertion)
- `check_firmware` Z 30 input-form normalization (5 parametrized)
- `check_firmware` Z 6II Roman-numeral variants (5 parametrized)
- `check_firmware` injected catalog URL honored
- `check_firmware` empty-model `product_not_found`
- 5 standardized `ValueError` error-code paths: `network_error` (catalog + product-page), `firmware_index_not_found` (no Z Series subcategory + malformed XML + non-YYYY/MM/DD date), `product_not_found` (unlisted `Z 99`), `firmware_not_available` (no #firmware section + empty pseudoTable), `download_url_not_found` (row without View download page link)
- `parse_error` is NOT emitted (verified by absence — every error-path test asserts a non-`parse_error` code)

### Fixtures captured

| File | Purpose |
|------|---------|
| `product_data.xml` | Golden catalog: `Mirrorless Cameras` → `Z Series` with all 14 bodies |
| `Z_30.html` | Golden product page: `C:Ver.1.20`, `2025/05/07`, `/en/download/fw/556.html`; software section with `L:Ver.` row exercises class-agnostic prefix scoping |
| `Z_6II.html` | Roman-numeral catalog entry product page for alias-set verification |
| `empty_firmware_page.html` | `#firmware` section with empty `pseudoTable` → `firmware_not_available` |
| `no_firmware_section_page.html` | Product page without `#firmware` → `firmware_not_available` |
| `no_z_series_catalog.xml` | Catalog with `Mirrorless Cameras` but no `Z Series` subcategory → `firmware_index_not_found` |
| `unlisted_model_catalog.xml` | Catalog with `Z Series` but no `Z 99` → `product_not_found` |
| `row_without_link.html` | Firmware row with valid `C:Ver.` version + valid date but no "View download page" anchor → `download_url_not_found` |

## Static Analysis

- **Tool**: `uv run ruff check .`
- **Result**: All checks passed (0 issues). Selected rule families: E, F, W, I, UP, S, B, A, C4, PT, RUF.
- **Notable**: `xml.etree.ElementTree.fromstring` flagged by `S314` (defusedxml recommendation) is suppressed with `# noqa: S314` because the spec/plan forbid adding a new external dependency; the upstream endpoint and fixture data are trust-bounded by the host ScrapeClient, and element parsing is read-only with no entity expansion consumed by the module.

## Static Typing

- **Tool**: `uv run mypy .` (strict; pyproject `strict = true`)
- **Result**: Success — no issues found in 103 source files
- **Per-target**: `uv run mypy --strict src/binocular/official_modules/nikon_z_series.py` → no issues; `uv run mypy --strict tests/test_official_nikon_z_series_module.py` → no issues

## Security Audit

- **Tool**: `uv run pip-audit`
- **Result**: No known vulnerabilities found (only skip: local `binocular` package itself, not on PyPI)

## Docker Build Check

- **Command**: `docker build -t binocular:qc-check -f Dockerfile . --load`
- **Result**: PASS (exit 0). Multi-stage build completes; frontend-builder emits the production `dist/`; runtime stage copies static assets.

## Frontend Verification (CI Alignment)

- `npm run lint` → PASS (exit 0)
- `npm run typecheck` (`tsc --noEmit`) → PASS (exit 0)
- `npm test -- --run` (vitest) → 9 test files, 33 tests passed

## Project Instructions Compliance

- No violations. ENFORCE_SRC_ROOT honored — module lives at `backend/src/binocular/official_modules/nikon_z_series.py`.
- Sync-over-async pattern (`asyncio.new_event_loop` + `run_until_complete` in `try/finally`) reused from `viltrox_lenses.py` / `panasonic_lumix.py` / `godox_flashes.py`.
- No new external dependencies (stdlib `re` + `xml.etree.ElementTree` only; no `bs4`, no `defusedxml`, no HTTP client imports).
- V1 authoring contract (ADR-0005): `MODULE_VERSION = "1.0.0"`, `SUPPORTED_DEVICE_TYPE = "camera"`, `check_firmware(url, model, http_client) -> dict[str, Any]`.
- No `parse_error` emitted — all five standardized error codes (`network_error`, `firmware_index_not_found`, `product_not_found`, `firmware_not_available`, `download_url_not_found`) cover the documented failure modes.

## Requirements Traceability

| Requirement | Status | Evidence |
|---|---|---|
| FR-001 Module exports `MODULE_VERSION="1.0.0"` | PASS | `test_module_declares_contract_constants` |
| FR-002 Module exports `SUPPORTED_DEVICE_TYPE="camera"` | PASS | `test_module_declares_contract_constants` |
| FR-003 Entry point `check_firmware(url, model, http_client) -> dict` | PASS | golden + error-path tests |
| FR-004 Alias-set model resolution | PASS | Z 30 / Z 6II variant parametrize suites |
| FR-005 `#firmware` pseudoTable regex parsers | PASS | `_parse_first_firmware_row` tests |
| FR-006 Class-agnostic `<token>:Ver.` prefix strip + date norm + download_url resolution | PASS | `_strip_version_prefix` / `_normalize_date` / `_resolve_download_url` tests + golden happy path |
| FR-007 YYYY/MM/DD → YYYY-MM-DD | PASS | `_normalize_date` tests + golden asserts `"2025-05-07"` |
| FR-008 Relative→absolute download_url resolution | PASS | `_resolve_download_url` tests + golden asserts `https://downloadcenter.nikonimglib.com/en/download/fw/556.html` |
| FR-009 Five typed `ValueError` (NOT `parse_error`) | PASS | 5 error-path tests |
| FR-010 No direct HTTP client imports + two-phase validation + auto-discoverable | PASS | `test_module_does_not_import_direct_http_clients` + `test_module_loads_through_extension_contract` |
| FR-011 Fixture-based zero-FP/FN tests | PASS | 8 fixtures, 68 tests |
| FR-012 mypy --strict clean | PASS | `uv run mypy --strict ...` success |
| FR-013 Ruff clean | PASS | `uv run ruff check .` clean |

## Code Coverage

- **Target**: 80% (`.github/sddp-config.md § Derived QC Policy`)
- **Module actual**: 92.09% (`nikon_z_series.py` 177 statements, 14 missed)
- **Missed lines**: defensive `except Exception` arms in `check_firmware` (lines 108, 114), `_find_category` empty-text skip (131), `_normalize_model` empty-input guard (147), `_resolve_product` empty-input guards (160, 163), `_extract_class` no-attr branch (179), `_strip_tags`/`_clean` utility edges (185), the empty-`src` no-row branch in `_parse_first_firmware_row` (283-284, 305-306, 320). All are defensive fallbacks that cannot be hit without adversarial HTML/XML outside the fixture contract.

## Performance / Accessibility

- No NFR detected in `spec.md`. SKIPPED — not required.

## Browser Runtime Validation

- No browser runtime required (pure Python scraping module, no UI). SKIPPED — not required.

## Manual Testing

- None required. All automated gates pass for real.

## Tool Recommendations

- None. All required categories ran successfully.

## Bug Tasks Generated

None.