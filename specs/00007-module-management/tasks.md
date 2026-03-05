---
feature_branch: "00007-module-management"
created: "2026-03-05"
spec: "spec.md"
plan: "plan.md"
---

# Tasks: Module Management (API & UI)

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 [P] Add `VALIDATION_FAILED` to `ErrorCode` literal in `backend/src/api/schemas/errors.py`
- [X] T002 [P] Add `UploadRejectedError` exception with `ValidationResult` payload in `backend/src/services/exceptions.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

- [X] T003 [P] Add `ModuleUploadResponse` and `UploadErrorDetail` schemas in `backend/src/api/schemas/modules.py`
- [X] T004 [P] Add `ExtensionModule`, `ValidationResult`, `PhaseResult`, `ValidationError` types and `VALIDATION_FAILED` code in `frontend/src/api/types.ts`; add `listModules()`, `uploadModule()`, `deleteModule()`, `reloadModules()` in `frontend/src/api/client.ts`; add `modules` key factory in `frontend/src/api/queryKeys.ts`

---

## Phase 3: User Story 1 — Upload an Extension Module (Priority: P1) 🎯 MVP

- [X] T005 [US1] Write failing upload endpoint integration tests (valid module, invalid extension, duplicate, underscore prefix, structural failure, oversized file) in `backend/tests/test_api/test_module_upload.py`
- [X] T006 [US1] {FR-001,FR-002,FR-003,FR-004,FR-005,FR-008,FR-009,FR-023} Implement `upload_module()` in `backend/src/services/module_service.py` — temp-file pipeline, filename regex validation, size check, static validation, save + rescan
- [X] T007 [US1] {FR-010} Add `POST /api/v1/modules` endpoint with multipart upload in `backend/src/api/routes/modules.py`
- [X] T008 [US1] Write failing ModuleUploadArea component tests (file selection, drag-and-drop, error display, loading state) in `frontend/tests/features/ModulesPage.test.tsx`
- [X] T009 [US1] {FR-016,FR-018,FR-025,FR-026} Create `ModuleUploadArea` component and `useUploadModule` hook in `frontend/src/features/modules/ModuleUploadArea.tsx` and `frontend/src/features/modules/hooks.ts`

---

## Phase 4: User Story 2 — View All Registered Modules (Priority: P1) 🎯 MVP

- [X] T010 [US2] Write failing module list rendering tests (table columns, status badges, inactive error display, empty state, reload) in `frontend/tests/features/ModulesPage.test.tsx`
- [X] T011 [US2] {FR-014,FR-015} Create `ModuleTable` component with accessible status badges and inline error display in `frontend/src/features/modules/ModuleTable.tsx`
- [X] T012 [US2] {FR-013,FR-019,FR-020,FR-022} Rewrite `ModulesPage` orchestrator with empty state, Reload button, and auto-refresh; add `useModules` and `useReloadModules` hooks in `frontend/src/features/modules/ModulesPage.tsx` and `frontend/src/features/modules/hooks.ts`

---

## Phase 5: User Story 3 — Delete a Module (Priority: P2)

- [X] T013 [US3] Write failing delete endpoint integration tests (successful delete, system module rejection, not-found) in `backend/tests/test_api/test_module_delete.py`
- [X] T014 [US3] {FR-011,FR-012} Add `delete_by_filename()` in `backend/src/repositories/extension_module_repo.py`, `unload()` in `backend/src/engine/loader.py`, `delete_module()` in `backend/src/services/module_service.py`, and `DELETE /api/v1/modules/{filename}` endpoint in `backend/src/api/routes/modules.py`
- [X] T015 [US3] Write failing delete confirmation dialog tests in `frontend/tests/features/ModulesPage.test.tsx`
- [X] T016 [US3] {FR-021} Add in-page delete confirmation dialog and `useDeleteModule` hook with list auto-invalidation in `frontend/src/features/modules/ModulesPage.tsx` and `frontend/src/features/modules/hooks.ts`

---

## Phase 6: User Story 4 — Runtime-Validate During Upload (Priority: P3)

- [X] T017 [US4] Write failing runtime validation tests (successful runtime, failure, timeout, skip when no test inputs) in `backend/tests/test_api/test_module_upload.py`
- [X] T018 [US4] {FR-006,FR-007,FR-024} Extend `upload_module()` in `backend/src/services/module_service.py` with optional runtime validation phase using `validate_runtime()` and configurable timeout
- [X] T019 [US4] {FR-017} Add optional Test URL and Device Model fields to `ModuleUploadArea` in `frontend/src/features/modules/ModuleUploadArea.tsx`

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T020 [P] Remove deprecated `ModuleCard.tsx` from `frontend/src/features/modules/`
- [X] T021 Run quickstart.md validation scenarios end-to-end

---

## Dependencies

```
Setup → Foundational → US1 Upload → US2 View → US3 Delete → Polish
                                  ↘→ US4 Runtime ─────────────↗
