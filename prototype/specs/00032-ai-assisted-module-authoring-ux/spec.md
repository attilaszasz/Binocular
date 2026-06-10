---
feature_branch: "00032-ai-assisted-module-authoring-ux"
created: "2026-06-09"
input: "AI-assisted module authoring UX: in-UI guidance section, downloadable AI Module Kit with contract reference/template/example/AI prompt, and AI-friendly validation error copy-paste on upload failure."
spec_type: "product"
spec_maturity: "clarified"
epic_id: "E031"
epic_sources: "{PRD:CAP-013}{PRD:CAP-003}"
---

# Feature Specification: AI-Assisted Module Authoring UX

**Feature Branch**: `00032-ai-assisted-module-authoring-ux`
**Created**: 2026-06-09
**Status**: Draft
**Spec Type**: product
**Spec Maturity**: clarified
**Epic ID**: E031
**Epic Sources**: {PRD:CAP-013}{PRD:CAP-003}
**Product Document**: specs/prd.md

## Problem Statement

Creating a Binocular extension module today requires reading external documentation, understanding the authoring contract, and manually diagnosing validation errors. Module authors who use AI coding tools (ChatGPT, Claude, Cursor, etc.) must hand-assemble context from scattered docs and manually reformat validation errors before pasting them into their AI tool. This friction discourages module creation and slows the edit-validate-fix loop, limiting the ecosystem to technically confident authors who can navigate the contract independently.

## Scope

### Included

- A prominent "Create a Module" guidance section on the Modules page explaining what modules are, how AI-assisted authoring works, and a brief step-by-step flow
- A downloadable AI Module Kit served as static files by the backend, containing: authoring contract reference, starter template, working example module, and structured AI instructions file
- Individual file downloads for each kit component plus a single .zip bundle download
- A "Copy errors for AI" button on the ValidationSummary component that copies a pre-formatted, AI-friendly error block to the clipboard
- Backend API endpoint(s) at `/api/v1/module-kit/` to serve kit files

### Excluded

- In-app AI chat or inline AI editing — the kit is designed for use in external AI tools
- Module marketplace or community sharing — out of scope per product principles
- Changes to the existing module validation logic or error codes — only the presentation/copy format changes
- New backend dependencies — uses only stdlib (`zipfile`, `pathlib`) and existing FastAPI capabilities

### Edge Cases & Boundaries

- Kit files must be self-contained: usable without the running Binocular app or its full source tree
- If kit files are missing from the filesystem (e.g., corrupted install), the guidance section still renders but download links show an appropriate error state
- The "Copy errors for AI" button should handle empty findings gracefully (no clipboard write, or a "No errors to copy" message)
- The AI instructions file must be tool-agnostic: no tool-specific syntax (e.g., no XML tags, no special markers)
- The .zip bundle must not exceed a reasonable size limit (kit files are text-only, expected <50 KB total)

## User Scenarios & Testing

### User Story 1 - View Module Creation Guidance (Priority: P1)

An operator visits the Modules page and sees a prominent guidance section explaining what extension modules are, how they work with AI tools, and a brief step-by-step flow (download kit → give to AI → upload result). The section is visible regardless of whether modules are already installed.

**Why this priority**: Core value proposition — without visible guidance, operators don't discover the AI-assisted authoring path and the feature has no utility.

**Independent Test**: Navigate to the Modules page and verify the guidance section is visible with explanatory text and download links.

**Acceptance Scenarios**:

1. **Given** the operator is on the Modules page, **When** the page loads, **Then** a "Create a Module" guidance section is visible above the module list with explanatory content and download actions.
2. **Given** modules are already installed, **When** the operator views the Modules page, **Then** the guidance section remains visible (not hidden by existing modules).

### User Story 2 - Download AI Module Kit (Priority: P1)

An operator downloads the AI Module Kit as individual files or as a single .zip bundle. They hand the kit (or just the AI instructions file) to their preferred AI coding tool, which produces a valid `.py` module file ready for upload.

