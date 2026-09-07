---
feature_branch: "00032-official-canon-rf-lenses"
created: "2026-09-07"
input: "E029 Official Canon RF Lenses"
spec_type: "product"
spec_maturity: "clarified"
epic_id: "E029"
epic_sources: "{PRD:CAP-015}{SAD:ADR-0005}{SAD:ADR-0012}"
---

# Feature Specification: Official Canon RF Lenses

**Feature Branch**: `00032-official-canon-rf-lenses`  
**Created**: 2026-09-07  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: clarified  
**Epic ID**: E029  
**Epic Sources**: {PRD:CAP-015}{SAD:ADR-0005}{SAD:ADR-0012}  
**Product Document**: `specs/prd.md`

## Problem Statement

Canon RF and RF-S lens owners must interpret regional firmware pages themselves. They need model-only monitoring that admits exact lens products while excluding accessories and unrelated mounts. Inferred coverage, duplicate package results, or hidden source failures would undermine unattended monitoring.

## Scope

### Included

- One independently selectable, automatically seeded official Canon RF Lenses module.
- Exact model-only lookup against Canon Asia English RF and RF-S catalogues with explicit lens classification.
- Catalogue-to-product-to-firmware-action discovery using source-provided links and actions.
- Operating-system package deduplication, normalized versions, and official release-detail links.
- Captured-source correctness coverage for release, no-firmware, and failure paths.

### Excluded

- Canon cameras, adapters, extenders, cinema lenses, unrelated mounts, other regions, and fallback rotation — outside verified lens coverage.
- Positive RF-S firmware claims — no release is verified.
- Firmware binaries, installation, new UI, API, schema, or configuration — existing detection flows are reused.

### Edge Cases & Boundaries

- Similar names, aperture variants, generations, and RF versus RF-S must not cross-match.
- Non-lens catalogue accessories must not be admitted.
- Duplicate Windows and macOS packages for the same model/version represent one release.
- No-firmware, unknown model, source drift, denial, timeout, and cancellation are distinct visible failures.
- Concurrent Canon camera and lens work shares the same Canon-origin 30-second pacing timeline, including retries.

## User Scenarios & Testing

### User Story 1 - Monitor an Exact Canon RF Lens (Priority: P1)

As a Canon lens owner, I can select the module and enter my exact RF/RF-S model without a firmware URL.

**Why this priority**: Exact, classified model-only firmware discovery is the feature's independently useful core value.

**Independent Test**: Search and check RF24-105mm F4 L IS USM through the captured source chain.

**Acceptance Scenarios**:

1. **Given** captured sources and `RF24-105mm F4 L IS USM`, **When** search or check runs, **Then** fixture version `2.0.7` and official detail URL `https://asia.canon/en/support/0401117302?model=RF24-105mm+F4L+IS+USM` are returned.
2. **Given** equivalent Windows and macOS packages for version `2.0.7`, **When** releases are interpreted, **Then** one model/version release is selected.
3. **Given** repeated seeding, **When** modules are listed, **Then** exactly one Canon RF Lenses definition exists with no required URL.

### User Story 2 - Receive Honest Unsupported and Unavailable Outcomes (Priority: P1)

As an operator, I see unsupported, unavailable, and failed outcomes instead of false firmware results.

**Why this priority**: Honest failure and zero false positives or negatives are mandatory for unattended monitoring.

**Independent Test**: Exercise accessory, near-name, RF-S no-firmware, and source-failure fixtures.

**Acceptance Scenarios**:

1. **Given** an excluded or inexact product, **When** checked, **Then** a visible unsupported failure occurs with no version.
2. **Given** captured RF-S18-45mm no-firmware evidence, **When** checked, **Then** firmware unavailability is visible and no positive RF-S release is claimed.
3. **Given** a missing catalogue structure or firmware action, **When** checked, **Then** source drift is surfaced and no stale or inferred result succeeds.
4. **Given** timeout or cancellation, **When** reached, **Then** the check fails visibly and no later request occurs.

### User Story 3 - Operate Politely Without Configuration (Priority: P2)

As an operator, I use the module without source configuration while requests remain polite and bounded.

**Why this priority**: This safeguards the source and reliability but builds on P1 discovery and failure behavior.

**Independent Test**: Verify deterministic shared pacing, retries, and cancellation without real sleeps.

**Acceptance Scenarios**:

1. **Given** concurrent Canon camera and lens checks, **When** each issues requests or retries, **Then** all attempts share one Canon-origin timeline with at least 30 seconds between attempts.
2. **Given** no user-supplied URL or Canon setting, **When** a supported model is checked, **Then** the bounded flow completes using official catalogue discovery.

