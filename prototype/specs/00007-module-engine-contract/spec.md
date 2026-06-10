---
feature_branch: "00007-module-engine-contract"
created: "2026-05-31"
input: "E006 Module Engine & Contract"
spec_type: "technical"
spec_maturity: "clarified"
epic_id: "E006"
epic_sources: "{PRD:CAP-002}, {SAD:ADR-0005}"
---

# Feature Specification: Module Engine & Contract

**Feature Branch**: `00007-module-engine-contract`  
**Created**: 2026-05-31  
**Status**: Draft  
**Spec Type**: technical  
**Spec Maturity**: clarified  
**Epic ID**: E006  
**Epic Sources**: {PRD:CAP-002}, {SAD:ADR-0005}  
**Product Document**: specs/prd.md

## Problem Statement

Binocular needs a stable extension-module foundation so firmware-checking intelligence can live outside the core app. Without a contract, loader, validation pipeline, and invocation boundary, one broken module could crash or stall unattended checks.

## Scope

### Included

- Python authoring contract, importlib loader, async runner, two-phase validation, module metadata persistence, and unsandboxed trust-boundary documentation.

### Excluded

- Upload/update/delete UI and public lifecycle endpoints — E008.
- Version comparison and check-result business logic — E009.
- Starter modules and fixtures — E015.
- Sandboxing or permission enforcement — out of scope for v1.

### Edge Cases & Boundaries

- Missing files, syntax/import failures, missing members, invalid outputs, ScrapeClient failures, `Exception`, `SystemExit`, and timeouts become structured failures.
- Validation is a contract gate, not a sandbox.

## Technical Objectives

### Objective 1 - Stable Contract And Loader (Priority: P1)

Define the authoring contract and load modules through explicit importlib path loading.

**Why this priority**: P1 because lifecycle, checking, and starter-module epics depend on it.

**Rationale**: One durable interface and one normalized import/contract boundary.

**Deliverables**: Contract docs, typed models/protocols, loader service.

**Validation Criteria**:
1. **Given** a valid module, **When** loaded, **Then** metadata and entrypoint info return.
2. **Given** invalid syntax or missing members, **When** loaded, **Then** structured failure returns.

### Objective 2 - Invocation Boundary (Priority: P1)

Run each module invocation behind an async timeout boundary.

**Why this priority**: P1 because broken or hanging modules must not crash or stall the core.

**Rationale**: Unsandboxed in-process failures must be contained.

**Deliverables**: Async runner, ScrapeClient injection, configurable timeout, failure mapping.

**Validation Criteria**:
1. **Given** a raising module, **When** invoked, **Then** failure detail returns and the core remains available.
2. **Given** a slow module, **When** invoked, **Then** timeout failure returns and later invocations run.

### Objective 3 - Two-Phase Validation (Priority: P1)

Validate modules before lifecycle consumers save or activate them.

**Why this priority**: P1 because E008 needs phase-specific rejection feedback before installation.

**Rationale**: Static checks catch shape problems; runtime proof catches execution failures.

**Deliverables**: Static validator, optional runtime proof, per-phase result model.

**Validation Criteria**:
1. **Given** invalid syntax, **When** validation runs, **Then** static fails and runtime is skipped.
2. **Given** invalid runtime output, **When** proof runs, **Then** runtime fails with phase findings.

### Objective 4 - Module Metadata Persistence (Priority: P2)

Persist module identity, source path, lifecycle status, and latest validation summary.

**Why this priority**: P2 because engine execution can work without UI lifecycle flows, but E008 needs durable state.

**Rationale**: Later workflows need a durable module list without importing every module per request.

**Deliverables**: Migration, repository methods, validation-state service integration.

**Validation Criteria**:
1. **Given** validation metadata, **When** persisted, **Then** later reads return identity, path, status, and summary.
2. **Given** failed validation, **When** status updates, **Then** stored state reflects failure.

### Technical Constraints

- Backend code must live under `backend/src/` and pass Ruff plus `mypy --strict`.
- Use raw parameterized SQL and append-only numbered migrations; no ORM.
- Modules must use the host-provided ScrapeClient for outbound fetches.
- Do not claim sandboxing; document unsandboxed arbitrary-code execution plainly.

## Integration Points

- **IP-001**: E008 depends on validation to accept/reject uploaded modules before installation.
- **IP-002**: E009 depends on the runner for normalized module output or failure detail.
- **IP-003**: E015 depends on the authoring contract and validation result model.
- **IP-004**: The engine depends on E007 ScrapeClient as the only module outbound HTTP capability.
- **IP-005**: Metadata persistence depends on the E004 migration runner and raw-SQL repository base.

