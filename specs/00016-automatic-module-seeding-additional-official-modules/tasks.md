# Tasks: E016 — Automatic Module Seeding & Additional Official Modules

**Input**: Design documents from `specs/00016-automatic-module-seeding-additional-official-modules/`

## Phase 1: Foundational

- [x] T001 [P] [US1] {FR-007} Create Panasonic Lumix MFT Cameras module file at backend/src/binocular/official_modules/panasonic_lumix.py and its HTML fixture file at backend/tests/fixtures/panasonic_lumix/index.html
- [x] T002 [P] [US1] {FR-008} Create Panasonic Lumix Lenses module file at backend/src/binocular/official_modules/panasonic_lumix_lenses.py and its HTML fixture file at backend/tests/fixtures/panasonic_lumix_lenses/index5.html
- [x] T003 [P] [US1] {FR-009} Create Godox Flashes module file at backend/src/binocular/official_modules/godox_flashes.py and pagination HTML fixtures under backend/tests/fixtures/godox_flashes/
- [x] T004 [P] [US1] {FR-007,FR-008,FR-009} Write unit and fixture tests for the three new official modules at backend/tests/test_official_panasonic_lumix_module.py, backend/tests/test_official_panasonic_lumix_lenses_module.py, and backend/tests/test_official_godox_flashes_module.py

## Phase 2: Delivery

- [x] T005 [US1] {FR-001,FR-002,FR-003,FR-004,FR-006} Implement OfficialModuleSeeder service in backend/src/binocular/services/seeder.py to discover, statically validate, and upsert valid bundled modules
- [x] T006 [US1] {FR-001} Integrate OfficialModuleSeeder instantiation and execution in backend/src/binocular/app.py lifespan and export from backend/src/binocular/services/__init__.py
- [x] T007 [US2] {FR-005} Implement idempotency and version checks in OfficialModuleSeeder to prevent downgrading database or file modifications after:T005
- [x] T008 [US1,US2] {FR-001,FR-002,FR-003,FR-004,FR-005,FR-006} [COMPLETES FR-001] Write comprehensive integration and idempotency tests for OfficialModuleSeeder in backend/tests/test_seeder.py after:T006,T007
