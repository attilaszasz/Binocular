---
feature_branch: "00019-module-dev-kit-ai-assisted-authoring"
created: "2026-06-11"
input: "E019 Module Dev Kit & AI-Assisted Authoring"
spec_type: "product"
spec_maturity: "clarified"
epic_id: "E019"
epic_sources: "{PRD:CAP-013}{PRD:CAP-003}"
---

# Feature Specification: Module Dev Kit & AI-Assisted Authoring

**Feature Branch**: `00019-module-dev-kit-ai-assisted-authoring`
**Created**: 2026-06-11
**Status**: Draft
**Spec Type**: product
**Spec Maturity**: clarified
**Epic ID**: E019
**Epic Sources**: {PRD:CAP-013}{PRD:CAP-003}
**Product Document**: specs/prd.md

## Problem Statement

Module authors who want to add support for a new device type face a cold-start problem: they must reverse-engineer the authoring contract from source code, find a working example, and understand validation error output — all without a guided path. Users who rely on AI coding assistants have no structured way to convey the contract and constraints to their AI tool, forcing manual translation of project-specific knowledge. This friction blocks the extensibility promise that is central to Binocular's value proposition.

## Scope

### Included

- Backend static file serving for the AI Module Kit (contract reference, starter template, working example, structured AI instructions)
- In-UI "Create a Module" guidance section on the Modules page with step-by-step authoring flow and kit download links
- Extraction of the existing inline `formatErrorsForAI` into a reusable shared `copyErrorsForAI` utility module for cross-component reuse
- Standalone test harness documentation for local module development
- Backend endpoint `GET /api/v1/module-kit/` to serve downloadable kit files

### Excluded

- In-app code editor for module authoring — complexity disproportionate to value; authors use their own editor/IDE
- Automated AI-powered module generation within the app — out of scope; the kit is designed to be used with external AI tools
- Module marketplace or registry — explicitly out of scope per PRD
- Changes to the V1 authoring contract itself — contract is stable; this epic documents it, not changes it

### Edge Cases & Boundaries

- Kit files must stay synchronized with the actual contract in `extensions/contract.py` — the contract reference is a documentation artifact, not a code generator
- If the Sony Alpha module (used as working example) changes in a future update, the kit example should be updated accordingly
- The standalone test harness is documentation-only; no new CLI tool or test runner is shipped
- The guidance section must work for both empty-state (no modules) and populated-state (modules exist) Modules page views

## User Scenarios & Testing

### User Story 1 - Download AI Module Kit (Priority: P1)

A module author visits the Modules page and sees a "Create a Module" guidance section. They click "Download AI Module Kit" and receive a bundle of files they can hand directly to their AI coding assistant. The kit contains: a contract reference document, a starter template with annotated placeholders, a working example (based on Sony Alpha), and structured AI instructions that tell the assistant exactly how to produce a valid module.

**Why this priority**: Core value proposition of CAP-013 — enables AI-assisted module creation with zero prior codebase knowledge.

**Independent Test**: Download the AI Module Kit, provide it to an AI coding assistant, and verify the assistant produces a module that passes validation on upload.

**Acceptance Scenarios**:

1. **Given** the Modules page is loaded, **When** the user views the "Create a Module" section, **Then** a "Download AI Module Kit" button is visible and enabled.
2. **Given** the user clicks "Download AI Module Kit", **When** the download completes, **Then** the kit files are available as individual downloads with a "Download All as ZIP" option containing: a contract reference, starter template, working example, and AI instructions file.
3. **Given** a user provides the kit files to an AI assistant with a prompt "Create a module for [device type]", **When** the AI generates a module, **Then** the module passes Phase 1 (AST) validation on upload.

### User Story 2 - In-UI Module Authoring Guidance (Priority: P1)

A module author visits the Modules page and sees a collapsible (accordion-style, expanded by default) "Create a Module" section that explains the authoring process step by step: (1) download the kit or read the contract, (2) write the module using the template, (3) test locally, (4) upload via the form. The section surfaces whether the user prefers AI-assisted or manual authoring.

**Why this priority**: Without visible in-app guidance, the dev kit is undiscoverable — the guidance section is the primary onboarding path (per SAD baseline).

**Independent Test**: Navigate to the Modules page and verify the guidance section renders with numbered steps, download links, and links to the contract reference.

**Acceptance Scenarios**:

