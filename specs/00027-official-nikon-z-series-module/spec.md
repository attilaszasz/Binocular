---
feature_branch: "00027-official-nikon-z-series-module"
created: "2026-07-01"
input: "E026 Official Nikon Z-Series Module"
spec_type: "product"
spec_maturity: "draft"
epic_id: "E026"
epic_sources: "{PRD:CAP-011}{SAD:ADR-0005}"
---

# Feature Specification: Official Nikon Z-Series Module

**Feature Branch**: `00027-official-nikon-z-series-module`  
**Created**: 2026-07-01  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: draft  
**Epic ID**: E026  
**Epic Sources**: {PRD:CAP-011}{SAD:ADR-0005}  
**Product Document**: specs/prd.md

## Problem Statement

Nikon's Z Series mirrorless cameras (Z 30, Z 5, Z 50, Z 6, Z 6II, Z 7, Z 7II, Z 8, Z 9, Z f, Z fc, Z50II, Z5II, Z6III) are a popular, actively-updated body line whose firmware is published on the Nikon Download Center. Operators using these cameras have no native way to monitor firmware updates through Binocular: the application ships official starter modules for several other manufacturers (Sony Alpha, Panasonic Lumix MFT, Panasonic Lumix Lenses, Godox Flashes, Viltrox Lenses) under CAP-011, but Nikon Z-Series support is missing. Operators must hand-author a Nikon module against a two-step XML-catalog → per-product HTML flow, which fragments the value of an otherwise plug-and-play starter set and leaves a known manufacturer uncovered.

## Scope

### Included

- Automatic firmware-version detection for operators who configure a Nikon Z-Series camera device (e.g. `Z 30`).
- The new module plugs into the existing official starter set alongside the other shipped modules and is auto-registered on application startup.
- Support for the 14 Z Series products listed under `Mirrorless Cameras` / `Z Series` in the Nikon Download Center XML catalog.
- Reliable identification of the latest firmware release per configured body, surfaced through the existing detect → compare → notify loop.
- Model-key normalization across display-name (`Z 30`), no-space (`Z30`), URL-slug (`Z_30`), lowercase, and Roman-numeral (`Z 6II` / `Z6II` / `Z_6II` / `Z 6 II`) input forms.
- Class-agnostic version-prefix stripping (`C:Ver.` for cameras; the stripper tolerates any `<token>:Ver.` prefix so `A:Ver.`/`L:Ver.` do not break parsing if encountered).
- Explicit categorised failure surfacing — when the source structure changes, the configured model is not listed, or a body page exposes no firmware, the operator sees a visible "scrape failed" status with the failure category, never a silent miss.
- Integration with the existing official module health monitor so a repeatedly failing Nikon check surfaces in-app like other official modules.

### Excluded

- Auto-seeding the module into SQLite on startup — already covered by E016 (module seeder).
- Frontend UI for adding devices or managing modules — covered in E006 and E009.
- Non-Z-Series Nikon products (D-SLR, COOLPIX, accessories, lenses) — out of scope; the module filters to `Mirrorless Cameras` / `Z Series`.
- Localized download centers (e.g. `nikonimglib.com/jp/...`) — out of scope; the module targets the English catalog.
- Lens/accessory firmware prefixes (`A:Ver.`, `L:Ver.`) as a product surface — out of scope, but the version stripper is class-agnostic so such prefixes are stripped rather than crashing the parser.

### Edge Cases & Boundaries

- Catalog XML structure changes (categories renamed, `Z Series` subcategory absent, `<product>` elements missing `href`): return `firmware_index_not_found` rather than guess a product link.
- Per-product page lacks a `<div id="firmware">` section or the `pseudoTable` has no firmware rows (e.g. a body with no published firmware updates): return `firmware_not_available`.
- Per-product page exposes a valid first firmware row but the row has no `View download page` link: return `download_url_not_found`.
- Catalog XML fetch or per-product page fetch fails (network/HTTP error): return `network_error` with the failing URL.
- Configured model is not present in the `Z Series` subcategory (e.g. `Z 99`): return `product_not_found`.
- Version string carries a non-`C:` prefix (e.g. `A:Ver.2.00`): the class-agnostic stripper strips the `<token>:Ver.` prefix and returns the bare version.
- Date in a non-`YYYY/MM/DD` form: return `firmware_index_not_found` (structural breakage) rather than emit an unnormalized date.
- Model input with trailing/leading whitespace, alternate casing, or alternate spacing around Roman numerals: normalize and match via the alias-set intersection rule.

