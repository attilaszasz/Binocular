**Project Mode**: Brownfield
**Epic / Capability Map**: E023 → CAP-001 (Device Inventory & Lifecycle)

## Phase 1: Foundational / Backend API

- [ ] T001 {FR-001} Expose POST `/api/v1/checks/search-version` route in `backend/src/binocular/routes/checks.py` using Pydantic models for request/response.
- [ ] T002 {FR-002,FR-003} Implement `search_version` method in `CheckService` class inside `backend/src/binocular/services/checks.py` to load the module, invoke the runner statelessly, and return the version without side-effects.
- [ ] T003 Write backend tests for search-version success and failure routes in `backend/tests/routes/test_checks_routes.py`.

## Phase 2: Frontend UI & Integration

- [ ] T004 {FR-004} Add "Search" button next to the Module select field in `frontend/src/components/inventory/device-form.tsx`.
- [ ] T005 {FR-005} Bind button disabled state to check if `moduleId` and `model` are non-empty.
- [ ] T006 {FR-006} Wire the Search button click handler to call `/api/v1/checks/search-version` and auto-populate `currentVersion` state in the form on success.
- [ ] T007 {FR-007} Handle search error state and show a clear error message in the form on failure.
- [ ] T008 Run lint, typecheck, format, and verify all tests pass.