1. **Given** the Modules page is loaded, **When** the user scrolls to the guidance section, **Then** a "Create a Module" section is visible with numbered authoring steps.
2. **Given** the guidance section is expanded, **When** the user reads the content, **Then** it includes: a link to download the AI Module Kit, a summary of the contract requirements, and a reference to the standalone test harness.
3. **Given** the user is on a mobile device, **When** the guidance section renders, **Then** it is responsive and readable without horizontal scrolling.

### User Story 3 - Kit File Serving Endpoint (Priority: P1)

The backend serves the AI Module Kit files as static assets at `GET /api/v1/module-kit/`. Each file is individually downloadable. The endpoint lists available kit files with their names and download URLs.

**Why this priority**: Backend serving is the mechanism that enables US1 and US2 — without it, files cannot be downloaded.

**Independent Test**: Call `GET /api/v1/module-kit/` and verify it returns a JSON list of available files with download URLs; verify each file URL returns valid content.

**Acceptance Scenarios**:

1. **Given** the backend is running, **When** `GET /api/v1/module-kit/` is called, **Then** it returns a JSON array listing available kit files with `name` and `url` fields.
2. **Given** the file list includes `STARTER_TEMPLATE.py`, **When** `GET /api/v1/module-kit/STARTER_TEMPLATE.py` is called, **Then** the response body is a valid Python file containing the template content.
3. **Given** the file list includes `AI_INSTRUCTIONS.md`, **When** the file is downloaded, **Then** it contains the contract reference, constraints, and structured prompting guidance.

### User Story 4 - Copy Validation Errors for AI (Priority: P2)

When a module upload fails validation, the user can click "Copy for AI" to copy the structured error output to their clipboard in a format their AI coding assistant can parse and act on. The utility formats errors with check names, line numbers, messages, and fix suggestions as structured markdown.

**Why this priority**: Enhances the AI-assisted iteration loop but is not strictly required for first-time module creation; the kit itself is the primary enabler.

**Independent Test**: Upload an invalid module, verify validation errors appear, click "Copy for AI", paste into a text editor, and confirm the output is structured markdown with check names, line numbers, and fix suggestions.

**Acceptance Scenarios**:

1. **Given** a module upload fails validation, **When** the user clicks "Copy for AI", **Then** the clipboard contains markdown-formatted error output with check name, message, line number, and fix suggestion for each failing check.
2. **Given** the copied error text is provided to an AI assistant, **When** the AI reads the structured output, **Then** the format is unambiguous enough for the AI to identify each error and its location.

### User Story 5 - Standalone Test Harness Documentation (Priority: P2)

The AI Module Kit includes documentation for running a module locally against the real contract. The documentation explains how to invoke `check_firmware` with mock inputs and verify the return shape matches `CheckResult`, without requiring the full Binocular backend to be running.

**Why this priority**: Supports local development workflow but is not blocking for module creation; authors can iterate via upload + validation.

**Independent Test**: Follow the test harness documentation to validate a module locally and confirm it provides a clear pass/fail result.

**Acceptance Scenarios**:

1. **Given** a module author has Python installed, **When** they follow the test harness documentation, **Then** they can validate their module's contract compliance locally without running the Binocular backend.
2. **Given** a module returns an incorrect type from `check_firmware`, **When** the local test harness runs, **Then** it reports the type mismatch with a clear error message.

## Requirements

### Functional Requirements

- **FR-001**: System MUST serve AI Module Kit files as static assets via `GET /api/v1/module-kit/` endpoint.
- **FR-002**: System MUST include a starter template (`STARTER_TEMPLATE.py`) with annotated placeholders conforming to the V1 contract.
- **FR-003**: System MUST include a working example module (`EXAMPLE_MODULE.py`) derived from the Sony Alpha official module.
- **FR-004**: System MUST include structured AI instructions (`AI_INSTRUCTIONS.md`) with contract reference, constraints, template, and prompting guidance.
- **FR-005**: System MUST display a "Create a Module" guidance section on the Modules page with numbered authoring steps and download links.
- **FR-006**: System MUST provide a "Copy for AI" button on validation error output that copies structured markdown to the clipboard.
- **FR-007**: System MUST include standalone test harness documentation in the AI Module Kit.
- **FR-008**: The `GET /api/v1/module-kit/` endpoint MUST return a JSON listing of available kit files with name and download URL.
- **FR-009**: Each kit file MUST be individually downloadable via `GET /api/v1/module-kit/{filename}`.
- **FR-010**: The guidance section MUST be responsive and render correctly on mobile and desktop viewports.

