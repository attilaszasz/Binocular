---
feature_branch: "00007-module-engine-contract"
created: "2026-06-10"
input: "E007 Module Engine & Contract"
spec_type: "technical"
spec_maturity: "clarified"
epic_id: "E007"
epic_sources: "{PRD:CAP-002}{SAD:ADR-0005}"
---

# Feature Specification: Module Engine & Contract

**Feature Branch**: `00007-module-engine-contract`
**Created**: 2026-06-10
**Status**: Draft
**Spec Type**: technical
**Spec Maturity**: clarified
**Epic ID**: E007
**Epic Sources**: {PRD:CAP-002}{SAD:ADR-0005}
**Product Document**: specs/prd.md

## Problem Statement

Extension modules are the core intelligence layer of Binocular — they contain the device-type-specific logic that knows how to scrape a manufacturer page and return the latest firmware version. Without a formal engine to load, validate, and execute these modules safely, the application cannot perform its primary function of firmware-update detection. The system currently has a placeholder `modules` table (from E006) but no mechanism to discover `.py` files from the modules directory, verify they conform to the authoring contract, or execute them with fault isolation.

## Scope

### Included

- Authoring contract definition: required function signature `check_firmware(url, model, http_client)`, required constants `MODULE_VERSION` and `SUPPORTED_DEVICE_TYPE`
- importlib-based module loader that discovers and loads `.py` files from the configured modules directory
- Per-invocation module runner with host-provided `ScrapeClient` injection, `asyncio.wait_for` timeout enforcement, and `Exception`+`SystemExit` error boundary
- Two-phase validation pipeline: mandatory AST static analysis (Phase 1) and optional runtime execution proof (Phase 2)
- Structured, per-phase validation results with AI-friendly error output
- Database migration to extend the `modules` table with engine-required columns (`version`, `author`, `file_path`, `is_official`, `status`)
- Module repository for CRUD operations on the `modules` table
- Extensions package structure under `backend/src/binocular/extensions/`

### Excluded

- Module upload/delete UI and API — deferred to E009 (Module Lifecycle Management)
- Scheduled or manual check execution — deferred to E012/E013
- Official module implementations — deferred to E011/E016
- Module seeding/auto-registration on startup — deferred to E016
- Module dev kit and AI Module Kit static files — deferred to E019

### Edge Cases & Boundaries

- A `.py` file in the modules directory that does not conform to the contract must be rejected by validation, never loaded for execution
- A module that raises an exception or `SystemExit` during execution must not crash the host process; the error must be captured and returned as a structured failure result
- A module that blocks or hangs must be terminated by the timeout boundary
- A module file with a syntax error must fail gracefully in Phase 1 AST parsing with a clear error message
- Multiple modules with the same `SUPPORTED_DEVICE_TYPE` are permitted (user may have alternatives)
- Protected filenames (underscore-prefixed, e.g. `_sony_alpha.py`) denote official/shipped modules

## Technical Objectives

### Objective 1 - Authoring Contract Definition (Priority: P1)

Define the strict interface contract that every extension module must implement, providing the canonical reference for module authors.

**Why this priority**: Without the contract definition, no module can be validated or executed — it is the foundation of the entire extension system.

**Rationale**: The contract must be narrow and stable (V1) to enable independent module authoring. It defines the exact function signature, required constants, and return types that the engine expects.

**Deliverables**:
- `backend/src/binocular/extensions/contract.py` — contract protocol, return types, constants schema
- `backend/src/binocular/extensions/__init__.py` — public API exports

**Validation Criteria**:
1. **Given** the contract module exists, **When** `mypy --strict` runs, **Then** the contract types pass type checking with no errors
2. **Given** a module author reads the contract, **When** they implement `check_firmware(url, model, http_client)` and define `MODULE_VERSION` and `SUPPORTED_DEVICE_TYPE`, **Then** the module satisfies the structural requirements

### Objective 2 - Module Loader (Priority: P1)

Implement importlib-based discovery and loading of `.py` module files from the configured modules directory into isolated module instances.

