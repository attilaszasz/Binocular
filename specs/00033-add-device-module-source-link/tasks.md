# Tasks: Add Device Module Source Link

**Project Mode**: brownfield
**Epic**: E030 — {PRD:CAP-001}{PRD:CAP-002}{SAD:ADR-0013}

## Dependencies

| Phase | Depends On | Purpose |
|-------|------------|---------|
| Phase 1: Foundational | — | Persist and serialize source metadata. |
| Phase 2: User Story 1 | Phase 1 | Render selected module source link. |
| Phase 3: User Story 2 | Phase 1 | Validate and seed optional declarations. |
| Phase 4: Polish | Phases 2–3 | Run full regression verification. |

## Phase 1: Foundational

- [X] T001 {FR-002} Add nullable source_url migration in backend/src/binocular/db/migrations/0008_module_source_url.sql → exports: modules.source_url
- [X] T002 {FR-001} Extract optional SOURCE_URL in backend/src/binocular/extensions/{contract,loader}.py after:T001 → exports: LoadResult.source_url
- [X] T003 {FR-002} Persist source_url in backend/src/binocular/extensions/repository.py after:T002 → exports: ModuleRepository.create(),update()
- [X] T004 {FR-003} Add source_url to ModuleResponse and module API in backend/src/binocular/{devices/models.py,routes/modules.py} after:T003 → exports: ModuleResponse.source_url

## Phase 2: User Story 1 - Locate the Module Source 🎯 MVP

- [X] T005 [US1] {FR-004} Add source_url to Module type in frontend/src/lib/api.ts after:T004 → exports: Module.source_url
- [X] T006 [US1] {FR-004} Add selected-module source link states to frontend/src/components/inventory/device-form.test.tsx after:T005
- [X] T007 [US1] {FR-004} Render non-empty selected source link in frontend/src/components/inventory/device-form.tsx after:T006 ← T005:Module.source_url [COMPLETES FR-004]

## Phase 3: User Story 2 - Declare Source Metadata

- [X] T008 [US2] {FR-001} Add loader tests for declared and absent SOURCE_URL in backend/tests/extensions/test_loader.py after:T002
- [X] T009 [US2] {FR-002,FR-003} Add repository and modules API source_url tests in backend/tests/{extensions,routes}/ after:T004
- [X] T010 [US2] {FR-002} Persist source_url in upload and official seeder paths in backend/src/binocular/{routes/modules.py,services/seeder.py} after:T003 [COMPLETES FR-002]
- [X] T011 [US2] {FR-005} Declare canonical SOURCE_URL values in backend/src/binocular/official_modules/*.py after:T010 [COMPLETES FR-005]

## Phase 4: Polish & Cross-Cutting Concerns

- [X] T012 Run backend and frontend regression suites and strict type checks after:T007,T011
