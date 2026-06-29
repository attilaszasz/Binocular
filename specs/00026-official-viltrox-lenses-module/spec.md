---
feature_branch: "00026-official-viltrox-lenses-module"
created: "2026-06-29"
input: "E025 Official Viltrox Lenses Module"
spec_type: "product"
spec_maturity: "draft"
epic_id: "E025"
epic_sources: "{PRD:CAP-011}{SAD:ADR-0005}"
---

# Feature Specification: Official Viltrox Lenses Module

**Feature Branch**: `00026-official-viltrox-lenses-module`  
**Created**: 2026-06-29  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: draft  
**Epic ID**: E025  
**Epic Sources**: {PRD:CAP-011}{SAD:ADR-0005}  
**Product Document**: specs/prd.md

## Problem Statement

Viltrox is a popular third-party lens manufacturer covering multiple camera mounts (FE / E / X / Z / M / DL). Operators using Viltrox lenses currently have no native way to monitor firmware updates through Binocular: the application ships official starter modules for several other manufacturers (Sony Alpha, Panasonic Lumix MFT, Panasonic Lumix Lenses, Godox Flashes) under CAP-011, but Viltrox support is missing. Operators must hand-author a Viltrox module against a custom flow (a Shopify-hosted index page with side-menu links plus per-lens download sections), which fragments the value of an otherwise plug-and-play starter set and leaves a known manufacturer uncovered by the official starter set.

## Scope

### Included

- Automatic firmware-version detection for operators who configure a Viltrox lens device (e.g. `TC-2.0X FE`) in their inventory.
- The new module plugs into the existing official starter set alongside the four other shipped modules (Sony Alpha, Panasonic Lumix MFT, Panasonic Lumix Lenses, Godox Flashes) and is auto-registered on application startup.
- Support for ~70 Viltrox lenses across 6 mount groups (FE / E / X / Z / M / DL) — the full set listed on the Viltrox download-center index page.
- Reliable identification of the latest firmware release per configured lens, surfaced to the operator through the existing detect → compare → notify loop.
- Explicit categorised failure surfacing — when the source page changes, the configured lens is not listed, or the lens page exposes no firmware, the operator sees a visible "scrape failed" status with the failure category, never a silent miss.
- The companion app version (`Viltrox Lens V1.13 for Mac/Win`) is structurally excluded from the lens-firmware version the operator sees.
- Consistent integration with the existing official module health monitor so that a repeatedly failing Viltrox check surfaces in-app like other official modules.

### Excluded

- Auto-seeding the module into the SQLite database on startup — already covered by E016 (module seeder) which auto-discovers any file in `official_modules/`.
- Frontend UI for adding devices or managing modules — covered in E006 and E009.
- The companion app version section / any non-`### Document Download` content on lens pages — out of scope; explicitly excluded.
- Localized index pages (e.g. `viltrox.com/cn/pages/...`) — out of scope; the module targets the public English index at `https://viltrox.com/pages/download-center-1`.

### Edge Cases & Boundaries

- Index page structure changes (sidebar replaced by JS widget, model names localized, side-menu absent): the module must return `parse_error` rather than guess the lens link.
- Per-lens page lacks a `### Document Download` section: the module must return `parse_error` (not silently return an empty version).
- Per-lens page exposes a valid first entry but no download link for it: the module must return `download_url_not_found` and use the lens page URL as a fallback only when the lens page itself is the canonical source.
- Index page lists a lens but the per-lens page fails to load: the module must return `network_error` with the failing URL.
- Lens page has an empty or "TBD" version string at the top of the section: the module must return `firmware_not_available` rather than guess.
- Companion app version string (e.g. `Viltrox Lens V1.13 for Mac/Win`) appears anywhere on a lens page or on the index: it must never reach `latest_version`.
- Model name with trailing/leading whitespace or alternate casing (e.g. `tc-2.0x fe`): the module must normalize and match.

## User Scenarios & Testing

### User Story 1 - Detect Firmware Version (Priority: P1)

