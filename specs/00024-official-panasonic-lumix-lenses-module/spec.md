---
feature_branch: "00024-official-panasonic-lumix-lenses-module"
created: "2026-06-06"
input: "Official Panasonic Lumix Lenses Module — Panasonic Lumix Lenses detection from https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index5.html with fixtures"
spec_type: "product"
spec_maturity: "clarified"
epic_id: "E023"
epic_sources: "{PRD:CAP-011}"
---

# Feature Specification: Official Panasonic Lumix Lenses Module

**Feature Branch**: `00024-official-panasonic-lumix-lenses-module`  
**Created**: 2026-06-06  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: clarified  
**Epic ID**: E023  
**Epic Sources**: {PRD:CAP-011}  
**Product Document**: specs/prd.md

## Problem Statement

Panasonic Lumix lens owners have no automated way to track firmware updates for their L-mount (S-series) and Micro Four Thirds (H-series) lenses. While Binocular already ships a module for Panasonic Lumix MFT camera bodies (E020), the separate lens firmware page (`index5.html`) has a distinct table structure, model patterns, and JavaScript handlers. Lens owners must manually check this page, risking missed updates that degrade lens performance and compatibility.

## Scope

### Included

- A new official extension module `official.panasonic_lumix_lenses` implementing the Binocular authoring contract
- Parsing of the Panasonic Lumix Lenses firmware table from `index5.html`
- Detection of L-mount (S-*) and Micro Four Thirds (H-*) lens models
- Fixture-based golden tests validating detection correctness against captured page snapshots
- A `FirmwareEntry` dataclass for parsed lens firmware rows (model, version, date, download URL)
- A `MODULE_METADATA` descriptor with `module_id: "official.panasonic_lumix_lenses"`, `display_name: "Panasonic Lumix Lenses"`, author, version, and `supported_device_hints` including "Panasonic Lumix", "L-mount", "Micro Four Thirds"
- Auto-discovery and seeding by the existing startup seeder (E021)

### Excluded

- Camera body firmware detection — handled by existing `official.panasonic_lumix_mft_cameras` module
- LEICA or SIGMA lens support listed on the same page but from other manufacturers
- Real-time scraping validation — tested via captured fixtures only

### Edge Cases & Boundaries

- Model not found in the firmware table → returns `product_not_found` failure status
- `check_input.model` is empty, `None`, or whitespace-only → treated as model-not-found, returns `product_not_found` (no unhandled exception)
- Firmware version cell empty or missing for a listed model → returns `firmware_not_available` failure status
- Firmware version cell contains non-parseable text (whitespace-only, placeholders, non-numeric) for a listed model → returns `firmware_not_available` failure status
- Lens entry has a valid model and version but no download handler (OpenWin/OpenWinS) → returns `download_url_not_found` failure status
- `check_input.current_version` is empty or non-parseable → detection still succeeds (returns `latest_version`), but version comparison is skipped — module does not crash or produce a misleading result
- Page structure changes and table is unparseable → returns `firmware_index_not_found` failure status
- HTTP error or timeout from the firmware page → returns `firmware_page_unavailable` failure status with `diagnostics` containing `{"http_status": int, "url": str}`
- Module must route all outbound HTTP through the host-provided scraping client — no direct HTTP library usage
- Download page URLs must be correctly resolved for both L-mount and MFT lens entries
- When an H-* model could match both the lenses module and the cameras module, the operator selects the correct module during device linking — both modules remain independently valid for their respective device types

## User Scenarios & Testing

### User Story 1 - Lens Firmware Version Detection (Priority: P1)

An operator with a Panasonic Lumix lens (e.g., S-R1635 L-mount or H-E08018 MFT) links the device to the Panasonic Lumix Lenses module. When a check runs, the module scrapes the lenses firmware page, locates the matching lens model, and returns the latest published firmware version.

**Why this priority**: Core value — without detection, the module provides no utility. P1 alone yields a viable module.

**Independent Test**: Run the module with model "S-R1635" against the captured fixture; verify `latest_version` is "2.0", `status` is "success", and `source_url` resolves to the download page.

**Acceptance Scenarios**:

1. **Given** a L-mount lens model "S-E2470" in the fixture page, **When** the module checks firmware, **Then** the result returns `latest_version: "2.0"` and `status: "success"` with the download page URL.
2. **Given** a MFT lens model "H-ES12035" in the fixture page, **When** the module checks firmware, **Then** the result returns `latest_version: "1.1"` and `status: "success"`.
3. **Given** a model "DC-GH7" (a camera, not a lens), **When** the module checks firmware, **Then** the result returns `status: "failed"` with `error_type: "product_not_found"`.

### User Story 2 - Honest Failure Signaling (Priority: P2)

When the lenses firmware page is unavailable, changes structure, or a lens model is not listed, the module surfaces a visible failure with diagnostic context rather than silently returning no result.

**Why this priority**: Honest failure is a core Binocular principle (project-instructions I). Essential for trust but the module's primary value is detection — honest failure is a safeguard, not the main flow.

