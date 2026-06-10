# Tasks: Notification & Alerting

**Input**: Design documents from `specs/00017-notification-alerting-apprise/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`, `contracts/`
**Tests**: Required because SC-001 through SC-004 must be verified in full.

## Project Mode

`Brownfield`

## Epic / Capability Map

- `[US1]` → Configure Notification Channels
- `[US2]` → Test Channels from the UI
- `[US3]` → Automatic Alerting on Detection

## Brownfield Notes

- Existing flows touched: FastAPI app state/lifespan, routes aggregator, `CheckService` detection post-hooks, config loading, and frontend layout settings views.
- Compatibility or migration concerns: add database migration `005_notification_channels.sql`; backend dependency `apprise` is already in pyproject.toml or needs verification.
- Regression focus: backend startup, inventory check triggers, database connection locks, and settings rendering.

## Phase 1: Setup (Repository / Workspace Delta)

- [x] T001 Verify `apprise` is installed or add it to backend dependency configuration in backend/pyproject.toml

---

## Phase 2: Foundational (Cross-Work-Item Blockers)

- [x] T002 Add database migration `005_notification_channels.sql` creating the `notification_channels` table in backend/src/binocular/db/migrations/
- [x] T003 {FR-008} Add masking utility function in backend/src/binocular/utils/masking.py → exports: mask_secret()
- [x] T004 {FR-003,FR-008} Add notifications repository tests in backend/tests/test_notifications_repository.py
- [x] T005 {FR-003,FR-008} Add notifications repository in backend/src/binocular/repositories/notifications.py after:T002,T003 ← T002 ← T003 → exports: NotificationChannelRepository
- [x] T006 {FR-007,FR-010} Add notifier service tests in backend/tests/test_notifications_service.py after:T005
- [x] T007 {FR-007,FR-009,FR-010} Add notifier service in backend/src/binocular/services/notifications.py after:T006 ← T005 → exports: NotifierService

---

## Phase 3: Work Item 1 - Configure Notification Channels (Priority: P1) 🎯 MVP

- [x] T008 [US1] {FR-001,FR-002,FR-003,FR-004} Add notification configuration route tests in backend/tests/test_notifications_routes.py after:T007
- [x] T009 [US1] {FR-001,FR-002,FR-003,FR-004} Add notification configuration router in backend/src/binocular/routes/notifications.py after:T008 → exports: router
- [x] T010 [US1] {FR-001,FR-002,FR-003,FR-004} Register notification router in backend/src/binocular/routes/__init__.py or app aggregation factory after:T009
- [x] T011 [US1] Add frontend notification settings API in frontend/src/api/notifications.ts → exports: getChannels(), updateChannel()
- [x] T012 [US1] Add notification configuration UI view and controls in frontend/src/App.tsx after:T011

---

## Phase 4: Work Item 2 - Test Channels from the UI (Priority: P1) 🎯 MVP

- [x] T013 [US2] {FR-005} Add test notification route in backend/src/binocular/routes/notifications.py after:T009
- [x] T014 [US2] {FR-005} Add test notification API in frontend/src/api/notifications.ts after:T011 → exports: testChannel()
- [x] T015 [US2] {FR-005} Add "Send Test" button and state banners in frontend/src/App.tsx after:T012,T014

---

## Phase 5: Work Item 3 - Automatic Alerting on Detection (Priority: P1) 🎯 MVP

- [x] T016 [US3] {FR-006} Integrate NotifierService as a post-check hook in CheckService in backend/src/binocular/services/checks.py after:T007
- [x] T017 [US3] {FR-006,FR-010} Add unit and integration tests verifying CheckService calls NotifierService on `update_available` state transitions in backend/tests/test_checks_service.py after:T016
- [x] T018 [US3] {FR-006,FR-010} Verify outbound dispatch failures are caught, logged, and isolated from SQL transactions in backend/tests/test_checks_service.py after:T017

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T019 Run notification backend test suite and verify full coverage in backend
- [x] T020 Run full frontend integration and style verification for responsive layout in frontend

---

## Dependencies

Setup → Foundational → US1 configuration → US2 testing → US3 automatic alerting → Polish.

- T005 depends on T002, T003, T004.
- T007 depends on T006, T005.
- T009 depends on T008, T007.
- T010 depends on T009.
- T012 depends on T011.
- T013 depends on T009.
- T014 depends on T011.
- T015 depends on T012, T014.
- T016 depends on T007.
- T017 depends on T016.
- T018 depends on T017.
- T019 and T020 depend on T015, T018.