### Key Entities

- **AI Module Kit**: A bundle of static files (starter template, working example, AI instructions, contract reference) served by the backend to enable module authoring with or without AI assistance.
- **Module Guidance Section**: An in-UI component on the Modules page that provides step-by-step authoring guidance and download links for the AI Module Kit.
- **Starter Template**: A minimal, annotated Python file (`STARTER_TEMPLATE.py`) implementing the V1 contract skeleton with placeholder comments.
- **Example Module**: A simplified, well-commented version of the Sony Alpha module (`EXAMPLE_MODULE.py`) serving as a pattern reference.

## Assumptions & Risks

### Assumptions

- The V1 authoring contract (`contract.py`) is stable and will not change during this epic.
- The Sony Alpha module is a representative and instructive example for module authors.
- Module authors have Python installed locally for the standalone test harness.
- AI coding assistants can process structured markdown instructions effectively.

### Risks

- **Contract-documentation drift** *(likelihood: low, impact: medium)*: If the contract changes after the kit is created, the kit files become stale. Mitigated by deriving the kit from the actual contract source.
- **AI instruction effectiveness** *(likelihood: medium, impact: low)*: Different AI assistants may interpret the structured instructions with varying success. Mitigated by testing with at least one major AI coding assistant during validation.

## Implementation Signals

- `NEW-API` — `GET /api/v1/module-kit/` endpoint for kit file listing and individual file serving
- `NEW-UI` — "Create a Module" guidance section component on the Modules page
- `NEW-CONFIG` — Kit static files directory at `backend/src/binocular/module_kit/`

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: A user can download the AI Module Kit from the Modules page and the downloaded files contain all four kit components (template, example, AI instructions, contract reference).
- **SC-002** [US2]: The "Create a Module" guidance section is visible on the Modules page and includes numbered steps with download links.
- **SC-003** [US3]: `GET /api/v1/module-kit/` returns a valid JSON listing and each file is individually downloadable with correct content.
- **SC-004** [US4]: Validation error output can be copied via "Copy for AI" and produces structured markdown with check names, line numbers, and fix suggestions.
- **SC-005** [US5]: The test harness documentation enables local module validation without the running Binocular backend.

## Glossary

| Term | Definition |
|------|------------|
| AI Module Kit | A downloadable bundle of files (template, example, AI instructions, contract reference) that enables module authoring with AI coding assistants. |
| V1 Contract | The stable authoring interface defined in `extensions/contract.py` that every extension module must implement: `check_firmware(url, model, http_client)` → `CheckResult`, plus `MODULE_VERSION` and `SUPPORTED_DEVICE_TYPE` constants. |
| Standalone Test Harness | A documented procedure for validating a module's contract compliance locally using Python, without running the Binocular backend. |

## Clarifications

### Session 2026-06-11

- Q: Should the AI Module Kit be served as individual files or as a single ZIP archive download? -> A: Individual files with a "Download All as ZIP" option.
- Q: Should the guidance section be collapsible (accordion) or always visible? -> A: Collapsible accordion, expanded by default.
- Q: Should the 'Copy for AI' utility be extracted into a shared utility? -> A: Extract to shared utility for cross-component reuse.

## Compliance Check

### Instructions Check Report
**Target**: spec.md
**Status**: PASS

| Principle | Verdict | Notes |
|-----------|---------|-------|
| I. Honest Failure | PASS | Not directly applicable to this feature; no scraping or detection logic. |
| II. Polite by Default | PASS | No outbound scraping in this feature. Kit files reference the polite HTTP client in documentation. |
| III. Data Ownership & Self-Containment | PASS | Kit files are static assets served from the backend; no external dependencies. |
| IV. Least-Privilege & Explicit Trust Boundary | PASS | US2 guidance section references the trust boundary warning already present in the upload form. |
| V. Type Safety & Correctness-First | PASS | Backend endpoint will be typed with mypy strict; frontend will pass tsc strict. |
| VI. Set-and-Forget Reliability | PASS | Static file serving; no runtime state or failure modes. |
| VII. Agent Output Style | N/A | Not an agent output artifact. |

**Violations**: None.