**Independent Test**: Run the module against an unparseable fixture; verify `status: "failed"` and `detail` contains a descriptive message.

**Acceptance Scenarios**:

1. **Given** an HTML page with no firmware table, **When** the module checks firmware, **Then** the result returns `status: "failed"` with `error_type: "firmware_index_not_found"`.
2. **Given** a lens model "S-NONEXIST" not in the fixture, **When** the module checks firmware, **Then** the result returns `status: "failed"` with `error_type: "product_not_found"`.
3. **Given** a lens model without a version listed, **When** the module checks firmware, **Then** the result returns `status: "failed"` with `error_type: "firmware_not_available"`.
4. **Given** a lens model listed in the fixture but with no download handler (no `OpenWin`/`OpenWinS`), **When** the module checks firmware, **Then** the result returns `status: "failed"` with `error_type: "download_url_not_found"`.
5. **Given** a FakeScrapeClient that raises a ScrapeTransportError (simulating a network failure), **When** the module checks firmware, **Then** the result returns `status: "failed"` with `error_type: "firmware_page_unavailable"` and `diagnostics` containing the HTTP status code and attempted URL.

### User Story 3 - Module Contract Compliance & Seeding (Priority: P2)

The module is discoverable by the automatic seeder on startup, passes static validation, and integrates with the existing module ecosystem without manual intervention.

**Why this priority**: Required for the module to function in the Binocular ecosystem. P2 because the module's scraping logic (P1) must work first.

**Independent Test**: After deployment, the module appears in the module registry with display name "Panasonic Lumix Lenses" and device type "Panasonic Lumix" without manual upload.

**Acceptance Scenarios**:

1. **Given** the module file in the official modules directory, **When** the application starts, **Then** the module appears as an installed module in the registry with `display_name: "Panasonic Lumix Lenses"`.
2. **Given** the module registered in the system, **When** the operator creates a new device, **Then** the module is available as a selectable option for device linking.
3. **Given** a dry-run check, **When** the module executes, **Then** no direct HTTP connections bypass the host-provided scraping client.

## Requirements

### Functional Requirements

- **FR-001**: System MUST parse L-mount (S-*) and Micro Four Thirds (H-*) lens firmware entries from the Panasonic lenses firmware page at `https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index5.html`.
- **FR-002**: System MUST extract the firmware version, model code, and download page URL for each lens entry, plus the firmware date (mandatory extraction for diagnostics, surfaced in `diagnostics["firmware_date"]`; no user-facing date comparison required).
- **FR-003**: System MUST return `ModuleCheckResult(status="success", latest_version=...)` when a matching lens model is found with a firmware version.
- **FR-004**: System MUST return a visible failure status with a descriptive `error_type` and `detail` when the model is not found (`product_not_found`), the page structure is unrecognizable (`firmware_index_not_found`), firmware is not listed for a found model (`firmware_not_available`), the download URL cannot be resolved (`download_url_not_found`), or a network-level error occurs (`firmware_page_unavailable`).
- **FR-005**: System MUST resolve the correct firmware download page URL for each lens entry, extracting download handlers from both `OpenWin` (MFT) and `OpenWinS` (L-mount) JavaScript functions.
- **FR-006**: System MUST use only the host-provided scraping client for all outbound HTTP — no direct client library imports.
- **FR-007**: System MUST be auto-discovered and seeded into the database on startup, appearing in the module registry without manual upload.
- **FR-008**: System MUST be testable via fixture injection (e.g., FakeScrapeClient) for off-line correctness validation against captured page snapshots.

## Assumptions & Risks

### Assumptions

- The Panasonic lenses firmware page (`index5.html`) maintains the current HTML table structure with `OpenWin`/`OpenWinS` JavaScript handlers.
- Lens model codes follow the `S-*` (L-mount) and `H-*` (MFT) prefix patterns observed on the live page.
- The existing module seeder (E021) requires no changes to discover a new file in `binocular/official_modules/`.

### Risks

- **Manufacturer page structure change** *(likelihood: medium, impact: high)*: If Panasonic redesigns the lenses page, the module's parsing will break. Mitigated by honest failure signaling and fixture-based regression tests.
- **Model pattern collision with cameras module** *(likelihood: low, impact: low)*: The cameras module's MFT model regex could match some H-* lens codes if used incorrectly. Mitigated by the dedicated lenses module URL and distinct model regex.

## Implementation Signals

- `NEW-ENTITY` — FirmwareEntry dataclass for parsed lens firmware rows
- `EXTERNAL-SERVICE` — scraping `av.jpn.support.panasonic.com` via ScrapeClient
- `NEW-CONFIG` — module registration via MODULE_METADATA in `binocular/official_modules/`

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: Running the module against the captured fixture produces `latest_version` matching the actual published version for every lens model in the fixture (zero false positives/negatives).
- **SC-002** [US1]: The module resolves a download page URL for each lens entry in the fixture that has an associated download handler, where the resolved URL matches the expected URL captured in the fixture (valid, well-formed, non-empty).
- **SC-003** [US2]: Running the module against an unparseable fixture returns `status: "failed"` with a non-empty `detail` message and a meaningful `error_type`.
- **SC-004** [US2]: Running the module with a non-lens model returns `status: "failed"` with `error_type: "product_not_found"`.
- **SC-005** [US3]: The module appears in the module registry after seeding without manual intervention.
- **SC-006** [US3]: A dry-run check against the fixture produces the expected version for a known lens model, confirming correct metadata and entrypoint wiring.