An operator wants Binocular to automatically detect when their Viltrox `TC-2.0X FE` lens has a newer firmware than the version they have installed.

**Why this priority**: Without this, the operator cannot use Binocular for Viltrox lenses — defeating the value of an official starter module. Core value proposition of E025.

**Independent Test**: Run a test that drives the module against captured Viltrox index and lens page fixtures and asserts `latest_version == "1.03"` for `TC-2.0X FE`, with a populated `release_date` and `download_url`.

**Acceptance Scenarios**:

1. **Given** a captured index page fixture listing `TC-2.0X FE` as a side-menu link to `/pages/tc-2-0x-fe` and a captured lens page fixture whose `### Document Download` section's first entry is `TC-2.0X FE V1.03 (2025-04-12)`, **When** `check_firmware` is called with model `TC-2.0X FE`, **Then** the module returns `latest_version = "1.03"`, `release_date = "2025-04-12"`, a `download_url` pointing to the lens page's download link, `product_name = "Viltrox TC-2.0X FE"`, and `product_type = "Lens"`.
2. **Given** the same fixtures, **When** `check_firmware` is called with model `tc-2.0x fe` (lowercased, with the page slug as fallback), **Then** the module normalizes the input, resolves to the same lens, and returns the same `latest_version = "1.03"`.

### User Story 2 - Reject Companion App Version (Priority: P1)

An operator wants assurance that the desktop companion app version (e.g. `Viltrox Lens V1.13 for Mac/Win`) is never mistaken for a lens firmware version.

**Why this priority**: A false positive where the desktop app version is reported as a lens firmware version would corrupt the user's stored version, trigger false alerts, and erode set-and-forget trust. Critical for detection correctness.

**Independent Test**: Run a test with a captured lens page that includes a "Viltrox Lens V1.13 for Mac/Win" section above or alongside the `### Document Download` section, and assert `latest_version` does not contain `1.13` (or any companion-app version) and that the desktop app section is never parsed.

**Acceptance Scenarios**:

1. **Given** a captured lens page whose `### Document Download` section's first entry is `TC-2.0X FE V1.03` and which also contains a `Viltrox Lens V1.13 for Mac/Win` block elsewhere on the page, **When** `check_firmware` is called with model `TC-2.0X FE`, **Then** the module returns `latest_version = "1.03"` (the lens firmware), not `1.13` (the companion app).
2. **Given** a captured index page that references the companion app version in a sidebar banner, **When** the module walks the index for any model, **Then** the companion app version string is never propagated into the `latest_version` field of any returned firmware entry.

### User Story 3 - Handle Parse Failures (Priority: P2)

An operator wants clear, diagnostic feedback when a firmware check fails because Viltrox restructured their pages, removed the `### Document Download` section, or did not list the configured model.

**Why this priority**: Supports the "honest failure" product principle — failures must be visible and categorizable, never silent. A silent miss is the most damaging possible failure for an unattended watcher.

**Independent Test**: Execute tests with fixtures representing an unparseable index, an unlisted model, an empty version string, and a missing `### Document Download` section; assert the module returns a failure with the correct error code.

**Acceptance Scenarios**:

1. **Given** a captured index page with no side-menu links to per-lens pages, **When** `check_firmware` is called for any model, **Then** the module raises a `parse_error`.
2. **Given** a valid index page fixture and a captured lens page fixture that lacks a `### Document Download` section, **When** `check_firmware` is called with the corresponding model, **Then** the module raises a `parse_error`.
3. **Given** a captured index page fixture where the configured model `XX-999 Z` is not in the side menu, **When** `check_firmware` is called with model `XX-999 Z`, **Then** the module raises `product_not_found`.
4. **Given** a captured lens page fixture whose `### Document Download` first entry has an empty version, **When** `check_firmware` is called for the corresponding model, **Then** the module raises `firmware_not_available`.
5. **Given** a captured lens page fixture whose `### Document Download` first entry has a valid version but the page exposes no download link for that entry, **When** `check_firmware` is called for the corresponding model, **Then** the module raises `download_url_not_found` and falls back to the lens page URL only when the page itself is the canonical source.

