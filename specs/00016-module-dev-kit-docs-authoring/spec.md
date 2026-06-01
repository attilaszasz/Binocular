---
feature_branch: "00016-module-dev-kit-docs-authoring"
created: "2026-06-01"
input: "E017 Module Dev Kit & Docs — authoring guide + standalone test harness"
spec_type: "product"
spec_maturity: "clarified"
epic_id: "E017"
epic_sources: "{PRD:CAP-013}"
product_document: "specs/prd.md"
---

# Feature Specification: Module Dev Kit & Docs

**Feature Branch**: `00016-module-dev-kit-docs-authoring`  
**Created**: 2026-06-01  
**Status**: Clarified  
**Spec Type**: product  
**Spec Maturity**: clarified  
**Epic ID**: E017  
**Epic Sources**: {PRD:CAP-013}  
**Product Document**: specs/prd.md

## Problem Statement *(mandatory)*

Developing extension modules for Binocular currently requires running the full application stack, uploading modules via the UI, and checking logs to debug issues. This workflow is slow, frustrating, and risky because unsandboxed module code must be imported and run directly in the application container to verify correctness. Providing comprehensive authoring documentation and a standalone local test/validation harness enables developers to create, debug, and fully validate their modules locally, safely, and instantaneously without running the main application container.

## Scope *(mandatory)*

### Included

- **Comprehensive Authoring Guide**: A Markdown document (`docs/modules-authoring-guide.md`) containing the extension model schema, the exact `MODULE_METADATA` structures, detailed API specs for `check_firmware` and the host-provided polite `ScrapeClient` (including its methods, inputs, and custom scrape errors), best practices, and copy-pasteable working templates.
- **Standalone CLI Test Harness**: A command-line utility (runnable via `python -m binocular.extensions.devkit`) that operates independently of the web application.
- **Parity Validation**: The dev kit MUST use the exact same static and runtime validation logic as the backend engine (including `ModuleLoader`, `ModuleValidator`, and `ModuleRunner` where possible, or an absolute functional equivalent).
- **Local Runtime Proof Execution**: The ability to run the module's `check_firmware` async entrypoint against a real URL, or a local file/mock source, returning the structured results and timing diagnostics to the terminal.
- **Polite Scraping Simulation**: Injecting a mock or local-only polite client that respects robots.txt (or accepts a simulated override), and supports rate limit / backoff simulation.

### Excluded

- **In-App Web Code Editor**: Users edit code in their local IDE, not in the Binocular web UI.
- **Sandbox/Isolation Layer**: Extension modules still execute unsandboxed with the user's host/CLI process privileges.
- **Automated Extension Marketplace / Directory**: Local-only file management; no global repository of extensions is created or managed.

### Edge Cases & Boundaries

- **Broken Syntax / Imports**: The harness must gracefully catch syntax errors, compile errors, and missing dependencies, outputting clear diagnostic errors instead of raw interpreter tracebacks.
- **Non-coroutine or Missing Entrypoints**: Handled explicitly by the loader and reported as static validation failures.
- **Network Timeouts & Exceptions**: Run failures in `check_firmware` (e.g., `httpx` connection issues or unhandled module exceptions) must be caught by an error boundary and mapped to clear failure findings with last-success timestamps if applicable.

## User Scenarios & Testing *(mandatory for product specs only)*

### User Story 1 - Local Static Validation (Priority: P1)

As a module author, I want to run a quick terminal command to check if my module meets the basic contract requirements (correct syntax, metadata fields, and async entrypoint) so that I know it won't be rejected immediately upon upload.

**Why this priority**: Core value proposition — without static contract validation, there is no way to verify that a module matches the core load requirements without deploying it into a running app instance.

**Independent Test**: Running `python -m binocular.extensions.devkit check path/to/my_module.py` against a syntactically invalid file outputs a static check verdict of `failed` with exact line numbers and error details.

**Acceptance Scenarios**:

1. **Given** a module file with correct syntax, `MODULE_METADATA` mapped with `module_id` and `display_name`, and an async `check_firmware` function, **When** I run the dev kit CLI, **Then** the static phase returns `passed`.
2. **Given** a module file with missing `MODULE_METADATA`, **When** I run the dev kit CLI, **Then** the static phase returns `failed` with a finding `missing_metadata`.

### User Story 2 - Local Runtime Execution (Priority: P1)

As a module author, I want to execute my module's scraper logic against a real target page or mock input and see the extracted version side by side with scrape diagnostics, without launching the core web application.

**Why this priority**: Core utility for debugging scraper logic — it is impossible to build correct scraper modules without running them against the page to verify parsing accuracy.

**Independent Test**: Running `python -m binocular.extensions.devkit run path/to/module.py --device-type "camera" --model "Alpha 7 IV" --current-version "1.00" --url "http://localhost:8000/fixture.html"` runs the module's `check_firmware` and outputs the returned `latest_version` and scrape status.

**Acceptance Scenarios**:

1. **Given** a valid module, **When** I execute the dev kit run command with device properties and a target URL, **Then** it fetches the page using the polite scrape client, invokes `check_firmware`, and prints the parsed `latest_version`, status, and execution duration.
2. **Given** a module that throws an unhandled exception inside `check_firmware`, **When** I run the dev kit command, **Then** the error boundary catches it and prints a clean failure summary with `error_type` and error message without crashing the CLI.

### User Story 3 - Standalone Authoring Documentation (Priority: P1)

As a developer, I want to read a single, comprehensive guide that defines the module interface, ScrapeClient capabilities, and error types, with a functional starter template so I can write my own module in minutes.

**Why this priority**: Essential developer onboarding and guidance.