**Why this priority**: Loading is the prerequisite for both validation and execution — the engine cannot function without it.

**Rationale**: Uses `importlib.util.spec_from_file_location` for path-based loading without polluting `sys.modules`. Loaded modules are verified for contract conformance before registration.

**Deliverables**:
- `backend/src/binocular/extensions/loader.py` — discovery, loading, contract conformance check

**Validation Criteria**:
1. **Given** a valid `.py` file in the modules directory, **When** the loader discovers it, **Then** it loads the module and verifies contract attributes exist
2. **Given** a non-Python file or directory in the modules path, **When** the loader scans, **Then** it is silently skipped
3. **Given** a `.py` file missing required contract attributes, **When** the loader attempts conformance check, **Then** it returns a structured error indicating which attributes are missing

### Objective 3 - Module Runner with Error Boundary (Priority: P1)

Execute a loaded module's `check_firmware` function with ScrapeClient injection, timeout enforcement, and fault isolation.

**Why this priority**: The runner is the runtime execution path — without it, loaded modules cannot perform firmware checks.

**Rationale**: Per ADR-0005, modules execute unsandboxed in-process. The runner must catch `Exception` and `SystemExit` (never `KeyboardInterrupt`) and enforce timeouts via `asyncio.wait_for`. The host-provided `ScrapeClient` is injected as the `http_client` parameter to enforce polite scraping.

**Deliverables**:
- `backend/src/binocular/extensions/runner.py` — execution wrapper with timeout and error boundary

**Validation Criteria**:
1. **Given** a valid loaded module and a ScrapeClient, **When** `check_firmware` is invoked, **Then** the runner returns the module's result
2. **Given** a module that raises `Exception`, **When** the runner executes it, **Then** the exception is caught and returned as a structured failure result without crashing the host
3. **Given** a module that raises `SystemExit`, **When** the runner executes it, **Then** `SystemExit` is caught and returned as a failure result
4. **Given** a module that hangs beyond the timeout, **When** `asyncio.wait_for` expires, **Then** execution is cancelled and a timeout failure result is returned

### Objective 4 - Two-Phase Validation Pipeline (Priority: P1)

Implement the validation gate that rejects non-conforming modules before they are accepted into the system.

**Why this priority**: Validation prevents malformed modules from silently breaking checks — it is the pre-save quality gate.

**Rationale**: Phase 1 (AST) uses `ast.parse` and `ast.NodeVisitor` to verify structural requirements without executing the code. Phase 2 (runtime proof) optionally executes the module with test inputs. Results are structured per-phase with line numbers and fix suggestions for AI-friendly copy-paste.

**Deliverables**:
- `backend/src/binocular/extensions/validator.py` — AST static validator + optional runtime proof runner
- Structured `ValidationResult` type with per-phase, per-check results

**Validation Criteria**:
1. **Given** a `.py` file with correct contract structure, **When** Phase 1 runs, **Then** all AST checks pass
2. **Given** a `.py` file missing `check_firmware`, **When** Phase 1 runs, **Then** it reports a structured error with the missing function name and expected signature
3. **Given** a `.py` file with a syntax error, **When** Phase 1 attempts `ast.parse`, **Then** it returns a parse error with line number
4. **Given** a valid module and test inputs, **When** Phase 2 runs, **Then** it executes the module and verifies the return type matches the contract
5. **Given** validation results, **When** formatted for output, **Then** they include per-check status, line numbers where applicable, and AI-friendly fix suggestions

### Objective 5 - Module Database Schema & Repository (Priority: P1)

Extend the existing `modules` table with engine-required columns and provide a repository for CRUD operations.

**Why this priority**: The engine needs to persist module metadata (version, author, file path, official status) and query it for loader operations.

**Rationale**: The existing `modules` table (migration 0002) has minimal columns. The engine needs `version`, `author`, `file_path`, `is_official`, and `status` columns to track module lifecycle state.