```

- **Setup → Foundational**: Error code and exception types must exist before schemas and API layer reference them
- **Foundational → All Stories**: Backend schemas and frontend API layer are consumed by every story
- **US1 → US2**: ModulesPage rewrite imports `ModuleUploadArea` created in US1
- **US2 → US3**: Delete button lives in `ModuleTable` created in US2
- **US1 → US4**: Runtime validation extends `upload_module()` and `ModuleUploadArea` from US1
- **US4 is independent of US2/US3** — can run after US1, but scheduled last per P3 priority
- **Execution order**: US1 (P1) → US2 (P1) → US3 (P2) → US4 (P3) follows priority ranking
- Tasks marked `[P]` can run in parallel within their phase

---

## Phase: Bug Fixes

- [X] T022 [BUG] {FR-018} Render per-error validation details in upload form — `ModulesPage.tsx` passes only `error.message`; extract `error.validationResult?.static_phase.errors` and `runtime_phase.errors` and render as a typed error list in `ModuleUploadArea` — `frontend/src/features/modules/ModulesPage.tsx`, `frontend/src/features/modules/ModuleUploadArea.tsx`
- [X] T023 [BUG] {FR-014} Add icon to Active/Error status badges in `ModuleTable` — FR-014 requires color + text label + icon together; add `CheckCircle` (Active) and `AlertCircle` (Error) icons from lucide-react — `frontend/src/features/modules/ModuleTable.tsx`
- [X] T024 [BUG] {FR-012} Rename `backend/_modules/mock_module.py` → `backend/_modules/_mock_module.py` so the seeded system module has an underscore prefix in the modules directory and is protected from deletion by the API — `backend/_modules/mock_module.py`
- [X] T025 [BUG] {FR-016} Fix Biome a11y error: replace `div[role="button"]` with a semantic `<label>` element wrapping the file input in `ModuleUploadArea` — eliminates `lint/a11y/useSemanticElements` violation — `frontend/src/features/modules/ModuleUploadArea.tsx`
- [X] T026 [BUG] Fix Biome format/import-order errors in new feature files — run `node_modules/.bin/biome check --write src/features/modules/` and remove unused `ExtensionModule` import from `hooks.ts` — `frontend/src/features/modules/`
- [X] T027 [BUG] mypy (pre-existing): `validator.py:377` — `overall_verdict` assigned `str` but declared `Literal['pass', 'fail']`; narrow the type appropriately — `backend/src/engine/validator.py`
- [X] T028 [BUG] mypy (pre-existing): `main.py:210` — root route handler redefinition causes incompatible return-type override; consolidate or annotate correctly — `backend/src/main.py`
- [X] T029 [BUG] {FR-012} Hide Delete button for system modules (`_`-prefixed filenames) in `ModuleTable` — spec US3 Scenario 3 requires "no delete action is offered, or any delete attempt is blocked with a message"; currently the Delete button renders for all modules — `frontend/src/features/modules/ModuleTable.tsx`
