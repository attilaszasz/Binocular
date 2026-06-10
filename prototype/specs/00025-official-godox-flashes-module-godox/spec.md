---
feature_branch: "00025-official-godox-flashes-module-godox"
created: "2026-06-07"
input: "E024 Official Godox Flashes Module — Godox Flashes detection from https://www.godox.com/firmware-flash/ with pagination-aware parsing and fixtures"
spec_type: "product"
spec_maturity: "clarified"
epic_id: "E024"
epic_sources: "{PRD:CAP-011}"
---

# Feature Specification: Official Godox Flashes Module

**Feature Branch**: `00025-official-godox-flashes-module-godox`  
**Created**: 2026-06-07  
**Status**: Clarified  
**Spec Type**: product  
**Spec Maturity**: clarified  
**Epic ID**: E024  
**Epic Sources**: {PRD:CAP-011}  
**Product Document**: specs/prd.md

## Problem Statement

Owners of Godox flash equipment — ranging from camera-brand-specific speedlights (V100S for Sony, V860IIIC for Canon) to cross-brand studio strobes (AD200Pro, AD300Pro) — have no automated way to track firmware updates. Godox publishes firmware on a paginated listing at `godox.com/firmware-flash/` with five entries per page in reverse chronological order. The listing lacks a model-specific search or filter, so locating a particular device requires stepping through pages manually. Binocular currently ships no official module for Godox, forcing flash owners to trawl this paginated listing by hand, risking missed updates that degrade flash exposure consistency, TTL accuracy, and wireless triggering reliability.

## Scope

### Included

- A new official extension module `official.godox_flashes` implementing the Binocular authoring contract
- Multi-page traversal of the Godox flash firmware listing at `https://www.godox.com/firmware-flash/`, following URL-based pagination (`/firmware-flash_N/`)
- Extraction of the firmware version, model name, release date, and firmware page URL from each entry's HTML structure (`.item .tit span` for version, `.text` for metadata)
- Exact, case-insensitive, alphanumeric-normalized model matching against page titles — including camera-brand suffix variants (e.g., V100S vs V100C). Normalization strips all non-alphanumeric characters and uppercases both the page title and user input before comparison, consistent with existing module conventions.
- Early termination: stop page traversal and return the result immediately when the requested model is found on any page
- Fixture-based golden tests validating detection correctness against captured page snapshots, including multi-page scenarios
- A `MODULE_METADATA` descriptor with `module_id: "official.godox_flashes"`, `display_name: "Godox Flashes"`, author, version, and `supported_device_hints` including "Godox", "Flash"
- Auto-discovery and seeding by the existing startup seeder (E021)

### Excluded

- Search-box-based lookup via the global site search — the `/support/search/` endpoint is a general site search, not a firmware-specific filter, and cannot be relied upon for flash-only results
- Non-flash Godox products (LED lights, triggers, microphones) listed on other firmware sections
- Camera-brand variant disambiguation beyond exact match — the user must provide the full model identifier including suffix (e.g., "V100S"), and the module will not guess or fall back to a base-model match
- In-page JavaScript execution or DOM rendering — the page is server-rendered HTML; no browser automation is needed

### Edge Cases & Boundaries

- Model not found after exhausting all paginated pages → returns `product_not_found` failure with diagnostics indicating total pages checked
- Page structure changes and no firmware entries parse from page 1 → returns `parse_error` failure (distinct from `product_not_found`); the module must never silently return no result when zero entries parse
- Hard page limit reached (30 pages) before model found → returns `page_limit_exceeded` failure with diagnostics including the last page number reached
- Consecutive empty pages encountered (2 in a row) → treat as end of pagination, return `product_not_found` for any still-missing model, with `diagnostics.pages_checked` reflecting the number of pages actually fetched (not the total traversable page count)
- Solo empty page at N>1 not part of a consecutive pair → treated as a transient gap: log warning in diagnostics, reset empty counter to 0, continue traversal; reserve `parse_error` exclusively for page 1 with zero entries
- Version format variations: the page uses `V1.17`, `V1.02`, `V1.3`, `v2.6` (lowercase), `V2.2`, and `V1.0`; the module must normalize by stripping leading V/v and preserve the exact dotted format for the host's version comparison
- Camera-brand suffix matching: "V100S" must not match "V100C" — the module requires exact match of the full model string as it appears in the page title
- `check_input.model` is empty, None, or whitespace-only → treated as model-not-found, returns `product_not_found` without error
- `check_input.current_version` is empty or non-parseable → detection still succeeds (returns `latest_version`), but version comparison is skipped
- HTTP error, timeout, or scrape failure from any page → returns `firmware_page_unavailable` failure with `diagnostics` containing `{"http_status": int, "url": str}`
- Module must route all outbound HTTP through the host-provided scraping client — no direct HTTP library imports
- Pagination next-link becomes inert (`javascript:;`) on the last page → this is the primary termination signal

