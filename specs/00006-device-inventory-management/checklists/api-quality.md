# Checklist: API Quality
**Created**: 2026-06-10 | **Feature**: [spec.md](../spec.md)

## Completeness

- [X] CHK001 Are all CRUD operations (Create, Read single, Read list, Update, Delete) specified with explicit HTTP methods and paths? [Completeness, Spec §FR-002–FR-006] <!-- Evaluator: Covered by spec.md §FR-002 through FR-006 -->
- [X] CHK002 Are error responses defined for all failure modes (not found, validation error, FK violation)? [Completeness, Spec §FR-008/FR-009] <!-- Evaluator: Covered by spec.md §FR-008, FR-009 and plan.md §Error Handling -->
- [X] CHK003 Are request/response schemas defined with required vs optional fields? [Completeness, Plan §API Surface] <!-- Evaluator: Covered by contracts/openapi.yaml — DeviceCreate, DeviceUpdate, DeviceResponse schemas -->
- [X] CHK004 Is the confirm endpoint (PUT /devices/{id}/confirm) specified with its distinct behavior separate from general update? [Completeness, Spec §FR-007] <!-- Evaluator: Covered by spec.md §FR-007 and contracts/openapi.yaml -->
- [X] CHK005 Are HTTP status codes specified for each operation outcome (201, 200, 204, 404, 422)? [Completeness, Spec §SC-006] <!-- Evaluator: Covered by spec.md §SC-006 and contracts/openapi.yaml -->

## Clarity

- [X] CHK006 Is the API response shape for device list (flat module fields vs nested object) explicitly decided? [Clarity, Spec §FR-003] <!-- Evaluator: Covered by spec.md §FR-003 and §Clarifications — flat fields -->
- [X] CHK007 Is the no-op behavior for confirming a device without pending update clearly specified? [Clarity, Spec §Edge Cases] <!-- Evaluator: Covered by spec.md §Edge Cases — no-op returning 200 -->
- [X] CHK008 Are the module listing endpoint's scope limitations (read-only in E006) documented? [Clarity, Plan §HINT-005] <!-- Evaluator: Covered by plan.md §Implementation Hints HINT-005 -->

## Consistency

- [X] CHK009 Are the API paths consistent between spec requirements, plan API Surface, and OpenAPI contract? [Consistency, Plan §API Surface] <!-- Evaluator: Covered by cross-reference of spec.md, plan.md, and contracts/openapi.yaml -->
- [X] CHK010 Are validation rules in the OpenAPI schema consistent with Pydantic model constraints in the plan? [Consistency, Plan §Error Handling] <!-- Evaluator: Covered by contracts/openapi.yaml schema constraints matching spec.md §FR-001 -->

## Testability

- [X] CHK011 Are acceptance scenarios for each CRUD operation defined with Given/When/Then format? [Testability, Spec §User Scenarios] <!-- Evaluator: Covered by spec.md §US1–US5 Acceptance Scenarios -->
- [X] CHK012 Is the testing strategy for API routes (integration tests with in-memory SQLite) specified? [Testability, Plan §Testing Strategy] <!-- Evaluator: Covered by plan.md §Testing Strategy — Integration tier -->
