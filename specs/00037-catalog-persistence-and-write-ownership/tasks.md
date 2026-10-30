# Tasks: Catalog Persistence and Write Ownership

## Project Mode
Brownfield; no bootstrap. Paths: backend/src/binocular/ unless prefixed. Apply plan.md acceptance/writer matrices (SC-001–008), data-model.md; test-after.

## Phase 1: Foundational
- [X] T001 {TR-001} Make db/migrations.py atomically submit pending scripts/version after fatal backup; preserve shipped SQL.
- [X] T002 {TR-002,TR-003,TR-004,TR-005,TR-006,TR-007,TR-010,TR-011,TR-014} Add schema/backfills/guards in db/migrations/0011_catalog_foundation.sql.
- [X] T003 {TR-003,TR-011,TR-014,TR-015} Type records/attestation/sanitization in db/catalog_types.py → exports: canonical_variant_v1,canonical_version_v1,VerifiedIdentity
- [X] T004 {TR-008,TR-013} Add db/unit_of_work.py; adapt db/connection.py and db/repository.py → exports: WriteUnit
- [X] T005 Replace memory/partial schemas with migrated file fixtures in backend/tests/conftest.py and affected suites after:T004
- [X] T006 {TR-009,TR-013} Bind devices/repository.py, extensions/repository.py, db/activity_repository.py, db/notifications_repository.py to units ← T004:WriteUnit
- [X] T007 {TR-009} Refactor app.py, deps.py, devices/service.py, services/checks.py, services/scheduler.py, services/notifier.py and route writers to units.
- [X] T008 {TR-009} Refactor official_modules/canon_endpoint_cache.py, services/seeder.py, services/settings_seeder.py, services/backup.py; audit commit/execute paths.

T004–T008: WAL/FK/5000ms; rollback before commit submission, drain submitted commit, honest outcome/close. Bound repos never commit; standalone writes own units; network outside; lifespan reads only.

## Phase 2: OBJ1 — Identities (P1) 🎯 MVP
- [X] T009 [OBJ1] {TR-003,TR-004,TR-006,TR-014} Add metadata/exact resolver/complete-only missing status in db/catalog_repository.py after:T008 ← T003:VerifiedIdentity
- [X] T010 [OBJ1] {TR-005,TR-015} Persist independent attempts/success in db/observation_repository.py after:T008 ← T004:WriteUnit
- [X] T011 [OBJ1] {TR-006,TR-007} Add unknown/link/revision CAS in devices/models.py and devices/repository.py after:T009
- [X] T012 [OBJ1] {TR-007} Render unknown/incomparable in frontend/src/lib/api.ts and frontend/src/components/inventory/device-card.tsx; extend form/status tests.
- [X] T013 [OBJ1] {TR-001,TR-002} Test offline preservation, backup/early/late upgrade failure/reopen in backend/tests/db/test_catalog_migration.py after:T002
- [X] T014 [OBJ1] {TR-003,TR-004} [COMPLETES TR-003] [COMPLETES TR-004] Test variant/rename/alias/enumeration restart in backend/tests/db/test_catalog_identity.py
- [X] T015 [OBJ1] {TR-006,TR-014} [COMPLETES TR-006] [COMPLETES TR-014] Test attestation/raw SQL insert/update/parent guards in backend/tests/db/test_catalog_security.py

## Phase 3: OBJ2 — Ownership (P1) 🎯 MVP
- [X] T016 [OBJ2] {TR-008,TR-009} [COMPLETES TR-009] Test lifecycle/cancellation/busy/all-writer interleavings in backend/tests/db/test_write_ownership.py after:T008
- [X] T017 [OBJ2] {TR-007} Fence V1 results/alerts by captured revision/module/model/link/config in services/checks.py after:T011
- [X] T018 [OBJ2] {TR-007,TR-012} [COMPLETES TR-007] Extend backend/tests/services/test_checks.py and frontend/e2e/source-accessibility.spec.ts after:T012

