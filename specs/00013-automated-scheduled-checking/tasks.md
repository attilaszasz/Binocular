**Project Mode**: Brownfield
**Epic / Capability Map**: E013 → CAP-004 (Automated Scheduled Checking)

## Phase 1: Setup & Database

- [x] T001 {FR-001} Add `apscheduler>=3.10.0,<4` dependency to `backend/pyproject.toml` and update local environment dependencies.
- [x] T002 {TR-001,FR-004} Create migration file `backend/src/binocular/db/migrations/0004_schedules.sql` defining the `schedules` table, the seeder for existing modules, and the trigger for new modules.

## Phase 2: Scheduler Service & API

- [x] T003 {TR-002,FR-001} Create `backend/src/binocular/services/scheduler.py` implementing `SchedulerService` wrapper for `AsyncIOScheduler` and scheduled check dispatching logic.
- [x] T004 {TR-002} Integrate `SchedulerService` lifecycle hooks in `backend/src/binocular/app.py` lifespan context.
- [x] T005 {FR-002,FR-003} Implement GET and PUT `/api/v1/schedules` endpoints in `backend/src/binocular/routes/modules.py` to allow querying and updating check frequencies.

## Phase 3: Verification (Tests)

- [x] T006 {TR-001,TR-002,FR-002,FR-003} Write backend tests under `backend/tests/` validating `SchedulerService` execution, resume behavior, and API routes.

## Phase 4: Frontend UI

- [x] T007 {FR-002,FR-003} Create `frontend/src/components/modules/FrequencyEditor.tsx` React component for editing module check frequency.
- [x] T008 {FR-002,FR-003} Embed `FrequencyEditor` inside `ModuleCard` at `frontend/src/components/modules/ModuleCard.tsx`.
