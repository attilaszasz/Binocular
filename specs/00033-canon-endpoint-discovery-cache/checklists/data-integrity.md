# Data Integrity: Canon Endpoint Discovery Cache
**Created**: 2026-09-08 | **Feature**: [spec.md](../spec.md)

## Completeness

- [X] CHK001 Are mapping and lease attributes typed, nullable state, composite keys, and constraints defined? [Completeness, Spec §Requirements/TR-001] <!-- Evaluator: Covered by data-model.md §CanonFirmwareEndpointMapping and §CanonRefreshLease -->
- [X] CHK002 Is persisted cache scope explicitly limited so no firmware version or equivalent result fields can be stored? [Completeness, Spec §Requirements/TR-001–TR-002] <!-- Evaluator: Covered by spec.md §Technical Requirements TR-001–TR-002 and data-model.md §Migration and Invariants -->
- [X] CHK003 Are mapping validity and invalidation states, including every invalidating failure category, defined? [Completeness, Spec §Requirements/TR-005] <!-- Evaluator: Covered by spec.md §Technical Requirements TR-005 and data-model.md §Relationships and Lifecycle -->
- [X] CHK004 Are lease ownership, fencing, expiry, heartbeat, waiter count, and closing state defined for cross-process coordination? [Completeness, Spec §Requirements/TR-006] <!-- Evaluator: Covered by data-model.md §CanonRefreshLease -->

## Consistency

- [X] CHK005 Are the canonical family/model cache key and endpoint constraints consistent across the specification, plan, and data model? [Consistency, Spec §Clarifications] <!-- Evaluator: Covered by spec.md §Clarifications, plan.md §Data Model Summary, and data-model.md §CanonFirmwareEndpointMapping -->
- [X] CHK006 Is strict freshness consistently defined as less than 24 hours, with exactly 24 hours expired, at the dispatch point? [Consistency, Spec §Edge Cases & Boundaries] <!-- Evaluator: Covered by spec.md §Edge Cases & Boundaries, plan.md §Implementation Hints HINT-001, and data-model.md §Migration and Invariants -->
- [X] CHK007 Do the repository contracts require atomic lease takeover, detach, and closure without holding transactions across network work? [Consistency, Plan §Implementation Hints] <!-- Evaluator: Covered by data-model.md §Repository Contracts and §Migration and Invariants; plan.md §Implementation Hints HINT-005 -->

## Testability

- [X] CHK008 Are migration idempotence, reopened-database durability, and timestamp-boundary behavior required with deterministic tests? [Testability, Spec §Technical Requirements/TR-008] <!-- Evaluator: Covered by spec.md §Technical Requirements TR-008, plan.md §Testing Strategy, and tasks.md §Phase 1 -->
- [X] CHK009 Are invalidation and lease state transitions independently testable without persisting a firmware result? [Testability, Spec §Technical Requirements/TR-005–TR-008] <!-- Evaluator: Covered by spec.md §Technical Requirements TR-005–TR-008 and tasks.md §Phase 3 -->