## Glossary

| Term | Definition |
|------|------------|
| L-mount | Leica-developed lens mount standard used by Panasonic S-series lenses; identified by `S-` model prefix |
| Micro Four Thirds (MFT) | Sensor format and lens mount standard; Panasonic lenses use `H-` model prefix |
| OpenWin / OpenWinS | JavaScript functions on the Panasonic support page that open download popup windows for firmware files |
| Fixture | A captured snapshot of the real firmware page HTML used for offline regression testing |

## Clarifications

### Session 2026-06-06

- Q: Does OpenWinS encode URLs the same way as OpenWin (via window.open() in script blocks)? → A: Same pattern as cameras module — extract from window.open() calls in script blocks, just with OpenWinS handler names.
- Q: What symbols must the module export beyond check_firmware? → A: Match the cameras module (E020) contract exactly: export a MODULE_METADATA descriptor and a check_firmware entrypoint accepting a model identifier and scraping client, returning a structured result with version or failure information. See plan.md for the concrete function signature.
- Q: What model matching rules apply for lens codes? → A: Same as cameras: case-insensitive, strip non-alphanumeric. L-mount and MFT lens codes have no / delimited variants, but normalization ensures robust matching.
- Q: What regex distinguishes lens rows from non-lens rows? → A: Match only S- (L-mount) and H- (MFT) prefixed rows; reject everything else.
- Q: Is firmware_date mandatory or optional? → A: Mandatory extraction (property of FirmwareEntry) but only surfaced in diagnostics — no user-facing date comparison needed.
- Q: What error_type for network-level failures (4xx, 5xx, timeouts)? → A: New error_type 'firmware_page_unavailable' with detail containing the HTTP status and URL — consistent with honest-failure principle.

## Stress-Test Findings

### Session 2026-06-06

- **STF-001** (HIGH, constraint-impossibility): Download URL extraction impossible for lens rows lacking both OpenWin and OpenWinS handlers. **Resolution**: Added `download_url_not_found` error_type to FR-004 and Edge Cases; relaxed SC-002 to apply only to entries with extractable handlers.
- **STF-002** (MEDIUM, concurrent-trigger-ambiguity): No ordering guarantee between module seeding and first firmware check. **Resolution**: E021 seeder runs synchronously during startup lifespan before any endpoints are served; module seeding completes before checks execute.
- **STF-003** (MEDIUM, boundary-scale-stress): No upper bounds defined for page size, entry count, or timeout. **Resolution**: Host ScrapeClient enforces HTTP timeout (default 10s). Page size is bounded by the client's response buffer. No additional module-level bounds needed.
- **STF-004** (MEDIUM, concurrent-trigger-ambiguity): Concurrent check_firmware invocations have no defined fan-out contract. **Resolution**: Host module engine invokes check_firmware independently per-device; the ScrapeClient handles internal concurrency safely. Module need not serialize.
- **STF-005** (MEDIUM, boundary-scale-stress): firmware_not_available boundary undefined for whitespace-only or non-numeric version cells. **Resolution**: Clarified firmware_not_available triggers on empty, whitespace-only, or non-parseable version cells in FR-004 and Edge Cases.

## Compliance Check

**Target**: `specs/00024-official-panasonic-lumix-lenses-module/spec.md`
**Status**: **PASS**

| Principle | Verdict | Notes |
|-----------|---------|-------|
| I. Honest Failure | PASS | US2 + FR-004 mandate visible failure with `error_type`/`detail`; Edge Cases cover `product_not_found`, `firmware_not_available`, `firmware_index_not_found`; SC-003/SC-004 validate failure paths. |
| II. Polite by Default | PASS | Edge Cases + FR-006 explicitly prohibit direct HTTP library imports; all scraping via host-provided client; US3 AC3 verifies no direct HTTP connections. |
| III. Data Ownership & Self-Containment | PASS | Module integrates with existing SQLite-seeded ecosystem (E021); no external databases, brokers, or cloud services introduced. |
| IV. Least-Privilege & Trust Boundary | PASS | No sandboxing claims made; module runs as a standard official module under the documented trust boundary. |
| V. Type Safety & Correctness-First | PASS | SC-001 requires zero false positives/negatives via fixture tests; FR-008 requires offline fixture-based correctness validation. |
| VI. Set-and-Forget Reliability | PASS | US2 honest failure signaling prevents silent misses; FR-004 returns descriptive failures rather than crashing; module-scoped failures cannot crash core process. |
| VII. Agent Output Style | N/A | Applies to agent communication, not spec content. |

**Artifact Conventions**: All required frontmatter, mandatory sections, and ID formats present. No violations.

**Verdict**: **PASS**
