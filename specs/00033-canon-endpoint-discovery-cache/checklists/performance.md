# Performance: Canon Endpoint Discovery Cache
**Created**: 2026-09-08 | **Feature**: [spec.md](../spec.md)

## Measurability

- [X] CHK001 Is the warm-path bound quantified as 0–30 seconds after centralized pacing-slot acquisition? [Measurability, Spec §Success Criteria/SC-002] <!-- Evaluator: Covered by spec.md §Technical Objectives Objective 2, SC-002, and §Clarifications -->
- [X] CHK002 Is the fresh mapping request count defined as exactly one mapped endpoint request, excluding client-controlled robots refreshes? [Measurability, Spec §Requirements/TR-003] <!-- Evaluator: Covered by spec.md §Technical Requirements TR-003 and §Clarifications -->
- [X] CHK003 Is recovery work bounded to one full rediscovery after cached-endpoint invalidation? [Measurability, Spec §Requirements/TR-005] <!-- Evaluator: Covered by spec.md §Technical Requirements TR-005 and plan.md §Error Handling Strategy -->

## Completeness

- [X] CHK004 Do fresh mappings retain centralized robots, retry, deadline, cancellation, and shared Canon pacing enforcement? [Completeness, Spec §Technical Objectives/Objective 2] <!-- Evaluator: Covered by spec.md §Technical Objectives Objective 2 and §Technical Constraints -->
- [X] CHK005 Is same-model work coalesced while distinct models continue to use shared Canon-origin pacing? [Completeness, Spec §Edge Cases & Boundaries] <!-- Evaluator: Covered by spec.md §Edge Cases & Boundaries and plan.md §Data Model Summary -->
- [X] CHK006 Does the plan prohibit holding SQLite transactions during pacing, HTTP, parsing, or waiter completion? [Completeness, Plan §Implementation Hints] <!-- Evaluator: Covered by plan.md §Implementation Hints HINT-005 and data-model.md §Migration and Invariants -->

## Testability

- [X] CHK007 Does the test strategy require injected time and scripted transports instead of real sleeps or live Canon requests? [Testability, Spec §Technical Requirements/TR-008] <!-- Evaluator: Covered by spec.md §Technical Requirements TR-008, plan.md §Testing Strategy, and research.md §Deterministic Validation -->
- [X] CHK008 Are shared pacing, concurrent single-flight, timeout, and cancellation performance behavior included in deterministic coverage? [Testability, Plan §Testing Strategy] <!-- Evaluator: Covered by plan.md §Testing Strategy and tasks.md §Phase 3 -->