**Why this priority**: Core value proposition — the kit is the primary deliverable that enables AI-assisted authoring; without it, the guidance section is informational but not actionable.

**Independent Test**: Download the .zip bundle, extract it, and verify it contains the contract reference, starter template, example module, and AI instructions file. Hand the instructions file to an AI tool and confirm it produces a valid module.

**Acceptance Scenarios**:

1. **Given** the operator is on the Modules page, **When** they click a download link for an individual kit file, **Then** the file downloads with the correct content and filename.
2. **Given** the operator clicks the "Download AI Module Kit" bundle link, **When** the download completes, **Then** a .zip file is received containing all four kit components.
3. **Given** an operator hands the AI instructions file to any AI coding tool with no other context, **When** the AI generates a module, **Then** the output is a syntactically valid `.py` file that passes Binocular's static validation phase.

### User Story 3 - Copy Validation Errors for AI (Priority: P1)

When a module upload fails validation, the operator sees a "Copy errors for AI" button on the validation feedback panel. Clicking it copies a pre-formatted error block to the clipboard that includes error codes, messages, the failed phase (static/runtime), and an instruction preamble telling the AI tool to fix the errors.

**Why this priority**: Completes the authoring loop — without copy-paste-friendly errors, AI-assisted iteration requires manual error reformatting, breaking the flow.

**Independent Test**: Upload an invalid module, verify the "Copy errors for AI" button appears, click it, paste into a text editor, and confirm the output contains structured error information with an AI instruction preamble.

**Acceptance Scenarios**:

1. **Given** a module upload has failed validation, **When** the operator clicks "Copy errors for AI", **Then** a structured error block is copied to the clipboard containing error codes, messages, failed phase, and a fix instruction preamble.
2. **Given** validation fails with findings in both static and runtime phases, **When** the operator copies errors, **Then** both phases' findings are included in the copied text.
3. **Given** a module upload succeeds (no validation errors), **When** the operator views the result, **Then** no "Copy errors for AI" button is shown.

### User Story 4 - Collapsible Guidance Section (Priority: P2)

The guidance section can be collapsed/dismissed by the operator to reduce visual noise once they are familiar with the workflow. The collapsed state persists across page navigations within the session.

**Why this priority**: UX polish — enhances the experience for returning users but the feature works without it.

**Independent Test**: Collapse the guidance section, navigate away and back, verify it remains collapsed.

**Acceptance Scenarios**:

1. **Given** the guidance section is expanded, **When** the operator clicks a collapse/dismiss control, **Then** the section collapses to a minimal state.
2. **Given** the guidance section is collapsed, **When** the operator navigates to another page and returns, **Then** the section remains collapsed.

## Requirements

### Functional Requirements

- **FR-001**: System MUST display a "Create a Module" guidance section on the Modules page with explanatory content about AI-assisted module authoring.
- **FR-002**: System MUST serve AI Module Kit files at `/api/v1/module-kit/` as individual downloads (contract reference, starter template, example module, AI instructions).
- **FR-003**: System MUST serve a .zip bundle of all kit files at `/api/v1/module-kit/bundle`.
- **FR-004**: System MUST display a "Copy errors for AI" button on the ValidationSummary component when validation findings exist.
- **FR-005**: System MUST copy a pre-formatted error block to the clipboard including: error codes, messages, failed phase (static/runtime), and an AI fix instruction preamble.
- **FR-006**: System MUST render the guidance section using shadcn/ui components consistent with the existing Modules page design (E030).
- **FR-007**: System MUST serve kit files without adding new backend Python dependencies beyond stdlib.
- **FR-008**: The AI instructions file in the kit MUST be tool-agnostic, producing valid modules when used with any AI coding tool.

### Key Entities

- **AI Module Kit**: A collection of static text files (contract reference, starter template, example module, AI instructions) served by the backend and downloadable from the Modules page. The kit is self-contained and designed for use with external AI tools.
- **ValidationSummary**: Existing frontend component (in ModulesPage.tsx) that displays per-phase validation findings. Extended with a "Copy errors for AI" clipboard action.

