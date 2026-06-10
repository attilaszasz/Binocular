# Checklist: Testing
**Created**: 2026-06-10 | **Feature**: [spec.md](../spec.md)

## Completeness

- [X] CHK001 Are test tiers (unit, integration, coverage) defined with specific tools and scope? [Completeness, Plan §Testing Strategy] <!-- Evaluator: Covered by plan.md §Testing Strategy — all tiers defined -->
- [X] CHK002 Are mock boundaries specified for each test tier (in-memory SQLite, MSW)? [Completeness, Plan §Testing Strategy] <!-- Evaluator: Covered by plan.md §Testing Strategy — mock boundaries per tier -->
- [X] CHK003 Are both backend and frontend testing strategies defined? [Completeness, Plan §Testing Strategy] <!-- Evaluator: Covered by plan.md — pytest + Vitest rows -->
- [X] CHK004 Is the coverage target (80%) specified and aligned with project instructions? [Completeness, Plan §Testing Strategy] <!-- Evaluator: Covered by plan.md §Testing Strategy and project-instructions.md §Testing & Quality Policy -->

## Clarity

- [X] CHK005 Are the test file locations documented in the project structure? [Clarity, Plan §Project Structure] <!-- Evaluator: Covered by plan.md §Project Structure — backend/tests/devices/ and frontend tests -->
- [X] CHK006 Is static analysis (mypy --strict, tsc) listed as a quality gate? [Clarity, Plan §Testing Strategy] <!-- Evaluator: Covered by plan.md §Testing Strategy — Static Analysis row -->

## Consistency

- [X] CHK007 Are the testing tools consistent with the project-instructions.md quality policy (pytest, Vitest, Ruff, Biome)? [Consistency, project-instructions.md §Testing] <!-- Evaluator: Covered by cross-reference of plan.md §Testing Strategy and project-instructions.md §Testing & Quality Policy -->
- [X] CHK008 Are test scope descriptions consistent with the requirement coverage map? [Consistency, Plan §Requirement Coverage] <!-- Evaluator: Covered by plan.md — all FR-### in coverage map have corresponding test tiers -->

## Testability

- [X] CHK009 Are all success criteria (SC-001 through SC-006) traceable to specific test approaches? [Testability, Spec §Success Criteria] <!-- Evaluator: Covered by spec.md §Success Criteria — each SC maps to a testable user scenario -->
- [X] CHK010 Are the acceptance scenarios structured as Given/When/Then to enable direct test case derivation? [Testability, Spec §User Scenarios] <!-- Evaluator: Covered by spec.md §US1–US5 — all use Given/When/Then -->
