---
feature_branch: "00029-official-canon-rf-firmware-modules"
created: "2026-09-06"
input: "Add official modules for Canon RF mount cameras and lenses; find official firmware sources and prepare a detailed plan only."
spec_type: "product"
spec_maturity: "draft"
epic_id: ""
epic_sources: ""
---

# Feature Specification: Official Canon RF Firmware Modules

**Feature Branch**: Proposed `00029-official-canon-rf-firmware-modules`; planning performed on `main`, no branch created.
**Status**: Draft; planning only, implementation not authorized.
**Created**: 2026-09-06
**Spec Type**: product
**Spec Maturity**: draft

## Problem Statement

Canon RF camera and lens owners need official firmware monitoring without finding a firmware URL themselves. Incorrect model matching or silently missing an update would undermine unattended monitoring.

## Scope

### Included

- Two independently selectable, automatically bundled official modules: Canon RF cameras and Canon RF lenses.
- Proposed baseline: EOS R catalogue bodies, RF and RF-S catalogue lenses, using Canon Asia's English support site.
- Model-only discovery, existing manual/scheduled checks and version search, official release-page links, fixture-based validation.
- Minimum centralized scraping changes necessary for compliant pacing and bounded execution without required user configuration.

### Excluded

- Firmware installation, binary downloads, accounts, browser automation and regional fallback.
- DSLR, EOS M, EF/EF-S/EF-M lenses, adapters and extenders.
- Proposed baseline excludes Cinema EOS bodies and cinema-specific lenses until RF-mount classification and sources are verified; this is not a claim of all RF-mount coverage.
- New UI, public API, database schema or module framework.

### Edge Cases & Boundaries

- R5 versus R5 Mark II, R6 versus R6 Mark II, RF versus RF-S, focal-length/aperture variants and lens generations must remain distinct.
- Windows/macOS packages may duplicate one release; OS package dates are not necessarily firmware release dates.
- A known product with explicitly no firmware differs from an unknown model or malformed source.
- Concurrent checks for both modules share one Canon origin and its pacing budget.

## User Scenarios & Testing

### User Story 1 - Monitor Camera Firmware (Priority: P1)

As an EOS R camera owner, I can choose the official camera module and supply my model without researching a URL.

**Why this priority**: Core camera monitoring value, independent of lens support.
**Independent Test**: Use a captured EOS R5 source through version search and a device check.
**Acceptance Scenarios**:

1. **Given** EOS R5 and no URL, **When** firmware is checked against the captured source, **Then** version 2.2.1 and its matching Canon release page are returned.
2. **Given** an ambiguous or unsupported camera name, **When** checked, **Then** a visible failure is returned rather than another body's firmware.
3. **Given** a later matching firmware fixture, **When** the existing check flow runs, **Then** existing update detection operates without Canon-specific UI changes.

### User Story 2 - Monitor Lens Firmware (Priority: P1)

As an RF or RF-S lens owner, I can independently choose the official lens module and check my exact lens model.

**Why this priority**: The second explicitly requested module, independently useful.
**Independent Test**: Check captured RF24-105mm F4 L IS USM firmware and RF-S no-firmware pages.
**Acceptance Scenarios**:

1. **Given** RF24-105mm F4 L IS USM and no URL, **When** checked against the captured source, **Then** version 2.0.7 and its matching Canon release page are returned.
2. **Given** a known RF-S lens with an explicit no-firmware response, **When** checked, **Then** firmware unavailability is visible and no version is invented.
3. **Given** a page mentioning lens compatibility inside camera release notes, **When** checking a lens, **Then** the camera version is not reported as lens firmware.

## Requirements

### Functional Requirements

- **FR-001**: System MUST ship separate camera and lens modules through existing automatic official-module discovery, with correct device types and no required URL.
- **FR-002**: Camera module MUST resolve an exact supported EOS R catalogue model and return its latest published stable firmware, not firmware for a similar body.
- **FR-003**: Lens module MUST resolve exact RF/RF-S catalogue lenses, excluding adapters/extenders and unrelated mounts, and return only lens-specific firmware.
- **FR-004**: Both modules MUST use only verified public official Canon sources, preserve source product links, reject ambiguous matches and avoid worldwide/exhaustive-coverage claims.
- **FR-005**: Results MUST contain a normalized numeric version and matching official release-notes page; optional dates MUST retain their actual source meaning. Duplicate OS packages MUST NOT create different firmware releases.
- **FR-006**: Unknown products, explicit no-firmware results, structural changes, denied access and timeouts MUST produce visible failures through the existing host error flow, never fabricated successful versions.
- **FR-007**: All requests MUST use the injected centralized client, obey applicable robots rules and at least Canon's published 30-second interval, including retries and concurrent camera/lens checks. No disallowed binary-download routes may be scraped.
- **FR-008**: Checks MUST work with zero required configuration under compliant pacing and bounded execution. Timed-out checks MUST NOT continue issuing background requests; unrelated modules MUST retain their existing execution budget.
- **FR-009**: Both modules MUST pass captured-source correctness tests with zero false positives/negatives across the supported fixture matrix, contract/loading tests, integration tests and required strict typing/lint checks before release.
- **FR-010**: Documentation MUST identify source region, supported product families, model examples, date/link semantics, pacing expectations and limitations, including unverified Cinema EOS and positive RF-S firmware coverage.

## Assumptions & Risks

### Assumptions

- Canon Asia English support is the initial regional authority; regional release parity is not assumed.
- Proposed coverage is catalogue-based EOS R plus RF/RF-S lenses, not every camera physically accepting an RF lens.
- Official release detail pages suffice for users to reach firmware instructions; automated binary retrieval is unnecessary.
- Current published numeric stable firmware versions can be compared by integer components; unexpected version syntax fails visibly.

### Risks

- **Source drift** (medium/high): HTML, catalogue taxonomy or regional availability can change; captured fixtures, structural validation and visible errors mitigate.
- **Host readiness** (high/high): Current pacing ignores crawl-delay and the runner defaults to 30 seconds; resolve centralized pacing, timeout and cancellation before module delivery.
- **Coverage gaps** (medium/high): EOS R catalogue omits R5 C and no positive RF-S release was verified; document supported scope rather than infer support.

## Implementation Signals

- `EXTERNAL-SERVICE`: Canon Asia public catalogue, product and model-specific firmware HTML.
- Existing module contract and seeder reused; centralized HTTP pacing and invocation deadline behavior require targeted changes.
- No new persisted entity, API, UI or required user configuration.

## Success Criteria

- **SC-001** [US1]: Every camera success fixture yields the exact expected version and model-specific source link; every camera mismatch fixture fails visibly.
- **SC-002** [US2]: Every lens success fixture yields the exact expected version and source link; unsupported and no-firmware fixtures never report a successful version.
- **SC-003** [US1]: Deterministic concurrent camera/lens tests prove at least 30 seconds between Canon request attempts and no requests after cancellation/deadline.
- **SC-004** [US2]: Both modules load and seed automatically, pass the fixture matrix, strict typing/lint and the project 80% coverage target without new required configuration.

## Clarifications

- Planning assumptions above are proposals, not user-approved scope reductions. Confirm before task generation if Cinema EOS (including R5 C), cinema lenses or extenders are required; broader coverage returns to source research and specification.
- User explicitly requested planning only. Do not create implementation completion or QC markers.
