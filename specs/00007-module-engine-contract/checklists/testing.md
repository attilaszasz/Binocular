# Testing Checklist: Module Engine & Contract

**Created**: 2026-06-10 | **Feature**: [spec.md](../spec.md)

## Completeness

- [X] CHK001 Are test fixtures specified for all contract conformance scenarios (valid, missing function, missing constants, syntax error)? [Completeness, Plan §Project Structure] <!-- Evaluator: Covered by plan.md §Project Structure - 7 fixture files listed -->
- [X] CHK002 Are error boundary test requirements defined for Exception, SystemExit, and timeout failure modes? [Completeness, Spec §OBJ3] <!-- Evaluator: Covered by spec.md §OBJ3 Validation Criteria 2-4 -->
- [X] CHK003 Are AST validation test requirements defined for both passing and failing module structures? [Completeness, Spec §OBJ4] <!-- Evaluator: Covered by spec.md §OBJ4 Validation Criteria 1-3 -->
- [X] CHK004 Is the coverage target (≥80%) explicitly specified for the extensions package? [Completeness, Plan §Testing Strategy] <!-- Evaluator: Covered by plan.md §Testing Strategy - Coverage tier ≥80% -->

## Clarity

- [X] CHK005 Are mock boundaries clearly defined (ScrapeClient mock, filesystem tmp_path, in-memory aiosqlite)? [Clarity, Plan §Testing Strategy] <!-- Evaluator: Covered by plan.md §Testing Strategy - Unit tier Mock Boundary column -->
- [X] CHK006 Is the distinction between unit tests (isolated) and integration tests (loader→runner→validator pipeline) clear? [Clarity, Plan §Testing Strategy] <!-- Evaluator: Covered by plan.md §Testing Strategy - separate Unit and Integration rows -->

## Consistency

- [X] CHK007 Are test file locations consistent with the existing project test structure? [Consistency, Plan §Project Structure] <!-- Evaluator: Covered by plan.md §Project Structure - backend/tests/extensions/ -->
- [X] CHK008 Is the testing framework (pytest + pytest-asyncio) consistent with existing test infrastructure? [Consistency, Plan §Testing Strategy] <!-- Evaluator: Covered by plan.md §Brownfield Notes - existing pytest setup -->

## Testability

- [X] CHK009 Are success criteria independently measurable (SC-001 through SC-005)? [Testability, Spec §Success Criteria] <!-- Evaluator: Covered by spec.md §Success Criteria - each SC is measurable with clear verification -->
- [X] CHK010 Are validation criteria written in Given/When/Then format for each objective? [Testability, Spec §OBJ1-5] <!-- Evaluator: Covered by spec.md §OBJ1-5 Validation Criteria sections -->
