---
feature_branch: "00019-backup-restore-operations"
spec: spec.md
plan: plan.md
---

# Tasks: Backup & Restore Operations

**Project Mode**: Brownfield
**Epic**: E019 — Backup & Restore Operations (P2, OPERATIONAL)

**Brownfield Notes**:
- **Patterns to reuse**: Route pattern from `routes/activity.py`; service pattern from `services/scheduler.py`; structlog event naming (`event_snake_case`); Pydantic `Field(alias=...)` with `populate_by_name=True`.
- **Tests to extend**: `test_scheduler_service.py` (add `add_backup_job`); `test_config.py` (new settings fields).
- **Naming conventions**: `snake_case` Python; camelCase Pydantic response aliases; `test_<module>.py`.

---

## Phase 1: Foundational — Config & Scheduler Extension

> Cross-objective blockers: new config fields used by all three objectives; scheduler extension needed by OBJ1 and OBJ2.

- [X] T001 Add `backup_schedule_hours: int = 24` and `backup_retention_count: int = 7` to `Settings` in `backend/src/binocular/config.py` {OR-005,OR-006} → exports: Settings.backup_schedule_hours, Settings.backup_retention_count, Settings.resolved_backup_dir
- [X] T002 Extend `test_config.py` to assert default values and `BINOCULAR_BACKUP_SCHEDULE_HOURS=0` disabling after:T001
- [X] T003 Add `add_backup_job(backup_svc, hours)` method to `SchedulerService` in `backend/src/binocular/services/scheduler.py` {OR-007} after:T001 → exports: SchedulerService.add_backup_job
- [X] T004 Extend `test_scheduler_service.py`: assert `add_backup_job` registers job when `hours > 0`, skips when `hours == 0` after:T003

---

## Phase 2: OBJ1 — Scheduled Live-Safe Backup Job 🎯 MVP

- [X] T005 [OBJ1] {OR-001} Create `BackupService` in `backend/src/binocular/services/backup.py` with `run_backup()` calling `create_backup_snapshot` from `db/backup.py` to `scheduled/` subdir after:T001 ← T001:Settings.resolved_backup_dir → exports: BackupService.run_backup, BackupService.list_snapshots
- [X] T006 [OBJ1] {OR-002} Add `_prune_old_snapshots()` to `BackupService`: list `binocular-*.db` in `scheduled/`, sort by name desc, delete oldest beyond `retention_count` after:T005 ← T005:BackupService
- [X] T007 [OBJ1] {OR-003} Add structlog events in `BackupService.run_backup()`: `backup_started`, `backup_succeeded` (path, size), `backup_failed` (error); `backup_prune_failed` warning in `_prune_old_snapshots` after:T006 ← T006:BackupService [COMPLETES OR-003]
- [X] T008 [OBJ1] {OR-007,OR-008} Wire `BackupService` into `app.py` lifespan: instantiate after migration runner; call `scheduler.add_backup_job(backup_svc, settings.backup_schedule_hours)` when `hours > 0` after:T003,T007 ← T003:SchedulerService.add_backup_job ← T007:BackupService [COMPLETES OR-007]
- [X] T009 [OBJ1] {OR-001,OR-002,OR-008} Write `test_backup_service.py`: unit-test `run_backup()` creates file in `scheduled/` subdir; prune deletes oldest beyond N; `hours=0` skips job registration; failure leaves existing snapshots intact after:T008

---

## Phase 3: OBJ2 — Backup Status API Endpoint 🎯 MVP

- [X] T010 [P] [OBJ2] {OR-004} Create `backend/src/binocular/routes/backups.py`: `GET /api/v1/backups` returning `BackupStatusResponse` (backupDir, scheduleHours, retentionCount, lastBackupAt, snapshots) after:T005 ← T005:BackupService.list_snapshots → exports: router
- [X] T011 [OBJ2] {OR-004} Register `backups_router` with prefix `/api/v1` in `backend/src/binocular/routes/__init__.py` after:T010 ← T010:router [COMPLETES OR-004]
- [X] T012 [OBJ2] {OR-004} Write `test_backups_routes.py`: `GET /api/v1/backups` returns 200 with empty snapshots list on fresh dir; returns snapshot list when files exist; returns 200 with correct scheduleHours and retentionCount from settings after:T011

---

## Phase 4: OBJ3 — Restore Runbook 🎯 MVP

- [X] T013 [OBJ3] {RR-001} Create `docs/restore.md`: restore runbook — stop container, identify snapshot in `data/backups/scheduled/`, copy to `/app/data/binocular.db`, remove `-wal`/`-shm`, start container, verify `/healthz` {RR-001}
- [X] T014 [OBJ3] {RR-002} Add rollback-after-migration section to `docs/restore.md`: use pre-migration snapshot from `data/backups/` (parent dir), note forward-only migration constraint, exact compose commands after:T013 [COMPLETES RR-002]
- [X] T015 [OBJ3] {OR-005} Add note to `.env.example` or `compose.yaml` documenting `BINOCULAR_BACKUP_SCHEDULE_HOURS` and `BINOCULAR_BACKUP_RETENTION_COUNT` env vars after:T001
