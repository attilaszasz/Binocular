---
feature_branch: "00012-official-sony-alpha-module"
created: "2026-05-31"
input: "E015 Official Sony Alpha Module; test case Sony A7CII ILCE-7CM2 current 2.00 detects latest 2.01"
spec_type: "product"
spec_maturity: "draft"
epic_id: "E015"
epic_sources: "{PRD:CAP-011}"
---

# Feature Specification: Official Sony Alpha Module

**Feature Branch**: `00012-official-sony-alpha-module`  
**Created**: 2026-05-31  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: draft  
**Epic ID**: E015  
**Epic Sources**: {PRD:CAP-011}  
**Product Document**: specs/prd.md

## Problem Statement

Sony Alpha camera and lens owners currently need to manually inspect Sony firmware listings to know whether offline gear is behind. Binocular needs an officially shipped Sony Alpha starter module that supports the full Alpha Universe firmware index, not a single validation model, so users get immediate value and module authors get a concrete, tested example. If this feature is incomplete or model-specific, the product can silently miss one of its promised starter ecosystems.

## Scope

### Included

- Official Sony Alpha module capable of detecting the latest published firmware version for Sony cameras and lenses listed on `https://alphauniverse.com/firmware/`.
- Fixture-backed detection correctness for the Alpha Universe firmware index, including Sony A7CII / ILCE-7CM2 where stored version `2.00` detects newer published version `2.01`.
- Integration with the existing unsandboxed module contract and host-provided scraping client.
- Visible scrape failure behavior when a supported Sony page is unavailable or cannot be parsed.

### Excluded

- Firmware download, installation, or device flashing — Binocular only detects and reports availability.
- Parsing unrelated regional Sony support pages outside the Alpha Universe firmware index — the index is the canonical source for this module.
- New module-management UI flows — lifecycle management already exists in E008.

### Edge Cases & Boundaries

- Model aliases, marketing names, store SKUs, and support model codes may differ and must not cause a false positive for the wrong camera or lens.
- Alpha Universe page layout or embedded-data changes must surface as a scrape failure rather than an absent or stale result.
- Firmware versions may contain leading zeroes or dotted numeric segments and must compare through the existing version-comparison service.

## User Scenarios & Testing

### User Story 1 - Detect Sony Alpha Updates (Priority: P1)

An operator with Sony Alpha cameras or lenses can use the shipped Sony module to check the Alpha Universe firmware index and see the latest firmware version returned for any listed product.

**Why this priority**: Core value proposition — the shipped module must detect real Sony Alpha updates correctly.

**Independent Test**: Run the Sony module against a captured Alpha Universe firmware-index fixture and verify both camera and lens entries are matched, including latest version `2.01` for model `ILCE-7CM2`.

**Acceptance Scenarios**:

1. **Given** a Sony A7CII device with model `ILCE-7CM2` and stored version `2.00`, **When** the Sony module checks an Alpha Universe fixture containing firmware version `2.01`, **Then** Binocular reports that a newer firmware version is available.
2. **Given** a Sony lens such as `SEL2470GM` listed in an Alpha Universe fixture, **When** the module checks the fixture, **Then** it returns the lens firmware version and download URL.
3. **Given** a supported Alpha Universe firmware fixture, **When** the module parses the page, **Then** it returns the latest firmware version and source URL without requiring direct outbound requests outside the host scraping client.

### User Story 2 - Surface Sony Scrape Failures (Priority: P2)

An operator can trust that a Sony page change or unsupported Sony model does not appear as a quiet no-update result.

**Why this priority**: Significant reliability value — MVP detection works without it, but honest failure preserves trust when pages change.

**Independent Test**: Run the module against an unparseable Sony fixture and verify a visible failure result is produced.

**Acceptance Scenarios**:

1. **Given** a Sony page fixture without any parseable firmware version, **When** the module checks it, **Then** the check records a scrape failure rather than reporting no update.

## Requirements

### Functional Requirements

- **FR-001**: System MUST ship an official Sony Alpha module that implements the existing module authoring contract.
- **FR-002**: System MUST parse the Alpha Universe firmware index and detect listed Sony camera and lens firmware versions by model code, product name, or store SKU.
- **FR-003**: System MUST use the host-provided scraping client for Sony page retrieval and MUST NOT perform direct outbound requests from the module.
- **FR-004**: System MUST surface unparseable Alpha Universe content, unlisted products, and listed products without firmware as visible failures instead of silent no-update results.
- **FR-005**: System MUST include captured Alpha Universe fixtures and automated tests that verify zero false positives and zero false negatives for shipped camera, lens, and failure cases.

### Key Entities

- **Sony Alpha Module**: Official extension module that maps Alpha Universe camera and lens catalog entries to firmware detection results.
- **Alpha Universe Fixture**: Captured firmware-index content used to validate version extraction and failure behavior without live network dependency.
- **Firmware Detection Result**: Structured module output consumed by the existing check and comparison services.

## Assumptions & Risks

### Assumptions

- Alpha Universe firmware-index content includes parseable catalog entries for cameras and lenses, including `ILCE-7CM2` version `2.01`.
- Existing module engine and detection comparison services are available from E006 and E009.
- Fixture-based validation is sufficient for release correctness; live Sony pages are not required in CI.

### Risks

- **Alpha Universe embedded-data changes** *(likelihood: medium, impact: high)*: Page data structure may change; mitigate by keeping parser failure visible and tests fixture-driven.
- **Model alias mismatch** *(likelihood: medium, impact: medium)*: Marketing names, model codes, and store SKUs may diverge; mitigate with explicit camera and lens fixture coverage.
- **Fixture drift** *(likelihood: low, impact: medium)*: Captured fixtures may become stale; mitigate by documenting actual latest version expectations in tests.

## Implementation Signals

- `NEW-WORKER` — Add an official extension module consumed by the existing module runner/check flow.
- `EXTERNAL-SERVICE` — Sony support pages are third-party scrape sources and must use the centralized polite scraping client.
- `BREAKING-CHANGE` — None expected; the module must conform to existing public contracts.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: Alpha Universe fixture validation returns Sony A7CII / `ILCE-7CM2` latest version `2.01` and Binocular determines it is newer than stored version `2.00`.
- **SC-002** [US1]: Alpha Universe fixture validation returns at least one Sony lens firmware version by lens model code.
- **SC-003** [US2]: Unparseable, unlisted, and no-firmware Alpha Universe fixture cases produce visible failure statuses, not no-update results.

## Glossary

| Term | Definition |
|------|------------|
| Sony Alpha | Sony interchangeable-lens camera ecosystem targeted by this starter module. |
| ILCE-7CM2 | Sony model code for Sony A7CII. |
| Alpha Universe firmware index | Sony page at `https://alphauniverse.com/firmware/` listing camera and lens firmware metadata. |
| Fixture | Captured Alpha Universe page content used for deterministic module correctness tests. |

## Compliance Check

PASS — The specification aligns with project instructions: official modules use fixture-based correctness validation, polite scraping remains centralized, and failures are visible.