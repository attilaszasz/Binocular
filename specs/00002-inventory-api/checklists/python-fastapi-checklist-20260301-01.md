# Requirements Quality Checklist — Python FastAPI — 00002-inventory-api

## Metadata
- Date: 2026-03-01
- Depth: Standard
- Audience: Author + Reviewers
- Focus Areas: Security & validation; Error handling consistency; Observability; Testability
- Inputs: spec.md, plan.md, OWASP ASVS/API Top 10, RFC 9457, RFC 9110, OpenAPI 3.1 + JSON Schema, Python typing strictness, FastAPI pytest/httpx practices, observability expectations, RFC 3339 timestamps

## Security & Validation
- [X] CHK001 Do the requirements explicitly define the trust boundary and access model (including the no-auth assumption) so security scope is unambiguous? [Clarity, Spec §6] — PASS: Spec Dependencies & Assumptions defines single-user trusted network and no-auth scope.
- [X] CHK002 Do the requirements define validation behavior for malformed resource identifiers before repository/database operations are attempted? [Completeness, Spec §3.1 (FR-019)] — RESOLVED: OpenAPI path IDs now enforce positive integers (`minimum: 1`) and invalid values surface as boundary validation errors.
- [X] CHK003 Do the requirements define canonicalization rules (trim/normalize) for all user-entered string fields to prevent validation bypass via whitespace variants? [Consistency, Spec §3.1 (FR-008, FR-018)] — RESOLVED: Spec FR-008b now mandates trim canonicalization for `name`, `firmware_source_url`, `current_version`, and `notes`.
- [X] CHK004 Do the requirements constrain firmware source URLs with explicit scheme expectations and boundary limits to reduce SSRF-style risk? [Security, Spec §3.1 (FR-008)] — RESOLVED: Spec FR-008 and OpenAPI now require absolute `http`/`https` URLs with max length 2048.
- [X] CHK005 Do the requirements set explicit maximum lengths for all mutable text fields (including notes/version text), not only names? [Completeness, Spec §3.1 (FR-008)] — RESOLVED: Spec FR-008a and OpenAPI add limits (`current_version` 100, `notes` 2000).
- [X] CHK006 Do the requirements state how unknown request-body fields are handled (rejected vs ignored) in a way consistent with OpenAPI 3.1/JSON Schema expectations? [Unambiguity, Spec §3.1 (FR-008, FR-017)] — RESOLVED: Spec FR-008c requires rejection; OpenAPI request schemas now set `additionalProperties: false`.
- [X] CHK007 Do the requirements enumerate allowed filter and sort values and define invalid-value handling to prevent unsafe or undefined query behavior? [Correctness, Spec §3.1 (FR-012, FR-013)] — RESOLVED: Spec FR-012/FR-013 now enumerate allowed values and require `VALIDATION_ERROR` for invalid inputs; OpenAPI includes enum + 422.
- [X] CHK008 Do the requirements explicitly require RFC 3339 timestamp format (including timezone semantics) for all API timestamp fields? [Precision, Spec §3.1 (FR-007)] — RESOLVED: Spec FR-007 now mandates RFC 3339 UTC with millisecond precision; OpenAPI timestamp descriptions aligned.