## User Scenarios & Testing

### User Story 1 - Flash Firmware Version Detection (Priority: P1)

An operator with a Godox flash (e.g., iT32 or V100S for Sony) links the device to the Godox Flashes module. When a check runs, the module fetches the firmware listing, traverses pages as needed, locates the matching flash model, and returns the latest published firmware version.

**Why this priority**: Core value — without version detection from the Godox firmware page, the module provides no utility. P1 alone yields a viable module.

**Independent Test**: Run the module with model "iT32" against a captured multi-page fixture; verify `latest_version` is "1.17", `status` is "success", and `diagnostics` includes the page number where the match was found.

**Acceptance Scenarios**:

1. **Given** the Godox firmware listing fixture with iT32 appearing on page 1 at V1.17, **When** the module checks firmware for model "iT32", **Then** the result returns `latest_version: "1.17"` and `status: "success"` with `diagnostics: {"matched_page": 1}`.
2. **Given** the Godox firmware listing fixture with V100S appearing on page 3 at V1.06, **When** the module checks firmware for model "V100S", **Then** the result returns `latest_version: "1.06"` and `status: "success"` with `diagnostics: {"matched_page": 3, "pages_checked": 3}`.
3. **Given** a fixture where model "V100" (no suffix) is requested, **When** the module checks firmware, **Then** the result returns `status: "failed"` with `error_type: "product_not_found"` — an unsuffixed model must not match any variant (V100C, V100N, V100S).

### User Story 2 - Multi-Page Traversal & Honest Failure (Priority: P2)

The module correctly traverses the paginated firmware listing, stopping early when the model is found, and surfaces visible failures with diagnostic context when the model is absent, the page structure changes, or a network error occurs.

**Why this priority**: Pagination traversal is essential because models appear on arbitrary pages (not only page 1). Honest failure is a core Binocular principle — without it, a missed update could go silently undetected. P2 because the module's primary value is detection (P1); failure signaling is a safeguard.

**Independent Test**: Run the module against a fixture where the model appears on page 3; verify the module fetches pages 1, 2, and 3, returns the correct version, and stops without fetching page 4.

**Acceptance Scenarios**:

1. **Given** a multi-page fixture where the last page's next-link is `javascript:;`, **When** the module searches for a non-existent model, **Then** the module fetches all pages, stops at the inert next-link, and returns `status: "failed"` with `error_type: "product_not_found"` and `diagnostics: {"pages_checked": N}`.
2. **Given** a fixture where page 1 has zero parseable firmware entries (page structure changed), **When** the module checks firmware, **Then** the result returns `status: "failed"` with `error_type: "parse_error"` — not `product_not_found` — and a descriptive `detail` message.
3. **Given** a FakeScrapeClient that raises a ScrapeTransportError on the first page request, **When** the module checks firmware, **Then** the result returns `status: "failed"` with `error_type: "firmware_page_unavailable"` and `diagnostics` containing the HTTP status code and attempted URL.
4. **Given** a fixture with model V1C on page 1 but the requested model is "V1C" with a different case (e.g., "v1c"), **When** the module checks firmware, **Then** the result returns `status: "success"` — model matching is case-insensitive.
5. **Given** a multi-page fixture where the model is not present and the module reaches page 30 (hard limit), **When** the module checks firmware, **Then** the result returns `status: "failed"` with `error_type: "page_limit_exceeded"` and `diagnostics: {"pages_checked": 30}` before fetching page 31.

### User Story 3 - Module Contract Compliance & Seeding (Priority: P2)

The module is discoverable by the automatic seeder on startup, passes static validation, and integrates with the existing module ecosystem without manual intervention.

**Why this priority**: Required for the module to function in the Binocular ecosystem. P2 because the module's scraping and detection logic (P1, P2) must work first.

