---
feature_branch: "00033-add-device-module-source-link"
created: "2026-09-07"
input: "E030 Add Device Module Source Link"
spec_type: "product"
spec_maturity: "draft"
epic_id: "E030"
epic_sources: "{PRD:CAP-001}{PRD:CAP-002}{SAD:ADR-0013}"
---

# Feature Specification: Add Device Module Source Link

**Feature Branch**: `00033-add-device-module-source-link`
**Created**: 2026-09-07
**Status**: Draft
**Spec Type**: product
**Spec Maturity**: draft
**Epic ID**: E030
**Epic Sources**: {PRD:CAP-001}{PRD:CAP-002}{SAD:ADR-0013}
**Product Document**: `specs/prd.md`

## Problem Statement

Operators adding a device may not know the exact model spelling expected by a selected extension module. Without a direct path to the module's manufacturer page, they must independently discover the source and risk entering a model the module cannot match. Module authors need an optional way to declare that canonical page without changing firmware-check execution.

## Scope

### Included

- Optional module-level `SOURCE_URL` metadata extracted without invalidating modules that omit it.
- Persistent module source URLs exposed by the modules API and rendered on the Add Device form.
- Canonical source URLs for every bundled official module.

### Excluded

- URL fetching, validation, scraping, or changes to check execution — source metadata is display-only.
- A source link for absent or empty metadata — no link avoids misleading operators.

### Edge Cases & Boundaries

- Existing modules and rows without a source URL remain valid and return/render an empty value.
- A selected module's link opens externally without exposing an opener to the destination.
- Upload and official-seeding update paths replace persisted metadata when a module declaration changes.

## User Scenarios & Testing

### User Story 1 - Locate the Module Source (Priority: P1)

An operator selecting a module while adding a device can open its declared source page and identify the model name to enter.

**Why this priority**: This is the feature's direct user value.

**Independent Test**: Select a module with a source URL and verify that a clickable external link is shown and targets that URL.

**Acceptance Scenarios**:

1. **Given** an Add Device form and a selected module with a persisted source URL, **When** the operator views the module field, **Then** an external link to that URL is available.
2. **Given** a selected module with no source URL, **When** the operator views the form, **Then** no source link is rendered.

### User Story 2 - Declare Source Metadata (Priority: P2)

A module author may declare the canonical source URL while existing module authors can omit it without changing their valid contract.

**Why this priority**: It enables the user experience without breaking the extension ecosystem.

**Independent Test**: Load and validate modules with and without `SOURCE_URL`, then verify their stored API metadata.

**Acceptance Scenarios**:

1. **Given** a valid module declaring `SOURCE_URL`, **When** it is uploaded or seeded, **Then** its declared URL is persisted and returned by the modules API.
2. **Given** a valid module omitting `SOURCE_URL`, **When** it is loaded and validated, **Then** it remains valid with empty source metadata.

## Requirements

### Functional Requirements

- **FR-001**: System MUST accept an optional string module-level `SOURCE_URL` constant and expose its value through module loading.
- **FR-002**: System MUST persist each module's source URL through upload and official-module seeding while preserving existing rows without a value.
- **FR-003**: System MUST include `source_url` in every modules API response.
- **FR-004**: System MUST render a selected module's non-empty source URL as a clickable external link on the Add Device form and render no link when empty.
- **FR-005**: System MUST declare canonical source URLs in every bundled official module.

### Key Entities

- **Module source URL**: Optional canonical manufacturer page metadata declared by an extension module and associated with its persisted module record.
- **SOURCE_URL**: Optional V1 authoring-contract constant supplying module source metadata.

## Assumptions & Risks

### Assumptions

- Bundled modules have a stable canonical index or catalogue page suitable for model lookup.
- Existing database migration infrastructure applies the next numbered migration before repository access.

### Risks

- **Stale source metadata** *(likelihood: medium, impact: low)*: Manufacturer pages can move; module updates can refresh the declaration.
- **Incomplete persistence path** *(likelihood: medium, impact: medium)*: Upload and seeding paths must both be covered by tests.

## Implementation Signals

- `MIGRATION` — nullable `modules.source_url` column.
- `NEW-API` — modules response adds source metadata.
- `NEW-UI` — Add Device form conditionally renders an external source link.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: An operator can open the declared source page from the selected module in the Add Device form.
- **SC-002** [US2]: Modules both with and without source metadata load, validate, persist, and serialize successfully.

## Glossary

| Term | Definition |
|------|------------|
| Source URL | Canonical manufacturer page a module uses as its model lookup source. |
| Extension module | User-managed script that implements Binocular's firmware-checking contract. |

## Compliance Check

PASS — Optional metadata, SQLite-only persistence, and display-only external links preserve project constraints; no direct outbound module requests or trust-boundary changes.
