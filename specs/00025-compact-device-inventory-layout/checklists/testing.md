# Checklist: Testing

**Created**: 2026-06-16 | **Feature**: [spec.md](../spec.md)

## Completeness
- [X] CHK001 Are there specific unit test cases defined for verifying that the device_type badge is absent? [Completeness, Spec §User Scenarios & Testing] <!-- Evaluator: Covered by spec.md §SC-001 and plan.md §Testing Strategy -->
- [X] CHK002 Are there specific unit test cases defined for verifying that the card rendering has compact styling classes? [Completeness, Spec §User Scenarios & Testing] <!-- Evaluator: Covered by spec.md §SC-002 and plan.md §Testing Strategy -->

## Clarity
- [X] CHK003 Are the mock datasets or mock components clear about what fields (including device_type) are passed to the card during test execution? [Clarity, Spec §User Scenarios & Testing] <!-- Evaluator: Covered by plan.md §Testing Strategy -->

## Consistency
- [X] CHK004 Do the card tests align with existing page and form test methodologies (Vitest + React Testing Library)? [Consistency, Spec §Constraints] <!-- Evaluator: Covered by plan.md §Testing Strategy and project-instructions.md -->
- [X] CHK005 Do the test cases cover both success and empty/missing data scenarios for version numbers? [Consistency, Spec §User Scenarios & Testing] <!-- Evaluator: Covered by spec.md §SC-002 and plan.md §Testing Strategy -->

## Testability
- [X] CHK006 Is the component rendered in JSDOM so that CSS classes (Tailwind paddings and margins) can be inspected or verified? [Testability, Spec §User Scenarios & Testing] <!-- Evaluator: Covered by plan.md §Testing Strategy -->
