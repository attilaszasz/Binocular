# Tasks: Environment-Based Notification Settings

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Project Mode
Brownfield

## Epic / Capability Map
E021 / CAP-007, CAP-009

## Phase 1: Config & Settings
- [x] T001 {TR-001} Update Settings class in backend/src/binocular/config.py to add SMTP, Gotify, and basic auth env var mappings with aliases.
- [x] T002 {TR-002} Update load_secret_files validator in backend/src/binocular/config.py to support non-prefixed file-based secrets.


## Phase 2: Seeder & Lifecycle
- [x] T003 {TR-004,TR-005} Implement NotificationSettingsSeeder in backend/src/binocular/services/settings_seeder.py to upsert settings into the database.
- [x] T004 {TR-003} Update FastAPI startup lifespan in backend/src/binocular/app.py to trigger NotificationSettingsSeeder after running database migrations.


## Phase 3: Testing & Polish
- [x] T005 {TR-001,TR-002,TR-003,TR-004,TR-005} Add unit and integration tests under backend/tests/ to verify configuration aliases, secrets files parsing, and startup seeding.