**Deliverables**:
- `backend/src/binocular/db/migrations/0003_modules_engine.sql` — ALTER TABLE migration
- `backend/src/binocular/extensions/repository.py` — module CRUD repository extending `RepositoryBase`

**Validation Criteria**:
1. **Given** migration 0003 applied to a database with migration 0002, **When** the schema is inspected, **Then** the `modules` table has `version`, `author`, `file_path`, `is_official`, `status` columns
2. **Given** the module repository, **When** a module is created/read/updated, **Then** all fields are correctly persisted and retrieved

### Technical Constraints

- Modules execute unsandboxed, in-process — this is an accepted trust boundary per ADR-0005
- All outbound HTTP from modules must go through the host-provided `ScrapeClient` (ADR-0006)
- Module files live in the configured `modules_dir` path (`/app/modules` by default)
- The contract is V1: `check_firmware(url: str, model: str, http_client: ScrapeClient) -> CheckResult`
- Default module execution timeout: 30 seconds (configurable via `BINOCULAR_MODULE_TIMEOUT`)
- `MODULE_VERSION` (str) and `SUPPORTED_DEVICE_TYPE` (str) are required module-level constants
- Protected (official) modules use underscore-prefixed filenames
- Backend code must pass `mypy --strict`

## Integration Points

- **IP-001**: E002 (Data Layer) provides `RepositoryBase` and migration runner — the module repository extends `RepositoryBase`, and migration 0003 is discovered and applied by the existing runner
- **IP-002**: E005 (Scraping Client) provides `ScrapeClient` — injected into module runner as the `http_client` parameter
- **IP-003**: E006 (Device Inventory) created the initial `modules` table — migration 0003 extends it with engine columns
- **IP-004**: E009 (Module Lifecycle, downstream) will consume `ModuleLoader`, `ModuleValidator`, and `ModuleRepository` for upload/update/delete flows
- **IP-005**: E010 (Update Detection, downstream) will consume `ModuleRunner` to execute firmware checks
- **IP-006**: E011/E016 (Official Modules, downstream) will implement the authoring contract and be validated/loaded by this engine

## Technical Requirements

- **TR-001**: System MUST define a module authoring contract with function `check_firmware(url, model, http_client)` and constants `MODULE_VERSION`, `SUPPORTED_DEVICE_TYPE`
- **TR-002**: System MUST load `.py` modules from the configured modules directory using `importlib.util.spec_from_file_location` without inserting into `sys.modules`
- **TR-003**: System MUST wrap every module execution in an error boundary catching `Exception` and `SystemExit`
- **TR-004**: System MUST enforce per-invocation timeouts via `asyncio.wait_for`
- **TR-005**: System MUST inject the host-provided `ScrapeClient` as the `http_client` parameter to every module invocation
- **TR-006**: System MUST implement Phase 1 AST validation using `ast.parse` and `ast.NodeVisitor` to verify structural contract conformance
- **TR-007**: System MUST implement Phase 2 optional runtime validation that executes the module with test inputs and verifies return types
- **TR-008**: System MUST produce structured validation results with per-phase, per-check status, line numbers, and AI-friendly fix suggestions
- **TR-009**: System MUST extend the `modules` table with `version`, `author`, `file_path`, `is_official`, `status` columns via a numbered migration
- **TR-010**: System MUST provide a module repository with create, read, update, list, and delete operations
- **TR-011**: System MUST pass `mypy --strict` for all new code in `backend/src/binocular/extensions/`

### Key Entities

- **Module**: A registered extension module with metadata (name, device_type, version, author, file_path, is_official, status). Persisted in the `modules` table. Referenced by devices via `module_id` FK.
- **ModuleContract**: The V1 interface specification: `check_firmware(url, model, http_client) -> CheckResult`, `MODULE_VERSION` (str), `SUPPORTED_DEVICE_TYPE` (str).
- **CheckResult**: The return type from `check_firmware` — contains the detected latest version string and optional metadata fields (`release_date`, `download_url`, `release_notes_url`).
- **ValidationResult**: Structured output of the two-phase validation pipeline — per-phase results with per-check status, messages, line numbers, and fix suggestions.
- **Module Status**: Lifecycle state of a registered module — `active` (loaded and operational), `inactive` (disabled by user), or `error` (failed validation).

