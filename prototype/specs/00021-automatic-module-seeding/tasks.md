---
feature_branch: "main"
spec: spec.md
plan: plan.md
---

# Tasks: Automatic Module Seeding

**Project Mode**: Brownfield
**Epic**: E021 — Automatic Module Seeding (P2, TECHNICAL)

**Brownfield Notes**:
- **Patterns to reuse**: Validation and repository instantiation patterns from `routes/modules.py` and `app.py`; transactional committing from `services/modules.py`; logging style from `services/backup.py`.
- **Naming conventions**: `snake_case` Python naming; `test_seeder.py` for test module files.

---

## Phase 1: Foundational Seeding Infrastructure

> Discovers and statically validates bundled official starter modules on startup.

- [X] T001 [OBJ1] {TR-001} Implement packaged module discovery in `OfficialModuleSeeder` inside `backend/src/binocular/services/seeder.py` by dynamically resolving the `binocular/official_modules/` directory path.
- [X] T002 [OBJ1] {TR-002,TR-003} Implement static-only AST and metadata validation in `OfficialModuleSeeder` reusing `ModuleValidator` with `proof_input=None` and `scrape_client=None` to ensure fast offline startup.

---

## Phase 2: Seeding Execution & Database Integration

> Copies files to persistent volume and upserts records into the SQLite database.

- [X] T003 [OBJ2] {TR-004,TR-005} Add installation logic in `OfficialModuleSeeder` utilizing `ModuleLifecycleService.install_validated_module` (or equivalent file copy and repository upsert logic) to stage, validate, copy, and register official modules.
- [X] T004 [OBJ3] {TR-006,TR-007} Add version and hash change detection: skip seeding if the database version and file hash already match; overwrite files and update SQLite if bundled version is newer or hash differs.
- [X] T005 [OBJ3] {TR-008,TR-009} Implement transactional commit/rollback safety per module and catch all exceptions inside `OfficialModuleSeeder` so a single corrupted module does not crash startup.

---

## Phase 3: Integration & Lifespan Startup Hook

> Connects the seeding workflow to FastAPI lifecycles.

- [X] T006 {IP-001} Wire `OfficialModuleSeeder` execution inside `backend/src/binocular/app.py`'s `lifespan` function immediately after migrations run.

---

## Phase 4: Verification & Automated Tests

> Verifies functionality and guards against regressions.

- [X] T007 [OBJ1,OBJ2,OBJ3] {TR-010} Create automated tests in `backend/tests/test_seeder.py` covering: empty DB first-run, idempotent second-run, automatic upgrade on updated container image, and corrupted module fault isolation.