## User Scenarios & Testing

### User Story 1 - Detect Firmware Version (Priority: P1)

An operator wants Binocular to automatically detect when their Nikon `Z 30` camera has a newer firmware than the version they have installed.

**Why this priority**: Without this, the operator cannot use Binocular for Nikon Z-Series cameras — defeating the value of an official starter module. Core value proposition of E026.

**Independent Test**: Drive the module against a captured `product_data.xml` catalog fixture and a captured `Z_30.html` product-page fixture; assert `latest_version == "1.20"`, `release_date == "2025-05-07"`, and `download_url == "https://downloadcenter.nikonimglib.com/en/download/fw/556.html"` for model `Z 30`.

**Acceptance Scenarios**:

1. **Given** a captured `product_data.xml` listing `Z 30` under `Mirrorless Cameras` / `Z Series` with `href=/en/products/603/Z_30.html`, and a captured `Z_30.html` whose `#firmware` pseudoTable's first row is `C:Ver.1.20` dated `2025/05/07` linking to `/en/download/fw/556.html`, **When** `check_firmware` is called with model `Z 30`, **Then** the module returns `latest_version = "1.20"`, `release_date = "2025-05-07"`, `download_url = "https://downloadcenter.nikonimglib.com/en/download/fw/556.html"`, `product_name = "Nikon Z 30"`, `product_model = "Z 30"`, `product_type = "Camera"`.
2. **Given** the same fixtures, **When** `check_firmware` is called with model `Z30` (no space) or `Z_30` (URL slug form), **Then** the module normalizes the input, resolves to the same product, and returns the same `latest_version = "1.20"`.

### User Story 2 - Model-Key Normalization (Priority: P1)

An operator wants assurance that whichever form of the model name they configure (`Z 30`, `Z30`, `Z_30`, `z 30`, `z30`, `z_30`, or Roman-numeral variants `Z 6II`/`Z6II`/`Z_6II`/`Z 6 II`), Binocular resolves it to the same Z Series product.

**Why this priority**: Nikon's catalog uses display names with spaces while operators may paste the no-space or slug form; a normalization mismatch would silently miss a configured body. Critical for detection correctness.

**Independent Test**: Call `check_firmware` with each of the six `Z 30` forms against the captured fixtures; assert all return `latest_version = "1.20"` and the same `product_model`.

**Acceptance Scenarios**:

1. **Given** the captured catalog + `Z_30.html` fixtures, **When** `check_firmware` is called with each of `Z 30`, `Z30`, `Z_30`, `z 30`, `z30`, `z_30`, **Then** every call returns `latest_version = "1.20"` and `product_model = "Z 30"`.
2. **Given** a captured catalog fixture listing `Z 6II`, **When** `check_firmware` is called with each of `Z 6II`, `Z6II`, `Z_6II`, `Z 6 II`, **Then** every call resolves to the same product via alias-set intersection.

### User Story 3 - Handle Failures Honestly (Priority: P2)

An operator wants clear, diagnostic feedback when a firmware check fails because Nikon restructured the catalog, removed the `#firmware` section, did not list the configured model, or a network error occurred.

**Why this priority**: Supports the "honest failure" product principle — failures must be visible and categorizable, never silent. A silent miss is the most damaging failure for an unattended watcher.

**Independent Test**: Execute tests with fixtures representing a broken catalog, an unlisted model, a body page with no firmware rows, a firmware row with no download link, and a network-failure mock; assert each returns the correct standardized error code.

**Acceptance Scenarios**:

1. **Given** a captured `product_data.xml` with no `Z Series` subcategory under `Mirrorless Cameras`, **When** `check_firmware` is called for any model, **Then** the module raises `firmware_index_not_found`.
2. **Given** a valid catalog fixture but the per-product page fetch fails (mocked network error), **When** `check_firmware` is called, **Then** the module raises `network_error`.
3. **Given** a captured catalog fixture where the configured model `Z 99` is not in the `Z Series` subcategory, **When** `check_firmware` is called with `Z 99`, **Then** the module raises `product_not_found`.
4. **Given** a captured product-page fixture whose `#firmware` section has no firmware rows, **When** `check_firmware` is called for the corresponding model, **Then** the module raises `firmware_not_available`.
5. **Given** a captured product-page fixture whose first firmware row has a valid `C:Ver.` version but no `View download page` link, **When** `check_firmware` is called, **Then** the module raises `download_url_not_found`.

## Requirements

### Functional Requirements

- **FR-001**: System MUST define the official Nikon Z-Series module in `backend/src/binocular/official_modules/nikon_z_series.py`, implementing the V1 authoring contract.
- **FR-002**: System MUST declare `MODULE_VERSION` and `SUPPORTED_DEVICE_TYPE = "camera"` constants in the module.
- **FR-003**: System MUST fetch the Nikon Download Center catalog at `https://downloadcenter.nikonimglib.com/en/0/product_data.xml` via the host-provided ScrapeClient, parse it with stdlib `xml.etree.ElementTree`, select the `Mirrorless Cameras` main category, then the `Z Series` subcategory, and collect the 14 `<product>` entries with their `name` and relative `href` attributes.
- **FR-004**: System MUST resolve the configured model against the `Z Series` product list using alias-set intersection: for each catalog `<product name>` and for the input model, generate the alias set {display name, no-space form, slug form} (uppercased, with `_` and spaces removed for the normalized comparison key); match on set intersection. Covers `Z 30`/`Z30`/`Z_30`/`z 30`/`z30`/`z_30` and Roman-numeral variants `Z 6II`/`Z6II`/`Z_6II`/`Z 6 II`.
- **FR-005**: System MUST resolve the matched product's relative `href` against the download-center base URL `https://downloadcenter.nikonimglib.com`, fetch the product page via the host-provided ScrapeClient, and isolate the `<div id="firmware" class="contentsType">` → `<div class="pseudoTable">` firmware rows using regex (same idiom as `panasonic_lumix.py`'s `_ROW_RE`/`_CELL_RE`). No BeautifulSoup dependency.
- **FR-006**: System MUST parse the FIRST firmware row as the latest. The row's version cell carries a class-agnostic `<token>:Ver.<version>` prefix (`C:Ver.` for cameras; `A:Ver.`/`L:Ver.` for lenses/accessories). The stripper MUST strip any `<token>:Ver.` prefix and return the bare version as `latest_version`.
- **FR-007**: System MUST normalize the row's `YYYY/MM/DD` date to `YYYY-MM-DD` and return it as `release_date`.
- **FR-008**: System MUST resolve the row's relative `View download page` link against the download-center base URL and return the absolute URL as `download_url`.
- **FR-009**: System MUST return explicit, typed diagnostic errors on failure (`network_error`, `firmware_not_available`, `firmware_index_not_found`, `product_not_found`, `download_url_not_found`). The prefix `parse_error` is NOT used — structural breakage of the catalog or firmware table maps to `firmware_index_not_found` / `firmware_not_available` respectively, matching the Sony/Panasonic conventions.
- **FR-010**: System MUST NOT perform any direct outbound HTTP — all fetches (XML catalog AND product page) MUST go through the host-provided `http_client` (ScrapeClient). No `httpx`, `requests`, or `urllib` calls.
- **FR-011**: System MUST provide golden/fixture-based tests using a captured `product_data.xml` catalog and a captured `Z_30.html` product page, validating the golden case (`latest_version = "1.20"`, `release_date = "2025-05-07"`, `download_url = "https://downloadcenter.nikonimglib.com/en/download/fw/556.html"`), model normalization across all input forms, and zero false positives / zero false negatives.
- **FR-012**: System MUST pass the two-phase module validation (Phase 1 AST + Phase 2 runtime) and be auto-discoverable by the existing seeder (E016) on application startup.
- **FR-013**: System MUST pass `mypy --strict` and Ruff clean for the new module and its tests.

