---
feature_branch: "00011-official-sony-alpha-module"
created: "2026-06-10"
input: "E011 Official Sony Alpha Module"
spec_type: "product"
spec_maturity: "draft"
epic_id: "E011"
epic_sources: "{PRD:CAP-011}"
---

# Feature Specification: Official Sony Alpha Module

**Feature Branch**: `00011-official-sony-alpha-module`  
**Created**: 2026-06-10  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: draft  
**Epic ID**: E011  
**Epic Sources**: {PRD:CAP-011}  
**Product Document**: specs/prd.md

## Problem Statement

Offline devices like Sony Alpha cameras do not have auto-update features, requiring operators to manually check manufacturer support pages. To automate firmware discovery for Sony Alpha cameras and lenses, Binocular needs a dedicated extension module. This module must implement the authoring contract, scrape the Sony Alpha Universe firmware index, extract version details, and validate correctly under both AST and runtime phases.

## Scope

### Included

- Implementation of the official Sony Alpha module (`sony_alpha.py`) satisfying the V1 authoring contract.
- Module-level constants: `MODULE_VERSION` and `SUPPORTED_DEVICE_TYPE`.
- Parsing logic for Sony Alpha Universe firmware index (extracting JSON arrays of `SONY_CAMERAS` and `SONY_LENSES`).
- Mapping device models (using marketing names, model numbers, or DTC SKUs) to parsed entries.
- Golden tests using captured HTML fixtures to verify extraction correctness, zero false positives, and zero false negatives.
- Visible parse failure diagnostics for missing catalog, unlisted model, or missing firmware.

### Excluded

- Seeding the module in the database automatically on startup — deferred to E016.
- Frontend UI for adding devices or managing modules — covered in E006 and E009.

### Edge Cases & Boundaries

- Target page structure changes or JSON arrays missing: must return a failed result with `firmware_index_not_found` error code.
- Model found in catalog but has empty version string: must return a failed result with `firmware_not_available` error code.
- Model not present in catalog: must return a failed result with `product_not_found` error code.
- Variations in model naming (e.g., "Sony A7CII", "A7C II", "ILCE-7CM2"): normalization must allow correct matching.

## User Scenarios & Testing

### User Story 1 - Detect Firmware version (Priority: P1)

An operator wants to automatically check for updates on their Sony A7C II camera using the official Sony Alpha module.

**Why this priority**: Without this, the system cannot verify updates for Sony Alpha cameras, which is the core value proposition of E011.

**Independent Test**: Run a test that scrapes a mock Sony Alpha Universe firmware page and extracts the correct firmware version `2.01` for `ILCE-7CM2` and `2` for `SEL2470GM`.

**Acceptance Scenarios**:

1. **Given** a mock scrape client configured with a valid firmware catalog HTML fixture, **When** `check_firmware` is called with model `ILCE-7CM2`, **Then** the module returns version `2.01`, the correct download URL, and success status.
2. **Given** a mock scrape client configured with a valid firmware catalog HTML fixture, **When** `check_firmware` is called with model `Sony A7CII` (marketing name), **Then** the module normalizes the model, matches it to `ILCE-7CM2`, and returns version `2.01`.

### User Story 2 - Handle Parse Failures (Priority: P2)

An operator wants clear, diagnostic feedback when a firmware check fails due to manufacturer page structural changes or missing products.

**Why this priority**: Supports the "honest failure" product principle — ensures failures are visible and categorizable instead of causing silent failures or generic crashes.

**Independent Test**: Execute tests with unparseable HTML, unlisted models, or models without listed firmware, verifying that the module returns failure statuses and correct diagnostic error types.

**Acceptance Scenarios**:

1. **Given** a mock scrape client configured with unparseable HTML, **When** `check_firmware` is executed, **Then** it returns failure with error type `firmware_index_not_found`.
2. **Given** a valid HTML catalog, **When** `check_firmware` is executed for model `ILCE-1` (which is not in the catalog), **Then** it returns failure with error type `product_not_found`.
3. **Given** a valid HTML catalog, **When** `check_firmware` is executed for model `ILCE-6100` (which has no version listed), **Then** it returns failure with error type `firmware_not_available`.

## Requirements

### Functional Requirements

- **FR-001**: System MUST define the official Sony Alpha module in a file named `sony_alpha.py` implementing the V1 authoring contract.
- **FR-002**: System MUST parse both `SONY_CAMERAS` and `SONY_LENSES` JSON arrays from the Sony Alpha Universe support page.
- **FR-003**: System MUST support resolving models using their official model code (e.g. `ILCE-7CM2`), marketing name (e.g. `Sony A7CII`), or DTC SKU (e.g. `ilce7cm2b`).
- **FR-004**: System MUST return explicit, typed diagnostic errors on failure (`firmware_index_not_found`, `product_not_found`, `firmware_not_available`).
- **FR-005**: System MUST provide golden/fixture-based tests validating parsing correctness under both successful and failing scenarios.

### Key Entities

- **Sony Alpha Module**: The Python script executing the firmware check, conforming to `MODULE_VERSION = "1.0.0"` and `SUPPORTED_DEVICE_TYPE = "camera"`.

## Assumptions & Risks

### Assumptions

- The target manufacturer website embeds products in `window.firmwareProducts` JSON structure.
- The ScrapeClient handles polite rate limits and robots.txt.

### Risks

- **Page Layout Redesign** *(likelihood: medium, impact: high)*: Sony changes their Alpha Universe site layout or changes the name of `window.firmwareProducts`. Mitigation: Module returns typed diagnostics (`firmware_index_not_found`) so the failure is immediately observable in the activity log.

## Implementation Signals

- `NEW-ENTITY` — Implementation of `backend/src/binocular/official_modules/sony_alpha.py` as an official module.
- `NEW-UI` — Not applicable for this backend module epic.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: `sony_alpha.py` passes Phase 1 AST validation and Phase 2 runtime validation in the module engine.
- **SC-002** [US1]: Tests verify correct version extraction (e.g. `2.01` for `ILCE-7CM2` and `2` for `SEL2470GM`) using golden fixtures.
- **SC-003** [US2]: Tests verify that parse failures return success=False (or status=failed) with explicit error diagnostics.

## Glossary

| Term | Definition |
|------|------------|
| DTC SKU | Direct-to-Consumer Stock Keeping Unit (e.g., "ilce7cm2b" for Sony A7C II black body). |
| Alpha Universe | Sony's firmware update catalog web page at `https://alphauniverse.com/firmware/`. |