## Phase 4: OBJ3 — Dormant work (P1) 🎯 MVP
- [X] T019 [OBJ3] {TR-010,TR-015} Persist refresh generations/budgets/cursors/leases/reservation CAS in db/work_repository.py after:T008 ← T004:WriteUnit
- [X] T020 [OBJ3] {TR-010} Add model-generation/device-revision reevaluation and bounded fenced chunks in db/work_repository.py.
- [X] T021 [OBJ3] {TR-005,TR-010} Add atomic APIs in db/observation_repository.py and db/work_repository.py after:T010 after:T011 → exports: record_success_and_enqueue,mutation_and_enqueue
- [X] T022 [OBJ3] {TR-011,TR-015} Add unique intents/immutable claims in db/delivery_repository.py after:T017 ← T003:canonical_version_v1 → exports: ensure_intent
- [X] T023 [OBJ3] {TR-011,TR-015} Add fenced transitions/evidence/quarantine/retry in db/delivery_repository.py ← T022:ensure_intent → exports: authorize_send,retry_uncertain
- [X] T024 [OBJ3] {TR-011} [COMPLETES TR-011] Test claims/all fences/late evidence/stopped-owner retry in backend/tests/db/test_catalog_delivery.py ← T023:authorize_send
- [X] T025 [OBJ3] {TR-005,TR-010,TR-012} [COMPLETES TR-005] Test rollback/restart/independent attempts-success/atomic work in backend/tests/db/test_catalog_work.py after:T021

## Phase 5: Polish
- [X] T026 {TR-013,TR-015} [COMPLETES TR-013] [COMPLETES TR-015] Test SQL/options and secret-free storage/logs in backend/tests/db/test_catalog_security.py after:T025
- [X] T027 {TR-010} [COMPLETES TR-010] Test 10,000-model default50/max100 pages/chunks, budgets/deadlines/WAL readers in backend/tests/db/test_catalog_performance.py after:T025
- [X] T028 {TR-012} [COMPLETES TR-012] Run gates; record evidence in specs/00037-catalog-persistence-and-write-ownership/validation-results.md after:T027

T026: unknown SQL options execute no SQL; zero unrelated changes/seeded credentials; sanitize before truncation/immutable insert, generic safe fallback.
T028: lint/static/security/coverage/accessibility/performance; backend/frontend ≥80%, official-module fixtures. Record cwd/command/exit/report. In backend/: uv run ruff check .; uv run mypy --strict .; uv run pytest --cov=binocular --cov-report=term-missing --cov-fail-under=80; uv run pip-audit. In frontend/: npm run lint; npm run typecheck; npm test -- --run --coverage; npm run build; npx playwright test. Root: docker build --load -t binocular:qc-check -f Dockerfile .; trivy image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 binocular:qc-check. Missing tools: NOT RUN/BLOCKED, rerun in capable CI; never invent PASS/QC markers.

## Dependencies
T001–T008 gate delivery; phases 2 → 3 → 4 → 5. IDs/after/import edges order work. Polish needs all objectives. No parallel batches or new workers/V1 work enqueue.

## Phase: Bug Fixes
- [X] T029 [BUG:CRITICAL] {TR-007} [pi-violation] Persist failed V1 attempt state and retain successful verification time — backend/src/binocular/devices/repository.py:121
  > Error: Failed checks advance last_checked while retaining current; after reload inventory renders Latest beside failed-attempt time.
  > Fix hint: Persist/expose failure separately from retained successful knowledge; add background-failure/reload assertions and correct existing retained-current tests.
- [X] T030 [BUG:CRITICAL] {TR-010} [pi-violation] Reject stale/failed observations as current during reevaluation — backend/src/binocular/db/work_repository.py:737
  > Error: Reevaluation checks config but not latest attempt outcome or observation age, promoting retained failed/stale knowledge to current/update_available/no_firmware.
  > Fix hint: Use supplied chunk clock and latest attempt eligibility; retain reference with failed/stale status and add expiry/failed-attempt regression tests.
- [X] T031 [BUG:ERROR] {TR-011} [requirement-gap] Reject execution UUID rebinding to unrelated task/process — backend/src/binocular/db/catalog_types.py:467
  > Error: dataclasses.replace(binding, task=completed_unrelated_task) retains registered owner/UUID; proof joins wrong execution while original may run.
  > Fix hint: Host-issued registration must bind identity to exact execution object; add same-UUID unrelated-execution test and fail closed on rebinding.