## Requirements

### Functional Requirements

- **FR-001**: System MUST ship one independently selectable Canon RF Lenses module that accepts a model without a URL and seeds idempotently.
- **FR-002**: System MUST resolve only RF or RF-S catalogue models equal after trimming surrounding whitespace and case-folding, and MUST reject near-name or ambiguous inputs.
- **FR-003**: System MUST classify matched entries as lenses and reject adapters, extenders, cinema products, and unrelated mounts even when listed by the RF catalogue.
- **FR-004**: System MUST follow the catalogue's product link verbatim and discover the firmware form action from that product page rather than construct either route from the model name.
- **FR-005**: System MUST use model-specific firmware content, normalize versions, deduplicate equivalent operating-system packages, and return the matching release-detail page rather than a binary route.
- **FR-006**: System MUST distinguish unsupported products, explicit no-firmware, source drift, denial, timeout, and cancellation without invented or stale versions or positive RF-S release claims.
- **FR-007**: System MUST route every outbound request through the host-provided scraping client and share Canon's effective per-origin interval across catalogue, product, firmware, concurrent, and retry requests.
- **FR-008**: System MUST use a bounded source-aware budget, issue no requests after timeout or cancellation, and preserve unaffected-source budgets.
- **FR-009**: System MUST support existing version-search and normal manual/scheduled check execution without new required configuration, UI, API, or persisted state.
- **FR-010**: System MUST validate the officially shipped module against captured fixtures with zero false positives and zero false negatives for the supported matrix, including RF24-105mm `2.0.7`, RF-S no-firmware, accessory exclusions, and exact near-name rejection.
- **FR-011**: Documentation MUST define the Canon Asia English region, RF/RF-S catalogue and classification boundaries, release semantics, exclusions, and unverified positive RF-S status.

## Assumptions & Risks

### Assumptions

- Canon Asia English remains the regional authority; parity is not implied.
- Existing module, seeding, search, check, and error boundaries remain available.
- Catalogue text or links distinguish lenses from accessories and cinema products.
- Numeric versions use existing comparison; unexpected syntax fails visibly.
- Captured versions are evidence and may cease to be latest.

### Risks

- **Source drift** *(likelihood: high, impact: high)*: Source stages can change independently; structural fixtures and visible failures mitigate misses.
- **Classification error** *(likelihood: medium, impact: high)*: Accessories could be admitted or lenses excluded; conservative fixture matrices mitigate false coverage.
- **Long source pacing** *(likelihood: medium, impact: medium)*: Multi-page checks can exceed naive timeouts; source-aware bounded budgets and deterministic timing tests mitigate it.

## Implementation Signals

- `EXTERNAL-SERVICE` — Canon Asia English RF/RF-S catalogue, product, firmware-fragment, and release-detail pages are the official source chain.
- `NEW-WORKER` — Add one bundled official module executed through the existing extension runner; do not add a separate process or direct HTTP path.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: Every supported fixture yields its expected version and official release link, with zero false positives or negatives.
- **SC-002** [US2]: Every accessory, unrelated mount, near-name, unknown, no-firmware, drift, denied, timeout, and cancellation fixture produces the expected visible unsuccessful outcome and no successful version.
- **SC-003** [US3]: Deterministic concurrent and retry checks prove at least 30 seconds between Canon-origin attempts and zero outbound requests after timeout or cancellation.
- **SC-004** [US1]: Repeated startup seeding yields exactly one selectable Canon RF Lenses module, and both version search and normal check execution require only a model name.
- **SC-005** [US2]: RF-S catalogue support is demonstrated by an explicit no-firmware fixture without any positive RF-S release assertion.

## Glossary

| Term | Definition |
|------|------------|
| RF catalogue | Canon Asia English support catalogue containing RF lenses and some non-lens accessories. |
| RF-S catalogue | Canon Asia English support catalogue for RF-S products; membership does not imply available firmware. |

## Clarifications

### Session 2026-09-07

- Q: How tolerant should exact model matching be? -> A: Trim surrounding whitespace and compare case-insensitively; reject all other differences.

## Compliance Check

**Status**: PASS

- Unsupported products, unavailable firmware, source drift, denial, timeout, and cancellation remain visible.
- All outbound access uses the centralized client with shared source pacing and cancellation boundaries.
- No external state, service dependency, sandbox claim, or source-layout violation is introduced.
- Fixture correctness, strict typing, and zero false-positive/negative expectations are required.
