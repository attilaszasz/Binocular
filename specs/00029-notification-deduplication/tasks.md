# Tasks: Notification Deduplication

**Input**: Design documents from `specs/00029-notification-deduplication/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`, `data-model.md`

**Tests**: Included — the plan's Testing Strategy requires ≥80% coverage on new/changed lines.

## Project Mode

`Brownfield` — extends existing `devices` table schema, `CheckService.run_device_check()`, and `InventoryRepository`. No generic bootstrap tasks.

## Brownfield Notes

- Existing flows touched: `CheckService.run_device_check()`, `CheckService.run_all_device_checks()`, `SchedulerService._run_scheduled_check()`, `routes/checks.py`, `InventoryRepository`
- Compatibility: migration 009 adds nullable column — existing devices get NULL, treated as "never notified" per FR-003
- Regression focus: existing check-result persistence, notification format/content (FR-007 — no task needed; dedup gates dispatch without altering format), scheduler behavior, manual check endpoints

---

## Phase 1: Foundational

- [X] T001 {FR-001} Create migration `backend/src/binocular/db/migrations/009_add_last_notified_version.sql` adding `last_notified_version TEXT DEFAULT NULL`
- [X] T002 {FR-001} Add `last_notified_version: str | None` to `DeviceRecord` and update `_record_from_row()` via `_optional_text()` in `backend/src/binocular/repositories/inventory.py`
- [X] T003 {FR-001} Update SELECT in `get_device()` and `list_active_devices()` to include `d.last_notified_version` in `backend/src/binocular/repositories/inventory.py` after:T002
- [X] T004 {FR-001,FR-004} [COMPLETES FR-001] Add `record_notification_dispatched(device_id, version) -> int` with UPDATE setter in `backend/src/binocular/repositories/inventory.py` after:T002
- [X] T005 {FR-008} Add `get_device_for_update(device_id)` wrapping `BEGIN IMMEDIATE` + `SELECT` lock in `backend/src/binocular/repositories/inventory.py` after:T002

---

## Phase 2: US1 - Suppress Duplicate Notifications (Priority: P1) 🎯 MVP

- [X] T006 [US1] {FR-002,FR-003} Write tests in `backend/tests/test_notification_deduplication.py`: first detection notifies, re-detection suppresses, newer version notifies
- [X] T007 [US1] {FR-010} Add `trigger` param to `CheckService.run_device_check()` and propagate through `run_all_device_checks()`, `routes/checks.py`, and `scheduler.py`
- [X] T008 [US1] {FR-002,FR-003,FR-008} Implement dedup gate: `get_device_for_update()` → `compare_versions()` gate → conditional dispatch in `backend/src/binocular/services/checks.py` after:T005,T007
- [X] T009 [US1] {FR-009,FR-010,FR-011} [COMPLETES FR-009,FR-010,FR-011] Add structlog INFO: `check_initiated`, `notification_dedup_decision`, `last_notified_version_updated` in `backend/src/binocular/services/checks.py`
- [X] T010 [US1] {FR-004} [COMPLETES FR-004] Wire `record_notification_dispatched()` after `send_notification()` returns `True` in `backend/src/binocular/services/checks.py` after:T004,T008

---

## Phase 3: US2 - Manual Checks Respect Deduplication (Priority: P1) 🎯 MVP

- [X] T011 [US2] {FR-006} Write tests in `backend/tests/test_notification_deduplication.py`: manual check after scheduled does not re-notify, manual check detects newer version
- [X] T012 [US2] {FR-006} [COMPLETES FR-006] Verify `trigger="manual"` in `run_all_device_checks()` and routes, `trigger="scheduled"` in scheduler calls

---

## Phase 4: US3 - Preserve Notification on Dispatch Failure (Priority: P1) 🎯 MVP

- [X] T013 [US3] {FR-005} Write tests in `backend/tests/test_notification_deduplication.py`: all channels fail, zero channels, partial success leaves `last_notified_version` updated
- [X] T014 [US3] {FR-005} [COMPLETES FR-005] Add zero-channels guard: skip dispatch and log WARNING; add failure logging on `send_notification()` `False` in `backend/src/binocular/services/checks.py` after:T010

---

## Dependencies

Foundational → US1 → US2 → US3

- T001–T005 must complete before Phase 2.
- T006–T010 must complete before Phase 3 tests (T011) and Phase 4 (T014).
- T011–T012 can proceed in parallel with T013 (both depend on T010).
- Tasks with `after:T###` depend on the referenced task being `[X]` before execution.
