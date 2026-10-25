# Security: Sources
**Created**: 2026-10-07 | **Feature**: [spec.md](../spec.md)

## Completeness

- [X] CHK001 Are server-side optional metadata type and size checks required before persistence? [Completeness, Spec §Requirements FR-009] <!-- Evaluator: Covered by data-model.md §Guidance Contract, AST/runtime stages; §Lifecycle / Legacy Seeding. -->
- [X] CHK002 Are every example item's type, length and empty-value rules defined? [Completeness, Spec §Clarifications FR-009] <!-- Evaluator: Covered by data-model.md §Guidance Contract, list/tuple/nonblank/120. -->
- [X] CHK003 Are unsafe, relative, credential-bearing and control-character URLs addressed? [Completeness, Spec §Requirements FR-007] <!-- Evaluator: Covered by data-model.md §Guidance Contract, SOURCE_HELP_URL. -->
- [X] CHK004 Are absent/unsafe links omitted rather than exposed as actionable controls? [Completeness, Spec §Requirements FR-007] <!-- Evaluator: Covered by spec.md FR-007; contracts/api.md §Module Addition Schema. -->
- [X] CHK005 Is new-window opener protection specified for both source and human-help links? [Completeness, Spec §Requirements FR-007] <!-- Evaluator: Covered by contracts/api.md §Scope Schema, independent validation/noopener noreferrer. -->
- [X] CHK006 Is guidance output constrained to escaped plain text rather than executable markup? [Completeness, Spec §Requirements FR-007/FR-009] <!-- Evaluator: Covered by data-model.md §Guidance Contract, strictness. -->
- [X] CHK007 Is the executable-module warning required before import-capable workflows? [Completeness, Spec §Requirements FR-017] <!-- Evaluator: Covered by spec.md FR-017; plan.md §Instructions Check IV; quickstart.md workflows. -->

## Clarity

- [X] CHK008 Is the unsandboxed in-process full-privilege trust boundary explicit? [Clarity, Spec §Requirements FR-017] <!-- Evaluator: Covered by spec.md FR-017 and Scope excluded sandbox claims. -->
- [X] CHK009 Is trusted-LAN/optional existing authentication retained without introducing accounts? [Clarity, Spec §Scope Excluded] <!-- Evaluator: Covered by plan.md §Technical Context; contracts/api.md §Scope Schema auth. -->
- [X] CHK010 Is verified provenance host-derived rather than controlled by module declarations? [Clarity, Spec §Requirements FR-010] <!-- Evaluator: Covered by data-model.md §Persistent Entities, host-controlled origin/hash and derived API. -->
- [X] CHK011 Are filename collisions and direct-file changes excluded as proof of official guidance? [Clarity, Spec §Requirements FR-010/FR-011] <!-- Evaluator: Covered by data-model.md §Lifecycle / Legacy Seeding, custom/direct/legacy transitions. -->
- [X] CHK012 Are nonliteral declarations and runtime validation stages distinguished without safety claims? [Clarity, Spec §Requirements FR-009/FR-017] <!-- Evaluator: Covered by data-model.md §Guidance Contract, AST/runtime; spec.md FR-017 full privileges. -->

## Consistency

- [X] CHK013 Is URL omission consistent with preserving canonical scraping metadata? [Consistency, Spec §Requirements FR-007] <!-- Evaluator: Covered by data-model.md §Guidance Contract SOURCE_URL; official-guidance.md §Evidence and Preservation. -->
- [X] CHK014 Are custom uploads prevented from inheriting verified official claims? [Consistency, Spec §Requirements FR-010/FR-011] <!-- Evaluator: Covered by data-model.md §Lifecycle / Legacy Seeding, custom clears official hash/is_official. -->
- [X] CHK015 Does local help avoid new vendor requests and preserve the centralized HTTP boundary? [Consistency, Spec §Requirements FR-008] <!-- Evaluator: Covered by spec.md FR-008; plan.md §Instructions Check II. -->
- [X] CHK016 Are parameterized SQLite writes and single-volume state retained? [Consistency, Spec §Requirements FR-011] <!-- Evaluator: Covered by plan.md §Technical Context; data-model.md §Execution / Write Boundaries. -->
- [X] CHK017 Are security/tooling additions development-only rather than runtime scope expansion? [Consistency, Spec §Scope Excluded] <!-- Evaluator: Covered by quickstart.md §Environment and Commands, npm -D installs and existing scanners. -->

## Testability

- [X] CHK018 Are malformed metadata and URL/provenance boundary cases present in offline validation? [Testability, Spec §Requirements FR-020] <!-- Evaluator: Covered by quickstart.md §Deterministic Matrix, metadata/lifecycle/isolation. -->
- [X] CHK019 Are security scans and image vulnerability checks explicitly required rather than silently skipped? [Testability, Spec §Requirements FR-020] <!-- Evaluator: Covered by plan.md §Testing Strategy; quickstart.md §Environment and Commands, pip-audit/npm audit/Trivy. -->
- [X] CHK020 Are strict compiler checks, TypeScript5 alignment and reproducible lockfile verification specified? [Testability, Spec §Requirements FR-020] <!-- Evaluator: Covered by quickstart.md §Environment and Commands, required TS5.9.3 task/strict configs/npm ci/build/typecheck. -->