**Independent Test**: After deployment, the module appears in the module registry with display name "Godox Flashes" without manual upload.

**Acceptance Scenarios**:

1. **Given** the module file in the official modules directory, **When** the application starts, **Then** the module appears as an installed module in the registry with `display_name: "Godox Flashes"`.
2. **Given** the module registered in the system, **When** the operator creates a new device, **Then** the module is available as a selectable option for device linking.
3. **Given** a dry-run check, **When** the module executes, **Then** no direct HTTP connections bypass the host-provided scraping client.

## Requirements

### Functional Requirements

- **FR-001**: System MUST parse firmware entries from the Godox flash firmware listing at `https://www.godox.com/firmware-flash/`, extracting each entry's model name (from `.item .tit` text before "Firmware"), firmware version (from `.item .tit span`), release date, and firmware page URL (from download link). Download page URLs that are relative paths MUST be resolved to absolute URLs via urljoin with the base page URL. Model matching SHALL use aggressive normalization: strip all non-alphanumeric characters and uppercase both the page title and the user-provided model before comparison (consistent with existing Panasonic and Sony module conventions).
- **FR-002**: System MUST traverse paginated pages following the URL pattern where page 1 is `/firmware-flash/` (no underscore) and pages 2+ use `/firmware-flash_N/`, stopping at the first page where the next-link (`a_next` href) is `javascript:;` (inert), with early termination when the requested model is found.
- **FR-003**: System MUST return `ModuleCheckResult(status="success", latest_version=..., source_url=...)` when a matching flash model is found, with `source_url` set to the absolute firmware download URL and `diagnostics` including `matched_page` (the 1-indexed page number where the model was found), `pages_checked` (total pages traversed), and `firmware_date` (the release date string from the page).
- **FR-004**: System MUST normalize firmware versions by stripping leading `V` or `v` characters, preserving the exact dotted format (e.g., `V1.17` → `1.17`, `v2.6` → `2.6`, `V1.3` → `1.3`). If the version string after V/v stripping does not contain at least one dot (e.g., `V10` → `10`) or contains non-numeric segments beyond the dotted pattern, pass the stripped value through as-is and let the host's version comparison handle it; do not reject or crash on non-standard formats.
- **FR-005**: System MUST return a visible failure status with a descriptive `error_type` and `detail` when: the model is not found after full traversal (`product_not_found`), page 1 yields zero entries (`parse_error`), a network-level error occurs during any page fetch (`firmware_page_unavailable` with `diagnostics: {"http_status": int, "url": str}`, using `0` as sentinel for non-HTTP transport failures), the hard page limit is reached (`page_limit_exceeded`), or an intermediate page (N>1) yields zero entries as part of two consecutive empty pages (`product_not_found`). A single empty page at N>1 that is not part of a consecutive pair is treated as a transient gap: log a warning in diagnostics, reset the empty counter, and continue traversal.
- **FR-006**: System MUST enforce a hard page limit of 30 pages as a circuit breaker; if reached before finding the model, return a `page_limit_exceeded` failure with `diagnostics: {"pages_checked": 30}`. The hard page limit takes precedence over all other termination conditions — if triggered, return `page_limit_exceeded` regardless of consecutive-empty or inert-link state.
- **FR-007**: System MUST use only the host-provided scraping client for all outbound HTTP — no direct HTTP library imports.
- **FR-008**: System MUST be auto-discovered and seeded into the database on startup, appearing in the module registry without manual upload.
- **FR-009**: System MUST be testable via fixture injection (e.g., FakeScrapeClient supporting multi-URL responses) for off-line correctness validation against captured page snapshots.

## Assumptions & Risks

### Assumptions

- The Godox firmware flash page (`/firmware-flash/`) maintains its current HTML structure with `.Firmware .items .item` containers, `.tit` title elements, and `<span>` version elements — all content is server-rendered without client-side JavaScript requirements.
- The pagination URL pattern (`/firmware-flash_N/` for pages 2+) and the inert next-link (`javascript:;`) on the last page remain stable.
- The existing module seeder (E021) requires no changes to discover a new `.py` file in `binocular/official_modules/`.
- Firmware entries continue to appear in reverse chronological order (newest first), making early termination on first match correct.
- Version strings continue to follow the `V`/`v` prefix + dotted numeric pattern observed across all examined pages.

### Risks

