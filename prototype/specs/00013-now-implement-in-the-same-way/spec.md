---
spec_type: product
epic_id: E020
epic_sources:
  - PRD:CAP-011
spec_maturity: clarified
---

# Feature Specification — Official Panasonic Lumix Module

## Problem Statement

Operators need a shipped Panasonic Lumix starter module that works like the official Sony module: immediate firmware-update value plus a reference-quality authoring example. Panasonic Lumix Micro Four Thirds cameras publish firmware on Panasonic's own global support pages, so users should not need to write a custom scraper for common Lumix bodies.

## Scope

### Included

- Official bundled extension module for Panasonic Lumix MFT camera bodies.
- Detection from Panasonic's global DSC firmware index at `https://av.jpn.support.panasonic.com/support/global/cs/dsc/download/index.html`.
- Fixture-backed parsing for model, latest firmware version, release date, and download page URL.
- Matching by exact model and slash-separated aliases, such as `DC-G90`, `DC-G91`, and `DC-G95`.
- Visible module failures when the page cannot be parsed, the device is not listed, or a listed device has no firmware version.
- Documentation that the module is an official authoring template.

### Excluded

- Panasonic lens firmware support; this feature is limited to MFT camera bodies.
- Scraping Alpha Universe for Panasonic firmware versions; that page has Panasonic picker entries but does not expose Panasonic firmware metadata.
- Automatic registration of official modules in production databases; existing module lifecycle storage remains unchanged.

### Edge Cases & Boundaries

- Rows with grouped model names must match each concrete listed alias.
- Version text such as `Ver.1.7` must return normalized latest version `1.7`.
- Download links may be JavaScript handlers and must be resolved to absolute Panasonic URLs when possible.

## User Scenarios & Testing

### US1 [P1] Operator checks a Panasonic MFT body

An operator adds a Panasonic Lumix MFT body with its recorded firmware version and runs the official Panasonic module. The module reports the latest version from Panasonic's support index so the operator can see whether an update is available.

Priority rationale: This is the core product value for the starter module.

Test: Given a fixture row for `DC-GH7` latest `Ver.1.7`, when the operator checks `DC-GH7` at `1.6`, then the result exposes latest version `1.7`.

### US2 [P1] Operator uses a grouped model alias

Panasonic publishes some rows as grouped aliases, for example `DC-G90/G91/G95`. A user who records any one of those concrete model numbers must still get the correct latest firmware.

Priority rationale: Panasonic's source format uses grouped aliases; failing this would miss valid supported cameras.

Test: Given a fixture row `DC-G90/G91/G95` latest `Ver.1.2`, when the operator checks `DC-G91`, then the module returns latest version `1.2`.

### US3 [P2] Module author uses the official module as a template

A module author can inspect the bundled Panasonic implementation and tests to understand responsible scraping, visible failures, and fixture-backed parser coverage.

Priority rationale: CAP-011 requires official modules to provide working value and authoring examples.

Test: Given the repository docs, when a module author opens official module documentation, then Panasonic is described alongside Sony as a trusted starter module.

## Requirements

FR-001: The system MUST ship an official `official.panasonic_lumix_mft_cameras` module implementing the existing extension contract.

FR-002: The module MUST fetch page content only through the injected `ScrapeClient` and MUST NOT import direct HTTP clients.

FR-003: The module MUST parse Panasonic MFT camera body entries from Panasonic's global DSC firmware index fixture, including model, latest version, firmware date, and download page URL when present.

FR-004: The module MUST match slash-separated grouped Panasonic model aliases as distinct supported model keys.

FR-005: The module MUST return visible failure results for an unparseable index, an unlisted model, and a listed model without a firmware version.

FR-006: Official module documentation MUST mention Panasonic Lumix support and the fixture-backed authoring-template expectation.

## Assumptions & Risks

### Assumptions

- Panasonic's global DSC firmware index is the authoritative public source for Lumix MFT body firmware versions.
- MFT body model codes are identifiable by Panasonic `G`, `GH`, `GX`, `GF`, `GM`, and `BGH` family prefixes.
- Existing module runner and version comparison services do not require changes.

### Risks

- Panasonic may change its HTML table or JavaScript download-link format, causing parse failures.
- Some regional Panasonic pages may differ from the global index.
- Alpha Universe's Panasonic picker data may mislead users because it does not include Panasonic firmware metadata.

## Implementation Signals

- EXTERNAL-SERVICE: Panasonic global DSC firmware index is fetched through the central scraping client.
- NEW-ENTITY: New official module file and fixture corpus under existing module/test locations.
- NEW-CONFIG: No new runtime configuration is required.
- NEW-UI: No UI change is required; existing module lifecycle and check surfaces consume the module.

## Success Criteria

SC-001 [US1]: `DC-GH7` fixture checks return latest version `1.7` from a current-version input below that value.

SC-002 [US2]: A grouped source row for `DC-G90/G91/G95` matches `DC-G91` and returns latest version `1.2`.

SC-003 [US3]: Official module documentation identifies Panasonic Lumix as an official starter module and states that fixtures validate parser correctness.

## Glossary

| Term | Definition |
|------|------------|
| MFT | Micro Four Thirds, Panasonic's mirrorless camera system family covered by this feature. |
| Grouped alias | A source row that lists multiple model variants in one cell, such as `DC-G90/G91/G95`. |

## Compliance Check

PASS — Specification follows project instructions and artifact conventions.