## Assumptions & Risks

### Assumptions

- The `ScrapeClient` from E005 is available and stable for injection into module runners
- The existing `modules` table from migration 0002 is in production and must be extended non-destructively via ALTER TABLE
- Module authors will target the V1 contract; future contract versions will be backward-compatible or versioned separately
- The modules directory exists and is readable by the application process

### Risks

- **Contract stability** *(likelihood: low, impact: high)*: Changing the V1 contract after modules are authored would break existing modules. Mitigated by keeping the contract narrow and stable.
- **Timeout calibration** *(likelihood: medium, impact: medium)*: Too-short timeouts may kill legitimate slow scrapes; too-long timeouts may hang resources. Mitigated by making timeout configurable with a sensible default.
- **AST validation completeness** *(likelihood: medium, impact: low)*: Static analysis cannot catch all semantic errors. Mitigated by Phase 2 runtime proof for deeper verification.

## Implementation Signals

- `NEW-ENTITY` — Module entity extended with engine columns (version, author, file_path, is_official, status)
- `MIGRATION` — Migration 0003 to ALTER TABLE modules
- `NEW-API` — Extensions package public API (contract, loader, runner, validator, repository)
- `NEW-CONFIG` — Module execution timeout configuration

## Success Criteria

### Measurable Outcomes

- **SC-001** [OBJ1]: The authoring contract is defined as a typed Python module that passes `mypy --strict`
- **SC-002** [OBJ2]: The loader discovers and loads all valid `.py` files from the modules directory and rejects non-conforming files with structured errors
- **SC-003** [OBJ3]: Module execution failures (exceptions, SystemExit, timeouts) are caught by the error boundary and returned as structured results without crashing the host process
- **SC-004** [OBJ4]: Two-phase validation produces per-check structured results with line numbers and fix suggestions suitable for AI-assisted module authoring
- **SC-005** [OBJ5]: Migration 0003 applies cleanly on top of migration 0002 and all module CRUD operations work correctly

## Glossary

| Term | Definition |
|------|------------|
| Authoring Contract | The strict V1 interface that every extension module must implement: `check_firmware` function plus `MODULE_VERSION` and `SUPPORTED_DEVICE_TYPE` constants |
| Error Boundary | The per-invocation fault isolation wrapper that catches `Exception` and `SystemExit` to prevent module failures from crashing the host |
| Two-Phase Validation | Pre-save quality gate: Phase 1 (AST static analysis) checks structural conformance; Phase 2 (runtime proof) optionally executes with test inputs |
| Protected Module | An official/shipped module identified by an underscore-prefixed filename (e.g., `_sony_alpha.py`) |

## Clarifications

### Session 2026-06-10

- Q: What should the default module execution timeout be? -> A: 30 seconds, configurable via `BINOCULAR_MODULE_TIMEOUT` environment variable
- Q: Should CheckResult include metadata beyond the version string? -> A: Yes — optional `release_date`, `download_url`, `release_notes_url` fields
- Q: What status values should the module entity support? -> A: `active`, `inactive`, `error`

## Compliance Check

Verified against `project-instructions.md`:
- **I. Honest Failure**: Module execution failures surface as structured results, never silent — PASS
- **II. Polite by Default**: ScrapeClient injection enforces polite scraping for all modules — PASS
- **III. Data Ownership**: Module metadata persisted in SQLite, no external dependencies — PASS
- **IV. Least-Privilege**: Unsandboxed execution documented as explicit trust boundary — PASS
- **V. Type Safety**: All new code must pass `mypy --strict` — PASS
- **VI. Set-and-Forget**: Broken modules cannot crash the core process — PASS
- **Source Code Layout**: Extensions package under `backend/src/binocular/extensions/` — PASS