## Error Handling Consistency
- [X] CHK009 Do the requirements map each error class to a single HTTP status with non-overlapping RFC 9110 semantics? [Consistency, Spec §3.1 (FR-016, FR-019)] — PASS: Spec FR-016 now defines fixed error-code→status mapping; FR-019 keeps not-found semantics explicit.
- [X] CHK010 Do the requirements define a stable error payload schema compatible with RFC 9457 Problem Details or an explicitly justified alternative contract? [Completeness, Spec §3.1 (FR-016)] — PASS: Spec FR-016 + OpenAPI `ErrorResponse` define a stable explicit alternative (`detail`, `error_code`, `field`).
- [X] CHK011 Do the requirements specify whether boundary validation failures are consistently represented as 400 or 422 across all endpoints? [Unambiguity, Spec §3.1 (FR-008, FR-016)] — PASS: Spec FR-016 maps `VALIDATION_ERROR` to 422 consistently.
- [X] CHK012 Do the requirements specify deterministic conflict behavior for uniqueness violations (status, code, and message expectations)? [Testability, Spec §3.1 (FR-009, FR-016)] — PASS: FR-009 + FR-016 define duplicate semantics with `DUPLICATE_NAME` at 409 and human-readable details.
- [X] CHK013 Do the requirements ensure not-found behavior is consistent across retrieval, mutation, and action endpoints (including race-like deletion timing cases)? [Consistency, Spec §3.1 (FR-019); Spec §2] — PASS: FR-019 and edge cases require clear `NOT_FOUND` behavior across endpoint types.
- [X] CHK014 Do the requirements require sanitization rules for INTERNAL_ERROR responses so sensitive internals are not exposed? [Security, Spec §3.1 (FR-016)] — RESOLVED: Spec FR-016 now requires generic `INTERNAL_ERROR` messages without sensitive internals.
- [X] CHK015 Do the requirements define a versioned/stable machine-readable error-code vocabulary so clients can safely branch on codes over time? [Robustness, Spec §3.1 (FR-016)] — PASS: FR-016 defines fixed core codes and controlled extensibility for future additions.

## Observability
- [X] CHK016 Do the requirements define request-correlation behavior (accept, generate, and return correlation identifiers) for both success and error responses? [Observability, Spec §3.1] — RESOLVED: Spec FR-020 now mandates `X-Correlation-ID` accept/generate/return behavior for success and error responses.
- [X] CHK017 Do the requirements define minimum diagnostic fields needed for latency/error triage (method, route, status, duration, error_code)? [Observability, Spec §3.1 (FR-016)] — RESOLVED: Spec FR-021 now mandates structured logs with method, route, status, duration, correlation ID, and error code.
- [X] CHK018 Do the requirements include measurable latency/error expectations at the API contract level so operational quality is verifiable? [Measurability, Spec §5] — RESOLVED: Spec SC-008 adds measurable p95 API latency thresholds tied to V1 scale assumptions.
- [X] CHK019 Do the requirements define auditability expectations for state-changing actions (confirm, bulk confirm, deletions) with timestamped outcomes? [Traceability, Spec §3.1 (FR-003, FR-010, FR-014)] — RESOLVED: Spec FR-022 now requires timestamped audit events for all state-changing actions with outcome and correlation ID.
- [X] CHK020 Do the requirements define timestamp precision and consistency expectations across created/updated/last_checked fields to support reliable diagnostics? [Consistency, Spec §3.1 (FR-007)] — RESOLVED: Spec FR-007 now standardizes precision/timezone semantics across all API timestamps.

## Testability
- [X] CHK021 Do the requirements provide at least one directly testable acceptance scenario for each critical P1 behavior and related FRs? [Coverage, Spec §1; Spec §3.1] — PASS: Each P1 story includes independent test guidance plus concrete Given/When/Then scenarios.
- [X] CHK022 Do the requirements define idempotency outcomes with measurable before/after expectations for repeated single and bulk confirm actions? [Verifiability, Spec §3.1 (FR-004, FR-015)] — PASS: FR-004/FR-015 and US3/US6 scenarios define repeat-action outcomes with explicit summaries.
- [X] CHK023 Do the requirements define deterministic sorting behavior for ties and null last-checked values to avoid flaky contract tests? [Determinism, Spec §3.1 (FR-013); Spec §1.5] — RESOLVED: Spec FR-013b now defines tie-breaker (`id` ascending) and null `last_checked_at` ordering.
- [X] CHK024 Do the requirements define enough contract-level request/response/error detail for OpenAPI-driven pytest/httpx API tests without implementation assumptions? [Testability, Spec §3.1 (FR-016, FR-017)] — PASS: OpenAPI contract defines endpoint shapes, enums, and error schema in sufficient detail for contract tests.