## Requirements

### Functional Requirements

- **FR-001**: System MUST define the official Viltrox Lenses module in a file named `viltrox_lenses.py` under `backend/src/binocular/official_modules/`, implementing the V1 authoring contract.
- **FR-002**: System MUST declare `MODULE_VERSION` and `SUPPORTED_DEVICE_TYPE = "lens"` constants in the module.
- **FR-003**: System MUST fetch the Viltrox download-center index page at `https://viltrox.com/pages/download-center-1` via the host-provided ScrapeClient, locate the configured model's `/pages/<slug>` link in the side menu, and follow that link to the per-lens page.
- **FR-004**: System MUST parse the `### Document Download` section on the per-lens page and return the top entry's `<lens name> V<version>` as `latest_version`, with the leading `V` stripped.
- **FR-005**: System MUST accept the lens display name (e.g. `TC-2.0X FE`) as the primary model key, with the page slug (e.g. `tc-2-0x-fe`) as a fallback when the display name does not match an index entry directly.
- **FR-006**: System MUST NEVER return a companion app version (e.g. `Viltrox Lens V1.13 for Mac/Win`) as a lens `latest_version`, even if it appears on the index or the lens page.
- **FR-007**: System MUST return explicit, typed diagnostic errors on failure (`network_error`, `parse_error`, `product_not_found`, `firmware_not_available`, `download_url_not_found`).
- **FR-008**: System MUST provide golden/fixture-based tests using captured HTML for at least one Viltrox index page and at least one per-lens page, validating parsing correctness, companion app rejection, and zero false positives / zero false negatives.
- **FR-009**: System MUST pass the two-phase module validation (Phase 1 AST + Phase 2 runtime) and be auto-discoverable by the existing seeder (E016) on application startup.
- **FR-010**: System MUST NOT perform any direct outbound HTTP — all fetches MUST go through the host-provided `http_client` (ScrapeClient).

### Key Entities

- **Viltrox Lenses Module**: The Python script executing the firmware check, conforming to `MODULE_VERSION = "1.0.0"` and `SUPPORTED_DEVICE_TYPE = "lens"`. Implements `check_firmware(url, model, http_client) -> dict` returning `{latest_version, release_date, download_url, product_name, product_model, product_type}`.
- **Viltrox Index Page Entry**: A single side-menu link on `https://viltrox.com/pages/download-center-1` mapping a lens display name to a `/pages/<slug>` URL.
- **Viltrox Lens Page `### Document Download` Entry**: A single firmware release line in the form `<lens name> V<version>`, optionally followed by a release date and notes. The first entry is the latest.

## Assumptions & Risks

### Assumptions

- Viltrox continues to host the index page at `https://viltrox.com/pages/download-center-1` with the lenses listed in a side menu as `/pages/<slug>` links.
- Each per-lens page contains a `### Document Download` section whose first entry is the latest firmware release in the form `<lens name> V<version>`.
- The companion app section is clearly distinguishable from per-lens firmware sections and is not labeled `### Document Download`.
- The ScrapeClient handles robots.txt, identifiable User-Agent, per-domain rate limiting, and exponential backoff (per project-instructions.md §II).
- The module's network use is bounded and modest: one index fetch + one lens page fetch per check, on a per-device schedule.

### Risks

- **Page structure change** *(likelihood: medium, impact: high)*: Viltrox redesigns the index page (sidebar replaced by JS widget, model names localized, side menu removed). Mitigation: module returns `parse_error`; the activity log surfaces the failure; E020 (Official Module Health Monitoring) escalates consistent failures to an in-app notification.
- **Inconsistent `V<version>` format** *(likelihood: low, impact: medium)*: Some lens page entries omit the leading `V` or use a different separator (e.g. parentheses, dash). Mitigation: version normalization step tolerates `V1.03` and `1.03`; fixtures cover both forms; failures bubble up as `parse_error` rather than silent skips.
- **Lens page with no active firmware** *(likelihood: low, impact: low)*: A lens appears in the side menu but its `### Document Download` section is empty (e.g. legacy model without firmware updates). Mitigation: module returns `firmware_not_available` rather than guessing; the operator sees a clear "scrape failed" status.

