# Analysis Report: Manual On-Demand Checks

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A001 | Task Convention | MEDIUM | `tasks.md` | Requirements FR-002, FR-003, FR-004, and FR-005 mapped to three or more task tags but the last carrying task did not consistently identify completion ownership. | Move incidental validation tags off late tasks and add `[COMPLETES FR-###]` markers to the final implementation task for each affected requirement. |

## Quality Summaries

- **Spec Quality**: PASS — no unresolved clarification markers, duplicate requirements, or placeholder text found.
- **Compliance**: PASS — plan decisions align with project instructions; no CRITICAL violations found.

## Coverage Summary

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| FR-001 | Yes | T004, T005, T007 | Completion marker present on T007. |
| FR-002 | Yes | T008, T009, T010, T011, T014 | Completion marker present on T014. |
| FR-003 | Yes | T001, T002, T003, T015, T018 | Completion marker present on T018. |
| FR-004 | Yes | T004, T006 | Covered. |
| FR-005 | Yes | T004, T006 | Covered. |
| FR-006 | Yes | T008, T009, T010, T011, T012 | Completion marker present on T012. |
| FR-007 | Yes | T008, T009, T010, T011, T012, T019 | Completion marker present on T019. |
| FR-008 | Yes | T015, T016 | Covered. |
| FR-009 | Yes | T013, T014, T015, T016, T017 | Completion marker present on T017. |

## Instructions Alignment Issues

None.

## Unmapped Tasks

None.

## Metrics

- Total Requirements: 9
- Total Tasks: 19
- Coverage: 100%
- Critical Issues Count: 0

## Autopilot Remediation Summary

| # | Finding ID | Severity | File(s) Modified | Change Applied | Status |
|---|-----------|----------|------------------|----------------|--------|
| 1 | A001 | MEDIUM | `tasks.md` | Added completion markers for FR-002 and FR-003; removed incidental FR-004/FR-005 tags from later validation/control tasks so their coverage ends at the rendering task. | Applied |
