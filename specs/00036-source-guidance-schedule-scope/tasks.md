# Tasks: Sources

**Project Mode**: Brownfield. B/ = backend/src/binocular/; F/ = frontend/src/.
**Tests**: FR-020, test-after per policy; quickstart.md matrix.

## Phase 1: Setup

- [X] T001 Pin TS5.9.3 in frontend/package{,-lock}.json; strict frontend/tsconfig.node.json; remove ignoreDeprecations6; npm ci/build.
- [X] T002 Configure v8/Playwright in frontend/{package.json,vite.config.ts,playwright.config.ts}; exclude e2e from Vitest; all-production 80% thresholds.

## Phase 2: Foundational

- [X] T003 {FR-001,FR-007,FR-009} Add bounded metadata/fallback parser in B/extensions/guidance.py → exports: SourceGuidance
- [X] T004 {FR-011} Add B/db/migrations/0010_source_guidance.sql, B/extensions/repository.py and B/devices/models.py fields; retain backup gate.
- [X] T005 {FR-010} Capture b1b8b99 shipped hashes before edits in B/services/official_provenance.py; protect unknown bytes → exports: guidance_provenance
- [X] T006 {FR-009,FR-010} Wire AST/runtime guidance in B/extensions/{contract,loader,validator}.py; ModuleResponse via B/routes/modules.py and F/lib/api.ts after:T003,T004,T005

## Phase 3: US1 — Choose a Firmware Source (P1) 🎯 MVP