### Key Entities

- **Nikon Z-Series Module**: The Python script executing the firmware check, conforming to `MODULE_VERSION = "1.0.0"` and `SUPPORTED_DEVICE_TYPE = "camera"`. Implements `check_firmware(url, model, http_client) -> dict` returning `{latest_version, release_date, download_url, product_name, product_model, product_type}`.
- **`product_data.xml`**: The Nikon Download Center catalog at `https://downloadcenter.nikonimglib.com/en/0/product_data.xml`, a tree of `<category layer="main">` → `<category layer="sub">` → `<product name="..." href="..." rss="..."/>`.
- **Firmware pseudoTable row**: A `<div class="row">` inside `<div id="firmware" class="contentsType">` → `<div class="pseudoTable">` on a product page. Carries a `<strong class="col">` label, a `version` cell (`<token>:Ver.<version>`), a `date` cell (`YYYY/MM/DD`), and a `link` cell with the `View download page` anchor. The first row is the latest.

## Assumptions & Risks

### Assumptions

- Nikon continues to publish the catalog at `https://downloadcenter.nikonimglib.com/en/0/product_data.xml` with the `<category layer="main">` → `<category layer="sub">` → `<product>` tree, and the `Mirrorless Cameras` / `Z Series` subcategory names remain stable.
- Each Z Series product page contains a `<div id="firmware" class="contentsType">` section with a `<div class="pseudoTable">` whose first row is the latest firmware release in the `<token>:Ver.<version>` / `YYYY/MM/DD` / `View download page` shape.
- The ScrapeClient handles robots.txt, identifiable User-Agent, per-domain rate limiting, and exponential backoff (per project-instructions.md §II).
- The module's network use is bounded and modest: one XML catalog fetch + one product-page fetch per check, on a per-device schedule.

### Risks

- **Catalog structure change** *(likelihood: medium, impact: high)*: Nikon renames `Z Series`, restructures the category tree, or removes `href` attributes. Mitigation: module returns `firmware_index_not_found`; the activity log surfaces the failure; E020 escalates consistent failures to an in-app notification.
- **Firmware table layout change** *(likelihood: low, impact: medium)*: Nikon restructures the `#firmware` pseudoTable or drops the `pseudoTable` class. Mitigation: regex-based parser returns `firmware_not_available` rather than guessing; fixtures cover the current shape; failures bubble up rather than silent skips.
- **Body with no firmware updates** *(likelihood: low, impact: low)*: A Z Series body page exists but has no `#firmware` section or an empty pseudoTable. Mitigation: module returns `firmware_not_available` rather than guessing.
- **Responsible-scraping posture** *(mandatory)*: The module must use the host-provided ScrapeClient for both fetches and avoid high-frequency polling; the per-module default check interval applies.

## Implementation Signals

- `NEW-ENTITY` — Implementation of `backend/src/binocular/official_modules/nikon_z_series.py` as an official module.
- `EXTERNAL-SERVICE` — Outbound scraping of `https://downloadcenter.nikonimglib.com/en/0/product_data.xml` and per-product `/en/products/<id>/<slug>.html` pages via the host-provided ScrapeClient.
- `NEW-WORKER` — No new background worker; the module plugs into the existing scheduled-check infrastructure (E013) and seeder (E016) without new workers.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: An operator who configures a Nikon `Z 30` device sees `latest_version = "1.20"`, `release_date = "2025-05-07"`, and `download_url = "https://downloadcenter.nikonimglib.com/en/download/fw/556.html"` within one scheduled check.
- **SC-002** [US1]: Across all captured Z Series catalog + product-page fixture pairs in the regression suite, zero false positives and zero false negatives are reported.
- **SC-003** [US2]: For each supported Z Series body, every accepted input form (`Z 30`/`Z30`/`Z_30`/`z 30`/`z30`/`z_30` and Roman-numeral variants `Z 6II`/`Z6II`/`Z_6II`/`Z 6 II`) resolves to the same product and returns the same `latest_version`.
- **SC-004** [US3]: For any failure-mode fixture, the operator-visible status surfaces a categorised failure (not a silent miss) within one check cycle.
- **SC-005** [US1]: All outbound requests from the new module traverse the host HTTP client; no direct third-party HTTP library call appears in module source.
- **SC-006** [US1]: No new lint or type errors are introduced in the backend tree; the full backend test suite remains green; `mypy --strict` and Ruff are clean for the new module and its tests.

