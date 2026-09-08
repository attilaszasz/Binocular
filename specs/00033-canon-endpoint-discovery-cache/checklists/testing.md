# Testing: Canon Endpoint Discovery Cache
**Created**: 2026-09-08 | **Feature**: [spec.md](../spec.md)

## Coverage

- [X] CHK001 Are migration idempotence and file-backed restart persistence required for cache metadata? [Completeness, Spec §Technical Objectives/Objective 1] <!-- Evaluator: Covered by spec.md §Technical Objectives Objective 1, SC-001, and tasks.md §Phase 1 -->
- [X] CHK002 Is the full 0, 24h-epsilon, 24h, and 24h-plus-epsilon freshness matrix required? [Completeness, Spec §Technical Requirements/TR-008] <!-- Evaluator: Covered by spec.md §Technical Requirements TR-008 and SC-001 -->
- [X] CHK003 Are warm hit, missing mapping, expiry, invalidation, one-fallback recovery, and visible recovery-failure paths required? [Completeness, Spec §Technical Requirements/TR-004–TR-007] <!-- Evaluator: Covered by spec.md §Technical Requirements TR-004–TR-008 and tasks.md §Phase 2 -->
- [X] CHK004 Are version search, manual, and scheduled entry points all required to prove live-derived warm results? [Coverage, Spec §Technical Objectives/Objective 2] <!-- Evaluator: Covered by spec.md §Technical Objectives Objective 2, SC-002, and plan.md §Requirement Coverage Map -->
- [X] CHK005 Are lease takeover, fencing, detach, close-race, and cancellation scenarios required for same-model coordination? [Completeness, Spec §Technical Requirements/TR-006–TR-008] <!-- Evaluator: Covered by spec.md §Technical Requirements TR-006–TR-008 and tasks.md §Phase 3 -->

## Test Design

- [X] CHK006 Are captured Canon fixtures, injected clocks, and scripted transports specified as the test seams? [Testability, Spec §Technical Requirements/TR-008] <!-- Evaluator: Covered by spec.md §Technical Requirements TR-008, plan.md §Testing Strategy, and research.md §Deterministic Validation -->
- [X] CHK007 Are transport, status, parsing, identity, timeout, and cancellation failure classes explicitly covered without stale success? [Correctness, Spec §Technical Requirements/TR-005] <!-- Evaluator: Covered by spec.md §Technical Requirements TR-005, SC-003, and plan.md §Error Handling Strategy -->
- [X] CHK008 Are strict typing, linting, security scanning, and the 80% coverage policy included in the final validation task? [Completeness, Plan §Testing Strategy] <!-- Evaluator: Covered by plan.md §Testing Strategy and tasks.md §Phase 3 T014 -->
- [X] CHK009 Are tests explicitly forbidden from making real sleeps or live requests? [Testability, Spec §Technical Requirements/TR-008] <!-- Evaluator: Covered by spec.md §Technical Requirements TR-008 and research.md §Deterministic Validation -->
