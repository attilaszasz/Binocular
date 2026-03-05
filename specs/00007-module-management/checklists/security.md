# Security & Completeness: Module Management (API & UI)
**Created**: 2026-03-05 | **Feature**: [spec.md](../spec.md)

## Upload Security (OWASP File Upload)

- [X] CHK001 Does the spec restrict accepted file types to an explicit allowlist rather than a blocklist? [Completeness, Spec §FR-001] <!-- Evaluator: Covered by FR-001 ".py files are accepted — other extensions are rejected" -->
- [X] CHK002 Does the filename validation regex prevent path traversal characters (`/`, `\`, `..`), null bytes, and double extensions? [Security, Spec §FR-001] <!-- Evaluator: Covered by FR-001 regex ^[a-zA-Z0-9][a-zA-Z0-9_-]*\.py$ -->
- [X] CHK003 Is the maximum file size limit stated as a formal functional requirement with an explicit enforcement point (before reading full content into memory)? [Completeness, Spec §Edge Cases] <!-- Evaluator: Resolved — added FR-023 to spec.md -->
- [X] CHK004 Does the spec require that invalid files are never written to the production modules directory (temp-first validation pattern)? [Security, Spec §FR-005 / FR-008] <!-- Evaluator: Covered by FR-005/FR-008 + plan.md AD-1 temp-file pipeline -->
- [X] CHK005 Does the spec prevent overwriting existing files — both system and user modules — via the upload path? [Security, Spec §FR-002 / FR-003] <!-- Evaluator: Covered by FR-002 (underscore prefix) + FR-003 (duplicate filename) -->
- [X] CHK006 Is encoding validation (UTF-8 only, reject binary/null bytes) explicitly required before structural validation begins? [Completeness, Spec §Edge Cases] <!-- Evaluator: Covered by Edge Cases "Binary or non-UTF-8 file content: rejected before any validation" -->
- [X] CHK007 Does the spec address whether the upload endpoint inherits existing authentication requirements, or is it accessible without authorization? [Security, Spec §FR-001] <!-- Evaluator: Resolved per user — added Trust Model section to spec.md -->
- [X] CHK008 Are all upload rejection scenarios enumerated with distinct error conditions (wrong extension, invalid filename, duplicate, underscore prefix, size limit, encoding, structural failure, runtime failure)? [Completeness, Spec §FR-010] <!-- Evaluator: Covered by FR-010 + contracts/openapi.yaml examples -->

## Code Execution Risk & Trust Model

- [X] CHK009 Does the spec explicitly define the trust model for uploaded modules (who can upload, what execution risks are accepted)? [Clarity, Spec §Edge Cases] <!-- Evaluator: Resolved per user — added Trust Model section to spec.md -->
- [X] CHK010 Is the "validate without executing" requirement concretely defined as AST-only parsing (no `exec()`, `compile()`, or `eval()`)? [Clarity, Spec §FR-004] <!-- Evaluator: Covered by FR-004 + Feature 00006 spec/plan (AST-based static analysis) -->
- [X] CHK011 Does the spec acknowledge that AST structural validation is not a security sandbox and cannot prevent malicious runtime behavior? [Clarity, Spec §Edge Cases] <!-- Evaluator: Resolved per user — added Trust Model section to spec.md -->
- [X] CHK012 Does the spec address whether uploaded modules can import arbitrary stdlib or third-party modules at runtime? [Completeness, Spec §Edge Cases] <!-- Evaluator: Resolved per user — added Trust Model section to spec.md -->
- [X] CHK013 Is the runtime validation timeout explicitly specified as a functional requirement (not just an edge case)? [Completeness, Spec §US4] <!-- Evaluator: Resolved — added FR-024 to spec.md -->
- [X] CHK014 Does the spec require that runtime validation uses the host-provided HTTP client (enforcing scraping rules) rather than allowing the module to create its own? [Consistency, Spec §FR-006] <!-- Evaluator: Covered by FR-006 "host-provided HTTP client" -->

## System Module Protection

- [X] CHK015 Is the system module identification mechanism (underscore-prefixed filename) consistently defined across both upload rejection and delete rejection requirements? [Consistency, Spec §FR-002 / FR-012] <!-- Evaluator: Covered by FR-002 + FR-012 both reference underscore prefix -->
- [X] CHK016 Does the spec block all write paths to system modules — upload new, overwrite existing, and delete? [Completeness, Spec §FR-002 / FR-003 / FR-012] <!-- Evaluator: Covered by FR-002 (upload), FR-003 (overwrite), FR-012 (delete) -->
- [X] CHK017 Is the protection mechanism a single authoritative rule applied at the API layer, or could it be bypassed through alternative request paths? [Security, Spec §FR-002 / FR-012] <!-- Evaluator: Covered by plan.md AD-4 — API-level enforcement -->
- [X] CHK018 Does the spec define what happens if a system module is manually removed from disk outside the API (e.g., during Reload)? [Completeness, Spec §Edge Cases] <!-- Evaluator: Covered by Edge Cases "deleted from disk outside the API... next Reload or restart will rescan" -->
- [X] CHK019 Does the spec prevent users from uploading a non-underscore-prefixed file that shadows or replaces a system module's functionality? [Security, Spec §FR-003] <!-- Evaluator: Covered by FR-003 duplicate filename rejection —>

## Validation Error Reporting Completeness

- [X] CHK020 Does the spec require that ALL validation errors are reported in a single response (not one-at-a-time)? [Completeness, Spec §FR-005 / SC-002] <!-- Evaluator: Covered by FR-005 + SC-002 -->
- [X] CHK021 Are validation errors required to be grouped by phase (structural vs. runtime) in the response? [Clarity, Spec §FR-010] <!-- Evaluator: Covered by Key Entities "Validation Result" per-phase results + contracts/openapi.yaml -->
- [X] CHK022 Does each error in the response include both a machine-readable code and a human-readable description? [Completeness, Spec §FR-010] <!-- Evaluator: Covered by Key Entities "ValidationError" with code + message -->
- [X] CHK023 Is the error response schema (`ValidationResult` with `PhaseResult` and `ValidationError`) formally defined in the spec or plan? [Completeness, Spec §Key Entities] <!-- Evaluator: Covered by Key Entities + contracts/openapi.yaml schemas -->
- [X] CHK024 Does the spec define the HTTP status code and error envelope format for all rejection categories? [Consistency, Spec §FR-010] <!-- Evaluator: Covered by FR-010 HTTP 400 + contracts/openapi.yaml response examples -->
- [X] CHK025 Are runtime validation failures (exception, timeout, invalid return value) distinguished from structural failures in the error response? [Clarity, Spec §FR-010 / Key Entities] <!-- Evaluator: Covered by ValidationErrorCode enum (RUNTIME_EXCEPTION, RUNTIME_TIMEOUT, etc.) in 00006 data-model -->
- [X] CHK026 Does the spec define the response format for pre-validation rejections (wrong extension, duplicate name) where the validation pipeline was never reached? [Completeness, Spec §FR-010] <!-- Evaluator: Covered by contracts/openapi.yaml examples (validation_result absent for pre-validation rejections) -->

## Frontend Integration & UX Completeness

- [X] CHK027 Does the spec require that the upload area is always visible (not hidden behind a toggle or collapsible panel)? [Clarity, Spec §FR-016] <!-- Evaluator: Covered by FR-016 "always visible above the module list" -->
- [X] CHK028 Are both drag-and-drop AND click-to-browse file selection required, or is one sufficient? [Completeness, Spec §FR-016] <!-- Evaluator: Covered by FR-016 "supports both drag-and-drop and click-to-browse" -->
- [X] CHK029 Does the spec require client-side file extension validation for immediate user feedback before server submission? [Completeness, Spec §FR-016] <!-- Evaluator: Resolved — added FR-025 to spec.md -->
- [X] CHK030 Are upload validation errors required to be displayed inline within the upload form (not as toasts or modals)? [Clarity, Spec §FR-018] <!-- Evaluator: Covered by FR-018 "displayed inline within the upload form" -->
- [X] CHK031 Does the spec require that error messages identify the error type and, where applicable, the location in the file? [Completeness, Spec §FR-018] <!-- Evaluator: Covered by FR-018 "message per error identifying its type and, where applicable, its location" -->
- [X] CHK032 Is the module list auto-refresh requirement defined for both upload success AND delete success scenarios? [Completeness, Spec §FR-020] <!-- Evaluator: Covered by FR-020 "After a successful upload or deletion" -->
- [X] CHK033 Does the spec require a distinct visual treatment for Active vs. Inactive status (color + text + icon, not color alone for accessibility)? [Completeness, Spec §FR-014] <!-- Evaluator: Resolved — amended FR-014 in spec.md -->
- [X] CHK034 Is the inactive module's failure reason accessible without navigating away from the page (tooltip, expandable row, or inline text)? [Clarity, Spec §FR-015] <!-- Evaluator: Covered by FR-015 "tooltip, expandable row, or inline text" -->
- [X] CHK035 Does the delete confirmation UI requirement specify an in-page dialog rather than a browser `confirm()` call? [Clarity, Spec §FR-021] <!-- Evaluator: Resolved — amended FR-021 in spec.md -->
- [X] CHK036 Does the empty state requirement specify both the visual treatment AND the call-to-action content? [Completeness, Spec §FR-022] <!-- Evaluator: Covered by FR-022 + US2 AS3 -->
- [X] CHK037 Are the optional Test URL and Device Model fields required to enforce "both or neither" validation on the client side? [Consistency, Spec §FR-006 / FR-017] <!-- Evaluator: Covered by FR-006 "both MUST be provided together or both omitted" -->
- [X] CHK038 Does the spec define loading/progress states for the upload submission (spinner, disabled button) to prevent double submissions? [Completeness, Spec §US1] <!-- Evaluator: Resolved — added FR-026 to spec.md -->

## Delete Endpoint Completeness

- [X] CHK039 Does the spec define behavior when deleting a module that is currently being executed by the scheduler? [Completeness, Spec §Edge Cases] <!-- Evaluator: Covered by Edge Cases "in-flight execution completes; next scheduled run skips" -->
- [X] CHK040 Does the delete success response (HTTP 204) match the standard REST convention and the project's API design standards? [Consistency, Spec §FR-011] <!-- Evaluator: Covered by FR-011 + Clarifications §Q5 -->
