**Project Mode**: Brownfield

**Brownfield Notes**:
- **Patterns to reuse**: Router registration in `routes/__init__.py`; `Card`/`Button` shadcn/ui; `useModules` hook pattern
- **Tests to extend**: `backend/tests/` pytest structure; `frontend/src/pages/modules.test.tsx`
- **Naming conventions**: snake_case Python; PascalCase React; kebab-case TS utilities

## Phase 1: Foundational — Kit Static Files

- [X] T001 {FR-002} Create kit package init `backend/src/binocular/module_kit/__init__.py`
- [X] T002 {FR-002} Create starter template `backend/src/binocular/module_kit/STARTER_TEMPLATE.py`
- [X] T003 {FR-003} Create example module `backend/src/binocular/module_kit/EXAMPLE_MODULE.py`
- [X] T004 [P] {FR-004,FR-007} Create AI instructions `backend/src/binocular/module_kit/AI_INSTRUCTIONS.md`
- [X] T005 [P] {FR-004} Create contract reference `backend/src/binocular/module_kit/CONTRACT_REFERENCE.md`

## Phase 2: 🎯 MVP US3 — Kit File Serving Endpoint

- [X] T006 [US3] {FR-001,FR-008,FR-009} Create kit API route `backend/src/binocular/routes/module_kit.py` after:T001
- [X] T007 [US3] {FR-001} Register kit router in `backend/src/binocular/routes/__init__.py` after:T006
- [X] T008 [US3] {FR-001,FR-008,FR-009} [COMPLETES FR-001] Write endpoint tests `backend/tests/test_module_kit.py` after:T007

## Phase 3: 🎯 MVP US1 — Download AI Module Kit

- [X] T009 [US1] {FR-005} Create `ModuleGuidanceSection` component `frontend/src/components/modules/ModuleGuidanceSection.tsx` after:T007
- [X] T010 [US1] {FR-005,FR-010} [COMPLETES FR-005] Integrate guidance section into `frontend/src/pages/modules.tsx` after:T009

## Phase 4: 🎯 MVP US2 — In-UI Module Authoring Guidance

- [X] T011 [US2] {FR-010} Verify guidance section responsive layout in `ModuleGuidanceSection.tsx` after:T010

## Phase 5: US4 — Copy Validation Errors for AI

- [X] T012 [US4] {FR-006} Extract `copyErrorsForAI` utility to `frontend/src/lib/copy-errors-for-ai.ts`
- [X] T013 [US4] {FR-006} [COMPLETES FR-006] Update `ModuleUploadForm.tsx` to import shared utility after:T012

## Phase 6: Polish & Cross-Cutting

- [X] T014 Write frontend component tests for `ModuleGuidanceSection` in `frontend/src/components/modules/ModuleGuidanceSection.test.tsx` after:T011
