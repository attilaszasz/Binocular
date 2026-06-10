# Analysis Report — E026 Per-Module Frequency on Modules Page

**Feature**: `00027-per-module-frequency-on-modules` | **Date**: 2026-06-07

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| AN-001 | Ambiguity | HIGH | FR-004, US2-4, Edge Cases | "Immediately" used inconsistently — US2-4 says "immediately" but Edge Cases say "on next trigger". SC-002 resolves via parenthetical but FR-004/US2-4 still ambiguous. | Replace "immediately" in US2-4 with "the scheduler picks up the change synchronously within the request". |
| AN-002 | Underspecification | HIGH | Edge Cases, FR-004 | Concurrency-write-prevention mechanism undefined: "data-fetching layer prevents conflicting concurrent writes" with no mechanism specified. | Clarify as last-write-wins via PUT idempotency + TanStack Query invalidation; no locking needed. |
| AN-003 | Underspecification | MEDIUM | US1-4 | "Each affected card" ambiguous when schedule data fails globally. | Clarify: all module cards on the current page show inline error if the schedule fetch fails. |
| AN-004 | Underspecification | MEDIUM | US2-9, STF-001 | Post-notification card state undefined after external-change notification closes the editor. | Clarify: card refreshes to show the new value; notification auto-dismisses after 5s. |
| AN-005 | Underspecification | MEDIUM | FR-006 | Pagination mechanism not specified in FR-006 (page-based vs cursor). | Already resolved by contracts/openapi.yaml (page/pageSize) — non-actionable, covered. |
| AN-006 | Underspecification | MEDIUM | Clarifications Q4, US2-6 | "on blur/input" ambiguous: fires on blur, input, or both. | Clarify: validate on blur only (more conservative); "input" in label means the input event triggers no validation, only blur. |
| AN-007 | Underspecification | LOW | US2-3 | Custom value reopening: does editor pre-populate or reset? | Document: editor pre-populates with current custom value on reopen. |
| AN-008 | Underspecification | LOW | US1-4 | "Retry option" mechanics undefined. | Document: retry button reloads the modules list (single action, not per-card). |
| AN-009 | Duplication | LOW | FR-001, Clarifications Q2 | Label format rules duplicated across FR-001 and clarifications. | Acceptable — clarifications are traceability records, not spec duplication. |
| AN-010 | Underspecification | MEDIUM | FR-004, Clarifications Q1 | Scheduler reschedule failure behavior undefined if reschedule_type() throws. | Document: DB write succeeds, schedule persisted; scheduler failure logged; auto-retries on next restart. Already partially covered in plan.md Error Handling. |

## Quality Summaries

- **Spec Quality**: 17 findings from Validator — 3 duplication (low), 5 ambiguity (1 high, 2 medium, 2 low), 9 underspecification (2 high, 4 medium, 3 low). No unresolved NEEDS CLARIFICATION markers. All clarification-session questions integrated into spec body.
- **Compliance**: **PASS** — Policy Auditor confirms all 7 core project-instructions principles satisfied or N/A. No violations.

## Coverage Summary

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| FR-001 | ✓ | T006, T008, T009 | COMPLETES on T009 |
| FR-002 | ✓ | T009, T011 | |
| FR-003 | ✓ | T009, T011 | |
| FR-004 | ✓ | T010 | |
| FR-005 | ✓ | T007, T008 | COMPLETES on T008 |
| FR-006 | ✓ | T002, T003, T004, T007 | COMPLETES on T004 |

## Unmapped Tasks

| Task ID | Phase | Rationale |
|---------|-------|-----------|
| T001 | Foundational | Infrastructure task — adds fields to dataclass consumed by T002/T004 |
| T005 | Foundational | Data integrity fix — DELETE cascade on module removal |

Both are in Foundational phase, which is explicitly exempt from requirement-tag requirement per SDD conventions.

## Metrics

- **Total Requirements**: 6 (FR-001–FR-006)
- **Total Tasks**: 11
- **Coverage**: 100% (6/6)
- **Critical Issues**: 0
- **HIGH Issues**: 2
- **MEDIUM Issues**: 5
- **LOW Issues**: 3
