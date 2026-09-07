---
feature_branch: "00031-official-canon-rf-cameras"
created: "2026-09-07"
input: "E028 Official Canon RF Cameras"
spec_type: "product"
spec_maturity: "clarified"
epic_id: "E028"
epic_sources: "{PRD:CAP-015}{SAD:ADR-0005}{SAD:ADR-0012}"
---

# Feature Specification: Official Canon RF Cameras

**Feature Branch**: `00031-official-canon-rf-cameras`  
**Created**: 2026-09-07  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: clarified  
**Epic ID**: E028  
**Epic Sources**: {PRD:CAP-015}{SAD:ADR-0005}{SAD:ADR-0012}  
**Product Document**: `specs/prd.md`

## Problem Statement

Canon EOS R owners must interpret regional firmware pages themselves. They need a model-only module that identifies firmware for the exact body without false matches or silent misses. Inferred coverage or hidden failures would undermine unattended monitoring.

## Scope

### Included

- One independently selectable, automatically seeded official Canon RF Cameras module.
- Exact model-only lookup against the Canon Asia English EOS R catalogue.
- Catalogue-to-product-to-firmware-action discovery using source-provided links and actions.
- OS-package deduplication, normalized versions, and official release-detail links.
- Captured-source correctness and integration coverage for success and failure paths.

### Excluded

- Canon RF/RF-S lenses — owned by E029 as an independently selectable module.
- Cinema EOS and EOS R5 C — absent from the verified EOS R catalogue flow and therefore unsupported until separately verified.
- DSLR, EOS M, other regions, and fallback-region rotation — outside the verified regional catalogue boundary.
- Firmware binary retrieval or installation — detection only.
- New UI, API, schema, or configuration — existing flows are reused.

### Edge Cases & Boundaries

- Similar names such as EOS R5 and EOS R5 Mark II must not cross-match; normalized exact matching may ignore harmless case or surrounding whitespace only.
- Duplicate Windows and macOS packages for the same model and version represent one release.
- An explicit no-firmware response differs from an unknown model or unparseable source, but none may produce a successful version.
- Source drift, denial, deadline exhaustion, and cancellation must remain visible failures.
- Concurrent Canon camera and lens work shares the same Canon-origin 30-second pacing timeline, including retries.

## User Scenarios & Testing

### User Story 1 - Monitor an Exact EOS R Camera (Priority: P1)

As a Canon EOS R owner, I can select the official module and enter my exact model without a firmware URL.

**Why this priority**: Exact model-only firmware discovery is the feature's independently useful core value.

**Independent Test**: Search and check EOS R5 through the captured source chain.

**Acceptance Scenarios**:

1. **Given** captured sources and `EOS R5`, **When** search or check runs, **Then** fixture version `2.2.1` and its official detail URL are returned.
2. **Given** equivalent Windows and macOS packages for EOS R5 version `2.2.1`, **When** releases are interpreted, **Then** one model/version release is selected.
3. **Given** the official module seed is run repeatedly, **When** available modules are listed, **Then** exactly one independently selectable Canon RF Cameras definition is present with no required URL.

### User Story 2 - Receive Honest Unsupported and Source-Failure Outcomes (Priority: P1)

As an operator, I see unsupported models and source failures instead of false firmware results.

**Why this priority**: Honest failure and zero false positives/negatives are mandatory for unattended monitoring.

**Independent Test**: Exercise the unsupported and source-failure fixture matrix.

**Acceptance Scenarios**:

1. **Given** an unknown, near-name, Cinema EOS, or EOS R5 C model, **When** checked, **Then** a visible failure and no version result.
2. **Given** a missing catalogue structure or firmware action, **When** checked, **Then** source drift is surfaced and no stale or inferred result succeeds.
3. **Given** timeout or cancellation during a multi-request flow, **When** the boundary is reached, **Then** the check fails visibly and no later outbound request occurs.

### User Story 3 - Operate Politely Without Configuration (Priority: P2)

As an operator, I use the module without source configuration while requests remain polite and bounded.

**Why this priority**: This safeguards the source and reliability but builds on the P1 discovery and failure behavior.

**Independent Test**: Verify deterministic shared pacing, retries, and cancellation without real sleeps.

**Acceptance Scenarios**:

1. **Given** concurrent Canon camera and lens checks, **When** each issues requests or retries, **Then** all attempts share one Canon-origin timeline with at least 30 seconds between attempts.
2. **Given** no user-supplied URL or Canon setting, **When** a supported model is checked, **Then** the bounded flow completes using official catalogue discovery.