## Glossary

| Term | Definition |
|------|------------|
| Nikon Z-Series module | The new official `nikon_z_series` module shipped under `backend/src/binocular/official_modules/`. `SUPPORTED_DEVICE_TYPE = "camera"`; model key is the Z Series body display name (e.g. `Z 30`). |
| `product_data.xml` | The Nikon Download Center catalog at `https://downloadcenter.nikonimglib.com/en/0/product_data.xml`, a tree of `<category layer="main">` → `<category layer="sub">` → `<product name="..." href="..." rss="..."/>`. The module selects `Mirrorless Cameras` / `Z Series`. |
| Z Series subcategory | The `<category layer="sub">` named `Z Series` under the `Mirrorless Cameras` main category. Lists the 14 Z Series bodies: Z 30, Z 5, Z 50, Z 6, Z 6II, Z 7, Z 7II, Z 8, Z 9, Z f, Z fc, Z50II, Z5II, Z6III. |
| Firmware pseudoTable row | A `<div class="row">` inside `<div id="firmware" class="contentsType">` → `<div class="pseudoTable">` on a product page. Carries a `version` cell (`<token>:Ver.<version>`), a `date` cell (`YYYY/MM/DD`), and a `link` cell with the `View download page` anchor. The first row is the latest. |
| `C:Ver.` prefix | Nikon's device-class version prefix for cameras (`C:` = camera). The stripper is class-agnostic: it strips any `<token>:Ver.` prefix (so `A:Ver.`/`L:Ver.` lens/accessory prefixes are also stripped if encountered) and returns the bare version. |
| Model-key normalization | The resolution rule: uppercase the input, strip `Z`-prefix whitespace variants, remove `_` and spaces, then compare against the same normalized forms generated from each catalog `<product name>`. Match on alias-set intersection (display name, no-space form, slug form) — mirroring `panasonic_lumix.py` / `sony_alpha.py`. Covers `Z 30`/`Z30`/`Z_30`/`z 30`/`z30`/`z_30` and Roman-numeral variants. |
| Authoring contract | The strict, documented interface (per ADR-0005) every module must implement: `check_firmware(url, model, http_client) -> dict`, plus `MODULE_VERSION` and `SUPPORTED_DEVICE_TYPE` constants. The host-provided `http_client` parameter is the `ScrapeClient` (polite-by-default); the parameter name and the class name are interchangeable. |

## Compliance Check

- **Policy Auditor verdict**: PASS. Spec is compliant with all MUST/SHOULD principles in `project-instructions.md`: ENFORCE_SRC_ROOT path correct (`backend/src/binocular/official_modules/`), ScrapeClient-only HTTP enforced (FR-010, SC-005) for BOTH the XML catalog fetch and the product-page fetch, explicit typed failure errors align with Honest Failure (FR-009, US3) using the five standardized prefixes (no `parse_error`), fixture-based zero-FP/FN tests satisfy §V correctness clause (FR-011), `mypy --strict` + Ruff required (FR-013, SC-006), no new worker/DB/external dependency introduced (stdlib `xml.etree.ElementTree` + regex, no BeautifulSoup), and modules are not claimed to be sandboxed. One LOW finding: spec body slightly exceeds the 10 KB soft size cap (rich failure-mode coverage and model-normalization detail justify the density; downstream phases should be aware).
