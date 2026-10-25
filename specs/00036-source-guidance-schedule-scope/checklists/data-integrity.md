# Data Integrity: Sources
**Created**: 2026-10-07 | **Feature**: [spec.md](../spec.md)

## Completeness

- [X] CHK001 Are stable identities distinguished from readable guidance labels? [Completeness, Spec §Requirements FR-001] <!-- Evaluator: Covered by spec.md §Requirements FR-001; plan.md §Requirement Coverage Map. -->
- [X] CHK002 Are defaults and omission semantics specified for every optional guidance field? [Completeness, Spec §Requirements FR-009] <!-- Evaluator: Covered by data-model.md §Guidance Contract. -->
- [X] CHK003 Are field types, length limits and example-count limits defined? [Completeness, Spec §Clarifications FR-009] <!-- Evaluator: Covered by data-model.md §Guidance Contract, 120/1000/2048 and 10×120. -->
- [X] CHK004 Are additive migration ordering and backup safeguards defined? [Completeness, Spec §Requirements FR-011] <!-- Evaluator: Covered by data-model.md §Persistent Entities, migration 0010/backup gate. -->
- [X] CHK005 Are IDs, links, schedules, pause and health fields explicitly preserved during upgrades? [Completeness, Spec §Requirements FR-011] <!-- Evaluator: Covered by data-model.md §Persistent Entities and §Lifecycle / Legacy Seeding. -->
- [X] CHK006 Are unchanged-content backfill and legacy/custom collision cases specified? [Completeness, Spec §Requirements FR-010/FR-011] <!-- Evaluator: Covered by data-model.md §Lifecycle / Legacy Seeding. -->
- [X] CHK007 Are missing or unrecognized provenance cases defined without invented official claims? [Completeness, Spec §Requirements FR-010] <!-- Evaluator: Covered by data-model.md §Persistent Entities, derived API; §Lifecycle / Legacy Seeding, protected unknown bytes. -->

## Clarity

- [X] CHK008 Is linked-device membership defined without a persisted counter? [Clarity, Spec §Requirements FR-012] <!-- Evaluator: Covered by data-model.md §Persistent Entities, scope snapshot. -->
- [X] CHK009 Is detail count defined from the same membership snapshot as its list? [Clarity, Spec §Success Criteria SC-003] <!-- Evaluator: Covered by contracts/api.md §Scope Schema, count equals devices.length. -->
- [X] CHK010 Are successful pause, pending entry and already-running work boundaries distinguished? [Clarity, Spec §Requirements FR-015] <!-- Evaluator: Covered by data-model.md §Execution / Write Boundaries, worker entry claim. -->
- [X] CHK011 Is explicit resume distinguished from interval edits, uploads and startup? [Clarity, Spec §Requirements FR-011/FR-015] <!-- Evaluator: Covered by data-model.md §Lifecycle / Legacy Seeding and §Execution / Write Boundaries. -->
- [X] CHK012 Is manual single/bulk/search behavior distinguished from automatic admission? [Clarity, Spec §Requirements FR-014] <!-- Evaluator: Covered by data-model.md §Execution / Write Boundaries, manual bypass/no status writes. -->

## Consistency

- [X] CHK013 Are shared-connection write boundaries consistent with unrelated repository/cache commits? [Consistency, Spec §Requirements FR-011/FR-015] <!-- Evaluator: Covered by data-model.md §Execution / Write Boundaries; plan.md AD-005. -->
- [X] CHK014 Are custom replacement omissions consistent across persistence and API guidance? [Consistency, Spec §Requirements FR-009/FR-010] <!-- Evaluator: Covered by data-model.md §Lifecycle / Legacy Seeding; contracts/openapi.yaml POST modules. -->
- [X] CHK015 Are canonical endpoints preserved separately from actionable help links? [Consistency, Spec §Requirements FR-007] <!-- Evaluator: Covered by data-model.md §Guidance Contract; contracts/api.md §Scope Schema links. -->
- [X] CHK016 Are membership refresh rules consistent with current and future module-wide scope? [Consistency, Spec §Requirements FR-012/FR-013] <!-- Evaluator: Covered by contracts/api.md §Scope Schema caching; spec.md FR-013. -->
- [X] CHK017 Are failed reads/writes distinguished from zero counts and saved state? [Consistency, Spec §Requirements FR-019] <!-- Evaluator: Covered by contracts/api.md §Module Addition Schema/§Scope Schema; plan.md §Error Handling Strategy. -->

## Testability

- [X] CHK018 Are migration/restart/backfill/protected-byte cases assigned deterministic evidence? [Testability, Spec §Success Criteria SC-005] <!-- Evaluator: Covered by quickstart.md §Deterministic Matrix, lifecycle/isolation. -->
- [X] CHK019 Are pause races and stale generations testable without real sleeps or notifications? [Testability, Spec §Success Criteria SC-004] <!-- Evaluator: Covered by quickstart.md §Deterministic Matrix, pause barriers/isolation. -->
- [X] CHK020 Are zero/one/many and concurrent membership cases included in the scope validation matrix? [Testability, Spec §Success Criteria SC-003] <!-- Evaluator: Covered by quickstart.md §Deterministic Matrix, scope. -->
