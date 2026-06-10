# Tasks: AI-Assisted Module Authoring UX

**Project Mode**: Brownfield
**Epic**: E031 — AI-Assisted Module Authoring UX
**Capability Map**: US1 → FR-001, FR-006 | US2 → FR-002, FR-003, FR-007, FR-008 | US3 → FR-004, FR-005 | US4 → (UX polish)

## Phase 1: Foundational

- [X] T001 {FR-007} Create kit files directory and static content at `backend/src/binocular/module_kit/` → exports: CONTRACT_REFERENCE.md, STARTER_TEMPLATE.py, EXAMPLE_MODULE.py, AI_INSTRUCTIONS.md
- [X] T002 {FR-002,FR-003} Create module kit API router at `backend/src/binocular/routes/module_kit.py` ← T001 → exports: router
- [X] T003 Register module_kit router in `backend/src/binocular/routes/__init__.py` ← T002:router

## Phase 2: US1 — View Module Creation Guidance 🎯 MVP

- [X] T004 [P] [US1] {FR-001,FR-006} Create ModuleGuidanceSection component at `frontend/src/components/modules/ModuleGuidanceSection.tsx`
- [X] T005 [US1] {FR-001} Integrate ModuleGuidanceSection into ModulesPage at `frontend/src/components/modules/ModulesPage.tsx` ← T004

## Phase 3: US2 — Download AI Module Kit 🎯 MVP

- [X] T006 [US2] {FR-008} Write self-contained AI instructions file at `backend/src/binocular/module_kit/AI_INSTRUCTIONS.md` after:T001
- [X] T007 [US2] {FR-002} Add kit file download links to ModuleGuidanceSection at `frontend/src/components/modules/ModuleGuidanceSection.tsx` after:T003

## Phase 4: US3 — Copy Validation Errors for AI 🎯 MVP

- [X] T008 [P] [US3] {FR-005} Create copyErrorsForAI utility at `frontend/src/components/modules/copyErrorsForAI.ts` → exports: formatErrorsForAI(), copyErrorsToClipboard()
- [X] T009 [US3] {FR-004,FR-005} [COMPLETES FR-004] [COMPLETES FR-005] Add "Copy errors for AI" button to ValidationSummary in `frontend/src/components/modules/ModulesPage.tsx` ← T008

## Phase 5: US4 — Collapsible Guidance Section

- [X] T010 [US4] Update ModuleGuidanceSection with collapsible behavior and session persistence at `frontend/src/components/modules/ModuleGuidanceSection.tsx` after:T005

## Phase 6: Polish & Cross-Cutting

- [X] T011 [P] Write backend unit tests for kit endpoints at `backend/tests/test_module_kit.py` after:T003
- [X] T012 [P] Write frontend tests for ModuleGuidanceSection and copy utility at `frontend/src/components/modules/__tests__/` after:T009
- [X] T013 Run full lint/type-check/test suite: `mypy --strict`, `tsc`, `ruff`, `biome`, `pytest`, `vitest` after:T011