- **Manufacturer page structure change** *(likelihood: medium, impact: high)*: If Godox redesigns the firmware listing (changing HTML structure, pagination URL scheme, or version format), the module's parsing will break. Mitigated by honest failure signaling (`parse_error` for zero entries on page 1) and fixture-based regression tests.
- **Pagination exhaustion on large listings** *(likelihood: low, impact: medium)*: If the page count grows significantly beyond the current 14 pages, the hard 30-page limit could be reached, causing `page_limit_exceeded` failures. Mitigated by the circuit breaker itself plus early termination for common models.
- **Model suffix ambiguity for unsuffixed queries** *(likelihood: low, impact: low)*: A user providing "V100" without a camera-brand suffix would receive `product_not_found` because the module requires exact match. Mitigated by documentation and the `supported_device_hints` field in `MODULE_METADATA`.

## Implementation Signals

- `EXTERNAL-SERVICE` — scraping `www.godox.com/firmware-flash/` and paginated subpages via ScrapeClient
- `NEW-CONFIG` — module registration via MODULE_METADATA in `binocular/official_modules/`
- `NEW-ENTITY` — FirmwareEntry dataclass for parsed flash firmware rows (model, version, date, download URL, page number)

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: Running the module against captured fixtures produces `latest_version` matching the actual published version for both provided test models (iT32 → "1.17", V100S → "1.06"), with zero false positives/negatives.
- **SC-002** [US1]: The module returns `status: "failed"` with `error_type: "product_not_found"` when given an unsuffixed model name (e.g., "V100") that has camera-brand variants on the page — confirming exact-match-only behavior.
- **SC-003** [US2]: Running the module against a multi-page fixture where the model appears on page N results in exactly N pages being fetched (verified via FakeScrapeClient URL capture), with no additional pages requested after the match.
- **SC-004** [US2]: Running the module against a fixture where page 1 has zero parseable entries returns `status: "failed"` with `error_type: "parse_error"` and a non-empty `detail` message.
- **SC-005** [US2]: Running the module with a requested model not present in any page of the fixture returns `status: "failed"` with `error_type: "product_not_found"` and `diagnostics.pages_checked` matching the total page count.
- **SC-006** [US3]: The module appears in the module registry with `display_name: "Godox Flashes"` after seeding without manual intervention.
- **SC-007** [US3]: A dry-run check against the fixture produces the expected version for a known model, confirming correct MODULE_METADATA and entrypoint wiring.
- **SC-008** [US2]: Running the module against a multi-page fixture where the model is absent and pages exceed 30 returns `status: "failed"` with `error_type: "page_limit_exceeded"` and `diagnostics.pages_checked: 30`, confirming the circuit breaker engages.

## Glossary

| Term | Definition |
|------|------------|
| Pagination | The Godox firmware listing displays five entries per page, with additional pages accessed via `/firmware-flash_N/` URLs where N is the page number (2, 3, ...). |
| Camera-brand suffix | A single-letter suffix appended to Godox flash model names indicating the camera system variant: C (Canon), N (Nikon), S (Sony), F (Fujifilm), O (Olympus/OM), P (Pentax). |
| Inert next-link | The pagination widget's "next page" link; on the last page, its href is `javascript:;` rather than a real URL, indicating end of pagination. |
| Circuit breaker | A hard limit (30 pages) that prevents unbounded page traversal if the pagination structure changes or the module misparses the next-link. |

## Compliance Check

**Date**: 2026-06-07
**Validator**: `project-instructions.md` v1.0.0 (2026-05-31)
**Result**: **PASS** — No violations across all seven core principles.

