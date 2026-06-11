**Project Mode**: Brownfield
**Epic / Capability Map**: E014 → CAP-007 (Notification & Alerting)

## Phase 1: Database Setup

- [x] T001 {FR-002,FR-005} Create migration file `backend/src/binocular/db/migrations/0005_notifications.sql` adding `last_notified_version` column to `devices` table and creating `notification_channels` table.

## Phase 2: Repository and Notifier Services

- [x] T002 {FR-002} Create `backend/src/binocular/db/notifications_repository.py` for database CRUD operations on `notification_channels`.
- [x] T003 {FR-004} Create HTML email responsive Jinja2 template at `backend/src/binocular/templates/email.html`.
- [x] T004 {FR-004} Create `backend/src/binocular/services/email_renderer.py` to compile responsive HTML templates using Jinja2.
- [x] T005 {FR-003} Create `backend/src/binocular/services/notifier.py` implementing `NotifierService` wrapper around Apprise supporting SMTP and Gotify.

## Phase 3: Integration into CheckService & API Routes

- [x] T006 {FR-003,FR-005,FR-006,FR-008} Update `CheckService.check_device` in `backend/src/binocular/services/checks.py` to trigger update alerts, check `last_notified_version`, update it upon successful alert dispatch, and log delivery failures to the activity log.
- [x] T007 {FR-001,FR-007} Create route module `backend/src/binocular/routes/notifications.py` exposing GET, PUT, and POST `/api/v1/notifications/test`, and register it in `backend/src/binocular/routes/__init__.py`.

## Phase 4: Backend Tests

- [x] T008 {FR-001,FR-002,FR-003,FR-004,FR-005,FR-006,FR-007,FR-008} Create `backend/tests/test_notifications.py` to cover DB schema operations, API endpoints, email rendering, Apprise notifier, and check-runner deduplication logic.

## Phase 5: Frontend Settings UI

- [x] T009 {FR-001,FR-007} Implement SMTP and Gotify settings forms and test dispatch buttons in `frontend/src/pages/settings.tsx`.