- [X] T007 [US1] {FR-002,FR-003,FR-004} Add eight official-guidance.md declarations in B/official_modules/*.py; fix lens type; preserve URLs/matching.
- [X] T008 [US1] {FR-011} Protect seeding/backfill/upgrades in B/services/seeder.py; preserve state/custom bytes after:T005,T007
- [X] T009 [US1] {FR-002,FR-003,FR-004,FR-020} Extend backend/tests/test_official_*_module.py: eight declarations/fixtures, Canon exclusions/RF-S, near-match/no-firmware.
- [X] T010 [US1] {FR-016} Prioritize guidance, disclose internals in F/components/modules/ModuleCard.tsx; visible failures/last-success after:T006

## Phase 4: US2 — Enter a Source-Specific Model (P1) 🎯 MVP

- [X] T011 [US2] {FR-007} Validate links in F/lib/source-guidance.ts; omit unsafe/absent actions, noopener noreferrer → exports: safeSourceUrl
- [X] T012 [US2] {FR-005,FR-008} Add local describedby help/examples in F/components/inventory/SourceGuidance.tsx; separate Nikon human help/XML ← T011:safeSourceUrl
- [X] T013 [US2] {FR-005,FR-006,FR-014} Update F/components/inventory/device-form.tsx: add/edit source-first, free text, pause warning, stale reset; preserve typed values after:T012
- [X] T014 [US2] {FR-006,FR-007,FR-020} [COMPLETES FR-007] Extend F/components/inventory/device-form.test.tsx: stale success/error/finally/unmount, safe links, zero render requests.

## Phase 5: US3 — Understand Monitoring Scope (P1) 🎯 MVP

- [X] T015 [US3] {FR-012} Add summary counts/exact same-query ScopeResponse in B/routes/modules.py and F/lib/api.ts after:T004 → exports: ScopeResponse
- [X] T016 [US3] {FR-015} Add thread-safe entry generations in B/services/automatic_admission.py; no lock across I/O/execution → exports: AutomaticAdmission
- [X] T017 [US3] {FR-015} Gate dispatch/worker entry in B/services/checks.py and B/extensions/runner.py; manual bypass, neutral skips ← T016:AutomaticAdmission
- [X] T018 [US3] {FR-015} Wire active-only jobs/commit-before-pause response in B/services/scheduler.py and B/routes/modules.py; explicit resume after:T017
- [X] T019 [US3] {FR-012,FR-019} Invalidate old/new member queries in F/hooks/{use-devices,use-modules}.ts; focus/refresh; loading/failure not zero ← T015:ScopeResponse
- [X] T020 [US3] {FR-013,FR-014,FR-019} Add exact-member list/current-future scope in F/components/modules/{ModuleCard,FrequencyEditor}.tsx; truthful save states after:T010,T019
- [X] T021 [US3] {FR-015,FR-020} [COMPLETES FR-015] Extend backend/tests/services/test_scheduler.py: deterministic query/worker/pause-resume barriers, restart/edit/manual.
- [X] T022 [US3] {FR-012,FR-013} [COMPLETES FR-012] Add F/components/modules/ModuleCard.test.tsx, backend/tests/test_module_scope.py: zero/one/many/relink/delete/snapshot.

## Phase 6: US4 — Maintain Custom Sources (P2)

- [X] T023 [US4] {FR-011} Preserve replacement state in B/routes/modules.py; clear omitted guidance/official claims; no false save after:T008,T018
- [X] T024 [US4] {FR-017} Document bounds/V1 compatibility in B/module_kit/*; retain contract/kit/validation/AI/sharing after:T006
- [X] T025 [US4] {FR-017,FR-018} Update F/components/modules/{ModuleGuidanceSection,ModuleUploadForm}.tsx, F/pages/modules.tsx; accessible errors/disclosure, pre-import trust warning.
- [X] T026 [US4] {FR-009,FR-010,FR-011} [COMPLETES FR-009] [COMPLETES FR-010] [COMPLETES FR-011] Extend backend/tests/{test_migrations,test_seeder}.py: lifecycle/metadata matrix after:T023
- [X] T027 [US4] {FR-016,FR-017} [COMPLETES FR-017] Extend F/components/modules/{ModuleGuidanceSection,ModuleUploadForm}.test.tsx: kit/download/copy/share, validation/warning failures.

## Phase 7: Polish

- [X] T028 {FR-018} Add frontend/e2e/source-guidance.spec.ts: SC-001–SC-006, forms/scope/pause/disclosure/authoring, keyboard/labels/375px/desktop after:T022,T027
- [X] T029 {FR-018,FR-020} [COMPLETES FR-018] [COMPLETES FR-020] Run quickstart.md lint/strict/build/tests/80%/security/image/browser matrix; record actual evidence/blockers in quickstart.md. after:T030,T031,T032
- [X] T030 {FR-020} Repair container zero-padded root identity bypass and test rejected identities in backend/tests/test_entrypoint.py; retain policy-aligned image build and privilege dropping.
- [X] T031 {FR-012,FR-013} Refresh active inspected scope queries with source summaries; RTL and real browser external-membership regression.
- [X] T032 {FR-017,FR-018} Handle missing Clipboard API on HTTP LAN origins with visible manual-copy fallback; add upload regression.

## Dependencies

Setup → Foundational → US1 → US2 → US3 → US4 → Polish. MVP: US1–US3. Sequential; T005 before T007.
T026: all lifecycle/bounds; T021: all pause barriers; T028: isolated SQLite/modules, fixtures, no alerts (quickstart.md).

## Requirement Coverage Map

| Requirement | Tasks |
|---|---|
| FR-001 | T003 |
| FR-002 | T007,T009 |
| FR-003 | T007,T009 |
| FR-004 | T007,T009 |
| FR-005 | T012,T013 |
| FR-006 | T013,T014 |
| FR-007 | T003,T011,T014 |
| FR-008 | T012 |
| FR-009 | T003,T006,T026 |
| FR-010 | T005,T006,T026 |
| FR-011 | T004,T008,T023,T026 |
| FR-012 | T015,T019,T022 |
| FR-013 | T020,T022 |
| FR-014 | T013,T020 |
| FR-015 | T016,T017,T018,T021 |
| FR-016 | T010,T027 |
| FR-017 | T024,T025,T027 |
| FR-018 | T025,T028,T029 |
| FR-019 | T019,T020 |
| FR-020 | T009,T014,T021,T029 |

## Phase: Bug Fixes

- [X] T033 [BUG:ERROR] {FR-018} [requirement-gap] Give collapsed mobile navigation links persistent accessible names — frontend/src/components/layout/nav-item.tsx:23
  > Error: axe link-name: Inventory, Modules, Logs and Settings links have no accessible text at 375px.
  > Fix hint: Preserve label with aria-label or screen-reader text when collapsed; add mobile/collapsed accessibility regression.
- [X] T034 [BUG:ERROR] {FR-018} [requirement-gap] Correct light-theme source-card text contrast — frontend/src/components/modules/ModuleCard.tsx:66
  > Error: axe color-contrast: Official 3.33:1, active 3.31:1, Healthy 2.47:1; small text requires 4.5:1.
  > Fix hint: Adjust light-theme foreground/background pairs in ModuleCard.tsx:66,107 and ModuleStatusBadge.tsx:11; retain readable dark-theme states and add browser contrast regression.