| # | Principle | Verdict | Evidence |
|---|-----------|---------|----------|
| I | Honest Failure | PASS | Four explicit `error_type` values (`product_not_found`, `parse_error`, `firmware_page_unavailable`, `page_limit_exceeded`) in FR-005; zero-entries-on-page-1 produces `parse_error` with the explicit rule "must never silently return no result" (Edge Cases); US2 dedicated to honest failure with 5 acceptance scenarios; SC-002/SC-004/SC-005/SC-008 test all failure paths. |
| II | Polite by Default | PASS | Edge case mandates "host-provided scraping client — no direct HTTP library imports"; FR-007: "MUST use only the host-provided scraping client"; US3 SA3 validates no bypass; Excluded section rules out browser automation. Host client handles robots.txt, User-Agent, rate limiting, and backoff by design. |
| III | Data Ownership & Self-Containment | PASS | No external database, message broker, cloud service, account system, telemetry, or analytics mentioned. FR-008 uses the existing SQLite database via auto-seeder. Module is a self-contained `.py` file in `binocular/official_modules/`. |
| IV | Least-Privilege & Trust Boundary | PASS | Module is an in-process unsandboxed extension by design; spec makes no claims of sandboxing. The trust-boundary documentation requirement is a system-level obligation satisfied by project documentation. |
| V | Type Safety & Correctness-First | PASS | Included scope: "Fixture-based golden tests validating detection correctness against captured page snapshots, including multi-page scenarios"; FR-009: "MUST be testable via fixture injection (e.g., FakeScrapeClient)"; SC-001: "zero false positives/negatives" against captured fixtures; SC-007: dry-run fixture validation. |
| VI | Set-and-Forget Reliability | PASS | FR-008: auto-discovery and seeding = zero required configuration. Module introduces no new infrastructure or state beyond SQLite. No process spawning, threading, or resource patterns that would undermine host-level module failure isolation. |
| VII | Agent Output Style | N/A | Applies to agent communication, not spec content. |

## Clarifications

### Session 2026-06-07

- Q: Model normalization algorithm — aggressive (strip non-alphanumeric, uppercase) or conservative (whitespace-only)? → A: Aggressive — strip all non-alphanumeric characters and uppercase. Matches existing Panasonic and Sony module conventions, ensuring consistent behavior across modules.
- Q: Zero-parseable entries on an intermediate page (N>1) — end-of-pagination, parse_error, or skip? → A: Treat as end-of-pagination only when part of 2 consecutive empty pages, returning product_not_found. A single empty page at N>1 is a transient gap: log warning, reset counter, continue.
- Q: How to handle non-standard version formats (V1.0.1, V1.10a, V10)? → A: All formats are parseable — strip V/v prefix and pass through as-is. The host version comparison handles non-standard formats; do not reject or crash.
- Q: Where should firmware date and download URL appear in result? → A: Match the Panasonic/Sony convention: date in diagnostics, source_url set to the firmware download URL.
- Q: What http_status for non-HTTP transport failures (DNS, connection refused)? → A: Use http_status: 0 as sentinel with firmware_page_unavailable error_type, consistent with existing module patterns.
- Q: How many fixture files should be committed? → A: Commit all six test scenarios: five HTML fixture files (page-1-hit, page-2, page-3-hit, parse-error, empty-page) and one programmatic circuit-breaker scenario (30-page limit tested via FakeScrapeClient in test code, not a committed .html file) for deterministic offline validation.

## Stress-Test Findings

### Session 2026-06-07

- **STF-001** (HIGH, cross-requirement-contradiction): Termination-condition priority between hard page limit (FR-006 → page_limit_exceeded) and consecutive-empty-pages (→ product_not_found) was undefined. **Resolution**: Added explicit priority clause to FR-006 — the hard page limit is checked first and takes precedence over all other termination conditions.
- **STF-002** (MEDIUM, boundary-scale-stress): Version format normalization boundary underspecified for non-conforming versions (single-segment, three+ segments, non-numeric). **Resolution**: Extended FR-004 with fallback rule — strip V/v and pass through as-is; never reject or crash on non-standard formats.
- **STF-003** (MEDIUM, boundary-scale-stress): Solo empty page at N>1 had no defined behavior. **Resolution**: Edge Cases updated — single empty page is a transient gap (log warning, reset counter, continue); parse_error reserved exclusively for page 1 zero entries.
- **STF-004** (MEDIUM, boundary-scale-stress): Whitespace normalization algorithm for model matching was declared but not defined. **Resolution**: FR-001 updated with explicit algorithm — strip all non-alphanumeric characters and uppercase (aggressive normalization, matching existing module conventions).
- **STF-005** (MEDIUM, cross-requirement-contradiction): Consecutive-empty-pages termination returned product_not_found but diagnostics.pages_checked semantics (actual vs total) were ambiguous. **Resolution**: Edge Cases clarified — pages_checked reflects pages actually fetched, not total traversable page count.
| Fixture | A captured snapshot of the real firmware page HTML used for offline regression testing; may include multiple page captures for pagination scenarios. |
