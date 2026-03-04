---
feature_branch: "00006-module-validation-engine"
created: "2026-03-04"
input: "Feature 2.2 — Module Validation Engine"
---

# Feature Specification: Module Validation Engine

**Feature Branch**: `00006-module-validation-engine`
**Created**: 2026-03-04
**Status**: Draft
**Product Document**: docs/binocular-product-brief.md

## User Scenarios & Testing

### User Story 1 - Validate Module Structure Before Saving (Priority: P1)

When a user uploads a module file, the system analyzes its structure without executing it — confirming valid Python syntax, the required check function with the correct signature, and all mandatory manifest constants. On failure, the user receives specific error messages (missing function, wrong signature, missing constants, syntax error) so they can fix the module.

**Independent Test**: Upload files with various defects and confirm each produces the correct error without executing the file.

**Acceptance Scenarios**:

1. **Given** a valid `.py` file with the required function and manifest constants, **When** static validation runs, **Then** the static phase reports pass.
2. **Given** a `.py` file with a syntax error, missing function, wrong signature, or missing constants, **When** static validation runs, **Then** the static phase reports fail with a per-defect error identifying the category and location.

---

### User Story 2 - Prove a Module Works Against a Real Target (Priority: P2)

After static validation passes, the user provides a test URL and device model. The system executes the module's check function with those inputs and the host-provided HTTP client. If the module returns a valid firmware version string within the time limit, runtime passes. If it throws, returns invalid data, or times out, runtime fails with an explanation.

**Why this priority**: Static validation confirms structure but not behavior. Runtime verification proves the module can reach the target site and extract data.

**Independent Test**: Submit a valid module with a working URL/model and confirm it passes; submit one targeting an unreachable URL and confirm it fails.

**Acceptance Scenarios**:

1. **Given** a module that passed static validation and a valid test URL/model, **When** runtime executes the check function, **Then** the runtime phase reports pass with the version string and elapsed time.
2. **Given** a module that raises an exception, returns invalid data, or exceeds the timeout, **When** runtime executes, **Then** the runtime phase reports fail with the error type and message.
3. **Given** a module that failed static validation, **When** the validation engine processes it, **Then** runtime is skipped (status: skipped) and the overall result is fail.

---

### Edge Cases

- Binary data, non-UTF-8 encoding, or 0-byte file: static validation rejects before parsing (`ENCODING_ERROR`).
- File exceeding the configurable size limit: rejected before any validation.
- Check function defined inside a class or nested function: reported as missing (only top-level definitions count).
- Module calls `sys.exit()` during runtime: caught by error boundary, reported as runtime failure.
- Unreachable test URL or missing dependency (`ImportError`): runtime fails with error details.
- Concurrent validations (e.g., two simultaneous uploads): out of scope for V1 (single-user product). Document as a known limitation.

## Requirements

### Functional Requirements

- **FR-001**: System MUST perform static validation of uploaded `.py` files without executing them — verifying the required check function exists as a top-level definition with the correct signature, and all mandatory manifest constants are present as top-level assignments.
- **FR-002**: Static validation MUST check against the established module interface contract: function `check_firmware(url, model, http_client)` and manifest constants `MODULE_VERSION`, `SUPPORTED_DEVICE_TYPE`. The contract is hard-coded for V1.
- **FR-003**: Static validation MUST report all detected issues (not just the first one) so the user can fix multiple problems in a single pass.
- **FR-004**: Static validation MUST gracefully handle non-Python files, encoding errors, and files exceeding a configurable size limit (default: 100 KB).
- **FR-005**: Runtime validation MUST only proceed if static validation passes; otherwise it MUST be skipped.
- **FR-006**: Runtime validation MUST load the module, invoke its check function with the user-provided test URL, device model, and host-provided HTTP client, and validate the return value contains a non-empty `latest_version` string.
- **FR-007**: Runtime validation MUST enforce a configurable timeout (default: 30 seconds) covering the entire runtime phase (module import + function invocation) and catch all exceptions (including `SystemExit`) during execution, reporting failures without crashing the validation engine.
- **FR-008**: The validation engine MUST return a structured result containing: per-phase status (pass/fail/skipped), per-phase error details, returned version string and elapsed time (if runtime succeeded), and an overall verdict that is pass only when both phases pass.
- **FR-009**: The validation engine MUST be usable independently of the web application layer. It MUST ship a factory function for creating a correctly configured, scraping-compliant HTTP client so standalone callers do not need to construct their own.
- **FR-010**: Runtime verification MUST use a scraping-compliant HTTP client consistent with Principle III. The web layer MAY pass its own pre-configured client; standalone callers MUST use the engine's factory.
- **FR-011**: The validation engine is a pure function — it MUST return a structured ValidationResult and MUST NOT persist results to the database. Persistence is the caller's responsibility.
- **FR-012**: The engine's static validation phase MUST be reusable by the module loader (Feature 00005) at startup/rescan time. Runtime verification runs only during user-initiated upload validation.