## Assumptions & Risks

### Assumptions

- The existing `docs/modules-authoring-guide.md` content is the authoritative source for the contract reference kit file.
- The existing `sony_alpha.py` official module serves as a suitable working example for the kit.
- Operators using AI tools are comfortable with a copy-paste workflow (download kit → give to AI → upload result).
- The Clipboard API (`navigator.clipboard.writeText`) is available in supported browsers.

### Risks

- **AI output quality varies by tool** *(likelihood: medium, impact: medium)*: Different AI tools may interpret the instructions file differently, producing modules of varying quality. Mitigation: the two-phase validation catches invalid modules before they enter the system.
- **Kit content staleness** *(likelihood: low, impact: medium)*: If the authoring contract changes, the kit files must be updated manually. Mitigation: kit files are derived from the existing contract and authoring guide, which are already maintained.

## Implementation Signals

- `NEW-API` — Backend endpoints at `/api/v1/module-kit/` for individual file serving and .zip bundle generation
- `NEW-UI` — "Create a Module" guidance section on the Modules page with download links and step-by-step flow
- `NEW-UI` — "Copy errors for AI" button on the ValidationSummary component with clipboard integration
- `NEW-CONFIG` — Static kit files stored in the backend source tree (e.g., `backend/src/binocular/module_kit/`)

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: The Modules page displays the guidance section with explanatory content and download actions on every page load.
- **SC-002** [US2]: All four kit files are downloadable individually and as a .zip bundle from the Modules page.
- **SC-003** [US2]: Handing the AI instructions file (alone) to an AI tool produces a `.py` file that passes Binocular's static validation phase.
- **SC-004** [US3]: After a failed module upload, clicking "Copy errors for AI" places a structured error block on the clipboard containing all validation findings with error codes, phases, and an AI instruction preamble.
- **SC-005** [US4]: The guidance section collapse state persists across in-session page navigations.

## Glossary

| Term | Definition |
|------|------------|
| AI Module Kit | A downloadable bundle of reference files (contract, template, example, AI instructions) that enables AI coding tools to produce valid Binocular extension modules. |
| AI instructions file | A structured prompt file within the kit that provides an AI coding tool with all context needed to generate a valid module, without requiring access to the Binocular codebase. |
| ValidationSummary | The frontend component that displays per-phase (static/runtime) validation findings when a module upload fails. |

## Clarifications

### Session 2026-06-09

- Q: Should the AI instructions file be plain text (.txt), Markdown (.md), or something else? -> A: Markdown (.md) — most AI tools handle Markdown natively and it allows structured headings.
- Q: Should the guidance section appear above or below the upload form? -> A: Between the header/upload form and the module list — visible but doesn't push existing content below the fold.
- Q: What visual feedback should the user see after clicking "Copy errors for AI"? -> A: Brief inline confirmation ("Copied!") — standard clipboard UX pattern.

## Compliance Check

Verified against `project-instructions.md`:
- **I. Honest Failure**: Kit download failures surface visibly; validation errors are never hidden. ✅
- **II. Polite by Default**: No outbound scraping involved in this feature. ✅
- **III. Data Ownership**: No external services, accounts, or telemetry. Kit files are local static content. ✅
- **IV. Least-Privilege**: Trust boundary documentation preserved; modules remain unsandboxed and this is communicated in the guidance section. ✅
- **V. Type Safety**: Backend endpoints will pass `mypy --strict`; frontend components will pass `tsc` strict. ✅
- **VI. Set-and-Forget**: Kit files are bundled with the image; no configuration required. ✅
- **VII. Agent Output Style**: N/A (product feature, not agent output). ✅
- **Source Layout**: Kit files under `backend/src/`; frontend components under `frontend/src/components/modules/`. ✅

**Result**: PASS — no violations detected.