## Requirements

### Technical Requirements

- **TR-001**: System MUST define and document a stable Python module authoring contract with required metadata, async entrypoint, check input, ScrapeClient parameter, and normalized output.
- **TR-002**: System MUST load module files from the configured modules directory using explicit importlib path loading and return structured failures for syntax, import, and missing-contract errors.
- **TR-003**: System MUST inject the host-owned ScrapeClient into module execution and MUST NOT expose an alternate outbound request path as part of the module contract.
- **TR-004**: System MUST wrap each module invocation in an async timeout boundary and convert timeout, `Exception`, `SystemExit`, ScrapeClient errors, and invalid outputs into structured failed results.
- **TR-005**: System MUST preserve host cancellation semantics and MUST NOT report framework cancellation or process interruption as a module-contained failure.
- **TR-006**: System MUST provide two-phase validation with phase-labeled static and optional runtime proof results.
- **TR-007**: System MUST skip runtime validation when static validation fails and include actionable phase findings.
- **TR-008**: System MUST persist module metadata and latest validation summary through SQLite using raw parameterized SQL and numbered migrations.
- **TR-009**: System MUST document that modules are trusted, unsandboxed, in-process Python code with full application privileges.

### Key Entities

- **Module**: Python file plus metadata, source path, lifecycle status, and latest validation summary.
- **ModuleMetadata**: Contract identity fields such as module ID, display name, supported device hints, author, and version.
- **ModuleCheckInput**: Runtime context passed by future check workflows.
- **ModuleCheckResult**: Normalized output or failure detail returned to detection workflows.
- **ModuleValidationResult**: Per-phase status with findings, duration, error type/message, and optional runtime proof output.

## Assumptions & Risks

### Assumptions

- Modules are Python source files stored on the configured modules volume.
- Module authors can target an async Python contract and use the host ScrapeClient.
- E008 owns user-facing lifecycle flows and calls this engine before installing uploaded source.
- E009 owns version comparison after normalized output returns.
- Operators accept the explicit unsandboxed trust boundary.

### Risks

- **Unsandboxed behavior** *(likelihood: medium, impact: high)*: A module can execute arbitrary Python; mitigation is docs, non-root container posture, and operator vetting.
- **Strict validation** *(likelihood: medium, impact: medium)*: Static checks may reject legitimate modules; mitigation is narrow checks and phase findings.
- **Timeout cleanup** *(likelihood: medium, impact: medium)*: `asyncio.wait_for` may not stop side effects instantly; mitigation is clear semantics and tests.

## Implementation Signals

- `NEW-ENTITY` — Module metadata and validation summary records.
- `MIGRATION` — Append-only SQLite migration for module metadata.
- `NEW-API` — Internal loader, validator, and runner service APIs.
- `EXTERNAL-SERVICE` — Host ScrapeClient injected into modules as the sole outbound dependency.
- `NEW-CONFIG` — `modules_dir` defaulting to `modules/` and invocation timeout defaulting to 10 seconds.
- `NEW-WORKER` — Async runner executes module invocations with timeout boundaries.

## Success Criteria

### Measurable Outcomes

- **SC-001** [OBJ1]: A valid sample module loads with normalized metadata in automated tests.
- **SC-002** [OBJ1]: Invalid syntax, import failure, and missing entrypoint cases produce structured failures in automated tests.
- **SC-003** [OBJ2]: Raising and timeout sample modules are contained by the runner and do not prevent a subsequent valid invocation.
- **SC-004** [OBJ3]: Static-fail, static-pass/runtime-fail, and full-pass validation paths return phase-labeled results in automated tests.
- **SC-005** [OBJ4]: Module metadata and latest validation summary persist across repository writes and reads using migrations.
- **SC-006** [OBJ2]: Contract documentation explicitly states that modules are unsandboxed and trusted.

## Clarifications

### Session 2026-05-31

- Q: Default module directory? -> A: `modules/`, configurable.
- Q: Default invocation timeout? -> A: 10 seconds, configurable.

## Glossary

| Term | Definition |
|------|------------|
| Authoring Contract | Python interface a module implements for load, validation, and invocation. |
| Runtime Proof | Optional validation using sample input. |
| Static Validation | AST, compile/import, metadata, and entrypoint checks. |
| Unsandboxed Module | Python code run in-process with app privileges and no isolation. |

## Compliance Check

**Result**: PASS

- Project instructions satisfied: explicit trust boundary, SQLite-only persistence, ScrapeClient-only outbound access, source-root policy, strict typing expectation.
