# Performance Checklist

- [X] CHK001 Is rate limiting scoped to the correct unit of isolation? [Completeness, Spec §Technical Objectives] <!-- Evaluator: Covered by OBJ3 and TR-005 -->
- [X] CHK002 Are retry attempts and delays bounded? [Completeness, Spec §Requirements] <!-- Evaluator: Covered by TR-006, TR-007, and HINT-004 -->
- [X] CHK003 Does the plan avoid slow wall-clock sleeps in tests? [Testability, Plan §Implementation Hints] <!-- Evaluator: Covered by AD-003 and HINT-003 -->
- [X] CHK004 Are same-origin pacing and retry behavior deterministic under validation? [Verifiability, Spec §Success Criteria] <!-- Evaluator: Covered by SC-003 -->
- [X] CHK005 Is a slower vendor prevented from blocking unrelated origins? [Boundary, Spec §Scope] <!-- Evaluator: Covered by Scope boundaries and research Rate Limit and Retry -->