## Implementation Signals

- `NEW-ENTITY` — Implementation of `backend/src/binocular/official_modules/viltrox_lenses.py` as an official module.
- `EXTERNAL-SERVICE` — Outbound scraping of `https://viltrox.com/pages/download-center-1` and per-lens `/pages/<slug>` pages via the host-provided ScrapeClient.
- `NEW-WORKER` — No new background worker; the module plugs into the existing scheduled-check infrastructure (E013) and seeder (E016) without new workers.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: An operator who configures a Viltrox `TC-2.0X FE` device sees a populated `latest_version`, `release_date`, and `download_url` within one scheduled check.
- **SC-002** [US1]: Across all captured Viltrox lens pages in the regression suite, zero false positives and zero false negatives are reported.
- **SC-003** [US2]: No lens firmware record is ever set to the companion-app version string for any configured Viltrox device.
- **SC-004** [US3]: For any failure-mode fixture, the operator-visible status surfaces a categorised failure (not a silent miss) within one check cycle.
- **SC-005** [US1]: All outbound requests from the new module traverse the host HTTP client; no direct third-party HTTP library call appears in module source.
- **SC-006** [US1]: No new lint or type errors are introduced in the backend tree; the full backend test suite remains green.

## Glossary

| Term | Definition |
|------|------------|
| Viltrox Lenses module | The new official `viltrox_lenses` module shipped under `backend/src/binocular/official_modules/`. Its `SUPPORTED_DEVICE_TYPE` is `lens` and its model key is the lens display name (e.g. `TC-2.0X FE`). |
| Index page | `https://viltrox.com/pages/download-center-1` — the Viltrox download-center landing page that lists ~70 lenses across 6 mount groups (FE / E / X / Z / M / DL), each linked to its own `/pages/<slug>` page. |
| Lens page | A per-lens `/pages/<slug>` page on Viltrox's Shopify-hosted site that contains a `### Document Download` section listing firmware releases. |
| `### Document Download` section | A Markdown section on a lens page whose entries follow the pattern `<lens name> V<version>` (e.g. `TC-2.0X FE V1.03`). The first entry is treated as the latest. |
| Top entry | The first firmware entry inside the `### Document Download` section, used as the latest version. |
| Lens display name | The human-readable lens identifier as it appears on the index (e.g. `TC-2.0X FE`). Used as the primary `model` value when configuring a Viltrox device. |
| Page slug | The URL slug portion of a per-lens page URL (e.g. `tc-2-0x-fe`). Used as a fallback when the lens display name does not match an index entry directly. |
| Companion app version | The `Viltrox Lens V1.13 for Mac/Win` desktop application version, which is not a lens firmware version and must be excluded from parsing. |
| Authoring contract | The strict, documented interface (per ADR-0005) every module must implement: `check_firmware(url, model, http_client) -> dict`, plus `MODULE_VERSION` and `SUPPORTED_DEVICE_TYPE` constants. The host-provided `http_client` parameter is the `ScrapeClient` (polite-by-default); the parameter name and the class name are interchangeable in the contract. |

## Compliance Check

- **Policy Auditor verdict**: PASS. Spec is compliant with all MUST/SHOULD principles in `project-instructions.md`: ENFORCE_SRC_ROOT path correct (`backend/src/binocular/official_modules/`), ScrapeClient-only HTTP enforced (FR-010, SC-005), explicit typed failure errors align with Honest Failure (FR-007, US3), fixture-based zero-FP/FN tests satisfy §V correctness clause, `mypy --strict` + Ruff required (SC-006), no new worker/DB/external dependency introduced, and modules are not claimed to be sandboxed. One LOW finding: spec body slightly exceeds the 10 KB soft size cap (rich failure-mode coverage justifies the density; downstream phases should be aware).