**Independent Test**: Opening `docs/modules-authoring-guide.md` reveals documented schemas for inputs, outputs, ScrapeClient methods, and copy-pasteable boilerplates.

**Acceptance Scenarios**:

1. **Given** a new developer with no prior knowledge of the codebase, **When** they read `docs/modules-authoring-guide.md`, **Then** they find clear code blocks representing `check_firmware(input, scrape_client)`, `MODULE_METADATA`, and how to catch `RobotsDeniedError` or `ScrapeTimeoutError`.

## Integration Points *(mandatory for technical and operational specs)*

- **IP-001**: The Dev Kit CLI relies on `binocular.extensions.loader.ModuleLoader` and `binocular.extensions.validator.ModuleValidator` to ensure 100% parity with the production application validation rules.
- **IP-002**: The Dev Kit runtime runner interacts with `binocular.scraping.client.ScrapeClient` to provide a polite HTTP client to the executing module.

## Requirements *(mandatory)*

### Functional Requirements *(product specs only)*

- **FR-001**: The Dev Kit MUST be a command-line tool runnable as `python -m binocular.extensions.devkit`.
- **FR-002**: The CLI tool MUST provide a `check` command to validate a module statically.
- **FR-003**: The CLI tool MUST provide a `run` command to run the module's `check_firmware` function and output the latest detected version, diagnostics, and scraper timing.
- **FR-004**: The `run` command MUST accept `--device-type`, `--model`, `--current-version`, and optionally `--url` and `--extra` arguments (as a comma-separated key=value list or JSON string) to construct the standard `ModuleCheckInput`.
- **FR-005**: The `run` command MUST initialize a real `ScrapeClient` with default settings (identifiable User-Agent, timeout, rate limits) to inject into the module, allowing real network testing.
- **FR-006**: The documentation MUST be written to `docs/modules-authoring-guide.md` and cover the exact imports, Pydantic inputs/outputs, `ScrapeClient` method definitions (`fetch`), robots.txt behavior, rate-limiting constraints, and error mappings.

### Key Entities *(include for product or technical specs if feature involves data)*

- **ModuleCheckInput**: Input entity representing the current state of a device (device type, model, recorded current version, page URL).
- **ModuleCheckResult**: Output entity containing the run status (success or failed), detected latest version, detail string, final URL, and typed diagnostics.

## Assumptions & Risks *(mandatory)*

### Assumptions

- Developers have Python 3.13 installed locally on their machine.
- Developers have internet access if they test modules against real manufacturer sites using the Dev Kit CLI.
- The dev kit is run from the project root directory or with standard pythonpath set.

### Risks

- **[Scraper block risk during local testing]** *(likelihood: medium, impact: low)*: Developers running frequent local tests might get temporarily rate-limited or blocked by target domains. Mitigated by highlighting this in the authoring guide and encouraging local mock fixtures.
- **[Parity discrepancy]** *(likelihood: low, impact: high)*: Updates to the in-app loader/runner are not reflected in the dev kit. Mitigated by directly reusing the core loader and validator modules in the CLI code.

## Implementation Signals *(mandatory)*

- `NEW-UI` — None, this is a CLI-only developer tool.
- `NEW-API` — None, CLI tool operates entirely on local scripts.
- `NEW-WORKER` — The dev kit CLI script `backend/src/binocular/extensions/devkit.py` containing the main entrypoint and CLI argument parser.
- `NEW-CONFIG` — None.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** [US1]: Running `python -m binocular.extensions.devkit check` on a valid module file prints a successful static validation verdict and returns exit code 0.
- **SC-002** [US1]: Running `python -m binocular.extensions.devkit check` on an invalid module file prints the exact error findings (such as missing metadata or syntax error) and returns exit code 1.
- **SC-003** [US2]: Running `python -m binocular.extensions.devkit run` on a module runs it successfully, outputs a `ModuleCheckResult` dump, and finishes without throwing unhandled CLI crashes.
- **SC-004** [US3]: A comprehensive `docs/modules-authoring-guide.md` document exists and successfully guides a developer to build a valid module.

## Glossary *(include when spec introduces 2+ domain-specific terms)*

| Term | Definition |
|------|------------|
| Static Phase | A validation phase that verifies syntax, compiles the file, loads `MODULE_METADATA`, and checks that the async entrypoint exists. |
| Runtime Phase | A validation phase that executes the module's `check_firmware` async function against real or mocked targets to prove it functions. |
| Dev Kit | The developer-facing CLI harness and documentation for local module authoring and testing. |

## Clarifications

### Session 2026-06-01

- Q: What should be the default test URL or behavior if no custom URL is provided to the run command? -> A: Fetch a pre-defined local mock URL (or return a generic mock HTML structure) to demonstrate parsing without real internet requests.

## Compliance Check

### Instructions Check Report
**Target**: spec.md
**Status**: PASS

| Principle | Verdict | Notes |
|-----------|---------|-------|
| I. Honest Failure | PASS | The spec mandates that scraper failures must be caught by an error boundary and reported with diagnostics rather than silently missing. |
| II. Polite by Default | PASS | The spec requires the dev kit CLI to initialize a polite ScrapeClient and simulates rate limiting/robots checks locally. |
| III. Data Ownership & Self-Containment | PASS | The dev kit runs locally and requires no external DB or servers. |
| IV. Least-Privilege & Explicit Trust Boundary | PASS | The spec explicitly states that extension modules run unsandboxed and details this in the developer docs. |
| V. Type Safety & Correctness-First | PASS | The dev kit relies on backend structures and standard typing, aligning with strict typing principles. |
| VI. Set-and-Forget Reliability | PASS | The dev kit is a standalone script that isolates module execution failures without crashing. |

