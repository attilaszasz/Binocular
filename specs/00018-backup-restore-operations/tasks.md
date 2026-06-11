**Project Mode**: Brownfield
**Epic / Capability Map**: E018 → {DOD:DDR-003} (Backup & Restore Operations)

## Phase 1: Backend Backup Service & Scheduling

- [x] T001 {OR-001} Add `backup_dir` setting to `backend/src/binocular/config.py` default to `data_dir / "backups"`.
- [x] T002 {OR-003} Create `BackupService` in `backend/src/binocular/services/backup.py` that implements transactionally consistent backup via SQLite `VACUUM INTO`.
- [x] T003 {OR-002} Schedule the nightly backup job to run at 02:00 UTC daily in `backend/src/binocular/services/scheduler.py`.
- [x] T004 {OR-003} Write unit tests for the `BackupService` database backup creation logic in `backend/tests/services/test_backup.py`.

## Phase 2: Router, Documentation & Integration Tests

- [x] T005 {OR-004} Create the manual backup API route in `backend/src/binocular/routes/backups.py` with `POST /api/v1/backups/trigger`.
- [x] T006 {OR-004} Include the backups router in `backend/src/binocular/routes/__init__.py`.
- [x] T007 {OR-004} Write routes integration tests in `backend/tests/routes/test_backups.py`.
- [x] T008 {RR-001,RR-002} Add the backup restore runbook and WAL-coupling caveats to `README.md`.