## Requirements

### Functional Requirements

- **FR-001**: System MUST ship one independently selectable Canon RF Cameras module that accepts a model without a URL and seeds idempotently.
- **FR-002**: System MUST resolve only catalogue models equal after trimming surrounding whitespace and case-folding, and MUST reject near-name, ambiguous, Cinema EOS, and EOS R5 C inputs.
- **FR-003**: System MUST follow the catalogue's product link verbatim and discover the firmware form action from that product page rather than construct either route from the model name.
- **FR-004**: System MUST use model-specific firmware content, normalize versions, deduplicate equivalent OS packages, and return the matching release-detail page rather than a binary route.
- **FR-005**: System MUST surface unsupported, no-firmware, source-drift, denial, timeout, and cancellation outcomes visibly without invented or stale versions.
- **FR-006**: System MUST route every outbound request through the host-provided scraping client and share Canon's effective per-origin interval across catalogue, product, firmware, concurrent, and retry requests.
- **FR-007**: System MUST use a bounded source-aware budget, issue no requests after timeout or cancellation, and preserve unaffected-source budgets.
- **FR-008**: System MUST support existing version-search and normal manual/scheduled check execution without new required configuration, UI, API, or persisted state.
- **FR-009**: System MUST validate the officially shipped module against captured fixtures with zero false positives and zero false negatives for the supported matrix, including the EOS R5 `2.2.1` observation and its official detail page.
- **FR-010**: Documentation MUST define the verified region, catalogue boundaries, release semantics, and Cinema EOS/EOS R5 C exclusion.

### Key Entities

- **Canon RF Cameras module**: Official extension definition selected by users and seeded by the application.
- **EOS R catalogue entry**: Exact camera model and source-provided product link within the verified Canon Asia catalogue.
- **Firmware action**: Product-page-discovered official endpoint that returns firmware content for that camera.

## Assumptions & Risks

### Assumptions

- Canon Asia English remains the selected regional authority; parity with other regions is not implied.
- Existing module, seeding, search, check, and error boundaries are available.
- Numeric stable firmware versions can use the existing comparison contract; unexpected syntax fails visibly.
- Captured EOS R5 version data is test evidence and may cease to be the live latest release.

### Risks

- **Source drift** *(likelihood: high, impact: high)*: Each source stage can change independently; structural fixture tests and visible failures mitigate silent misses.
- **Coverage overstatement** *(likelihood: medium, impact: high)*: RF-mount compatibility could be mistaken for verified EOS R catalogue support; exact catalogue boundaries and explicit exclusions mitigate it.
- **Long source pacing** *(likelihood: medium, impact: medium)*: Multi-page checks can exceed naive timeouts; source-aware bounded budgets and deterministic timing tests mitigate it.

## Implementation Signals

- `EXTERNAL-SERVICE` — Canon Asia English catalogue, product, firmware-fragment, and release-detail pages are the official source chain.
- `NEW-WORKER` — Add one bundled official module executed through the existing extension runner; do not add a separate process or direct HTTP path.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: Every supported fixture yields its expected version and official release link, with zero false positives or negatives.
- **SC-002** [US2]: Every unsupported, ambiguous, no-firmware, drift, denied, timeout, and cancellation fixture produces a visible unsuccessful outcome and no successful version.
- **SC-003** [US3]: Deterministic concurrent and retry checks prove at least 30 seconds between Canon-origin attempts and zero outbound requests after timeout or cancellation.
- **SC-004** [US1]: Repeated startup seeding yields exactly one selectable Canon RF Cameras module, and both version search and normal check execution require only a model name.

## Glossary

| Term | Definition |
|------|------------|
| EOS R catalogue | Canon Asia English camera catalogue used as the verified membership boundary for this feature. |
| Firmware action | Official endpoint discovered from a catalogue-linked product page that returns model-specific firmware rows. |

## Clarifications

### Session 2026-09-07

- Q: How tolerant should exact model matching be? -> A: Trim surrounding whitespace and compare case-insensitively; reject all other differences.

## Compliance Check

**Status**: PASS

- Honest failures are explicit for unsupported models, source drift, denial, timeout, and cancellation.
- All outbound access uses the centralized client with shared source pacing and cancellation boundaries.
- No external state, service dependency, sandbox claim, or source-layout violation is introduced.
- Fixture correctness, strict typing, and zero false-positive/negative expectations are required.