### Key Entities

- **Validation Result**: Overall verdict (pass/fail) plus a phase result for static and runtime.
- **Phase Result**: Status (pass/fail/skipped), list of validation errors, and phase-specific metadata (version string, elapsed time).
- **Validation Error**: A structured error with a code from a closed enum and a human-readable message. Valid error codes: `SYNTAX_ERROR`, `MISSING_FUNCTION`, `INVALID_SIGNATURE`, `MISSING_CONSTANT`, `ENCODING_ERROR`, `FILE_TOO_LARGE`, `RUNTIME_EXCEPTION`, `RUNTIME_TIMEOUT`, `INVALID_RETURN_VALUE`. New codes require a spec amendment.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A valid module passes static validation in under 1 second with zero false positives.
- **SC-002**: A defective module is rejected with at least one error per defect, each identifying the category and location.
- **SC-003**: A correct module passes runtime verification and returns the version string and elapsed time.
- **SC-004**: A module that throws, returns invalid data, or times out is reported as a failure — the engine never crashes.
- **SC-005**: The report contains a top-level verdict, per-phase status (pass/fail/skipped), and per-failure error objects with code and message.

## Compliance Check

### Project Instructions Alignment (v1.0.0)

| Principle | Status | Notes |
|---|---|---|
| I. Self-Contained Deployment | PASS | Pure backend utility, no external services or additional ports. |
| II. Extension-First Architecture | PASS | FR-001 enforces contract validation without execution. FR-007 requires error boundaries including `SystemExit`. FR-002 hard-codes the 00005 contract. FR-012 shares static validation with the module loader. |
| III. Responsible Scraping | PASS | FR-010 mandates host-provided HTTP client with central scraping enforcement. |
| IV. Type Safety & Validation | PASS | FR-008 mandates structured typed results. Key entities map to typed models. |
| V. Test-First Development | PASS | Acceptance scenarios with Given/When/Then. Measurable success criteria. Edge cases enumerated. |

**Result**: PASS — No compliance violations detected.

## Clarifications

### Session 2026-03-04

- Q: When the engine runs standalone, who creates the scraping-compliant HTTP client? → A: Engine ships a factory function (`create_compliant_client()`) so both web and standalone callers can obtain a correctly configured client.
- Q: Should 00006 replace, supplement, or share validation logic with 00005's module loader? → A: Shared static core — 00006's static phase becomes the canonical validator called by 00005's loader at startup. Runtime verification runs only at upload time.
- Q: Should error codes be a closed enum, open convention, or free-form? → A: Closed enum of 9 codes (SYNTAX_ERROR, MISSING_FUNCTION, INVALID_SIGNATURE, MISSING_CONSTANT, ENCODING_ERROR, FILE_TOO_LARGE, RUNTIME_EXCEPTION, RUNTIME_TIMEOUT, INVALID_RETURN_VALUE). New codes require spec amendment.
- Q: What scope of configurability for the required contract (FR-002)? → A: Hard-code the 00005 contract for V1. Configurability is YAGNI — only one known consumer pattern exists.
- Q: Should the runtime timeout cover import + invocation, or just invocation? → A: Single timeout covers the entire runtime phase (import + invocation). If importing alone exceeds the limit, it's caught and reported.
- Q: Can multiple validations run in parallel? → A: Out of scope for V1. Single-user product makes concurrent uploads unlikely. Documented as a known limitation.
- Q: Should the engine persist results to the database? → A: No — pure function returning ValidationResult. Persistence is the caller's responsibility, satisfying FR-009 standalone usability.
- Q: Should extra parameters on `check_firmware` (e.g., `*args`, `**kwargs`, defaults) be accepted? → A: No. Exact 3-parameter match required (`url`, `model`, `http_client`). Extra params produce `INVALID_SIGNATURE`.
- Q: Should the static validator check manifest constant value types at the AST level? → A: No — existence-only check. Type verification (must be `str`) is deferred to the runtime phase. Annotated assignments (`AnnAssign` nodes) are accepted alongside plain `Assign`.
- Q: When a syntax error prevents AST walking, can other errors still be reported? → A: No. `ast.parse()` raises `SyntaxError` before any node walking. Only `SYNTAX_ERROR` is reported in that case. FR-003's "all issues" applies within a parseable file.
- Q: What does "location" mean in error messages (SC-002)? → A: Line number when available from the AST node. Syntax errors include line and column from the `SyntaxError` exception. Missing-element errors report "module top level" when no specific line applies.
- Q: What error code applies to a 0-byte file? → A: 0-byte files are rejected during pre-validation as `ENCODING_ERROR` (empty content has no valid Python to parse).
- Q: What does `elapsed_seconds` measure? → A: Wall-clock time for the entire runtime phase — from start of module import through `check_firmware()` return.
