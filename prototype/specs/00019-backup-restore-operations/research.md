## Research Report

**Context**: SQLite live-safe backup scheduling and restore runbook patterns for a self-hosted homelab Python/FastAPI app using APScheduler and aiosqlite.

## SQLite Online Backup API

- **Key findings**: `sqlite3.Connection.backup(target)` (PEP 249 extension, Python 3.7+) copies a live WAL-mode database page-by-page without locking out readers. Safe under concurrent load; produces a consistent single-file `.db` snapshot. Already used in `binocular/db/backup.py` via `asyncio.to_thread`. Using `VACUUM INTO` is an alternative — smaller output but locks the source briefly; Online Backup API is preferred for non-blocking homelab use.
- **Recommended**: Keep `sqlite3.Connection.backup()` in a thread pool as already implemented. Add retention pruning (keep N most-recent files) to avoid unbounded backup directory growth.
- **Avoid**: Plain `cp` / `shutil.copy` of the WAL-mode file under load — WAL + SHM files can be inconsistent. Do not call `PRAGMA wal_checkpoint(TRUNCATE)` in the backup job (affects write concurrency during checkpoint).
### Sources
- https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup — Python official docs for the backup API

## APScheduler Interval Job for Backup

- **Key findings**: APScheduler 3.x `BackgroundScheduler` / `AsyncIOScheduler` supports `add_job(func, 'interval', hours=N)` for periodic tasks. The existing scheduler service (E011) already wraps APScheduler for device-type checks; the backup job follows the same pattern. `misfire_grace_time` prevents stale-trigger double-runs after a restart.
- **Recommended**: Add the backup job to the existing APScheduler instance at app startup (lifespan). Use `replace_existing=True` and a stable `id='backup_job'` so restarts do not duplicate job registrations. Default interval: 24 hours. Make it opt-in/configurable via an env var (`BINOCULAR_BACKUP_SCHEDULE_HOURS`); default enabled since the feature exists specifically to provide this capability.
- **Avoid**: Creating a second scheduler instance; use the one established by E011. Do not persist job store to SQLite (the DB being backed up) — in-memory job store is fine for a restartable interval job.
### Sources
- https://apscheduler.readthedocs.io/en/3.x/userguide.html — APScheduler user guide

## Backup Retention Policy

- **Key findings**: For homelab single-user use, a rolling window of N files (e.g., 7 daily snapshots) is standard. Pruning by count (keep most-recent N) is simpler than time-based TTL and avoids clock-skew issues. Operator can supplement with offsite copy (NAS, second disk).
- **Recommended**: Default `BINOCULAR_BACKUP_RETENTION_COUNT=7`. Prune after each successful backup: list files matching `binocular-*.db` in the backup dir, sort by name (timestamps sort lexicographically), delete oldest beyond the limit.
- **Avoid**: Unbounded retention — fills operator's disk silently. Deleting all backups before confirming the new one succeeded.
### Sources
- https://www.sqlite.org/backup.html — SQLite backup documentation

## Restore Runbook

- **Key findings**: SQLite restore is: stop service → replace DB file → remove stale `-wal`/`-shm` → start. The Binocular startup migration runner already calls `PRAGMA integrity_check` implicitly via migration queries. A markdown runbook with exact commands is the canonical homelab approach.
- **Recommended**: Publish a `RESTORE.md` at the repo root (or `docs/restore.md`) with: (1) stop container, (2) copy backup over `/app/data/binocular.db`, (3) remove `-wal`/`-shm`, (4) start container, (5) verify `/healthz`. Include a section for rollback-after-migration.
- **Avoid**: Restoring while the container is running (WAL writes will corrupt). Forgetting to remove `-wal`/`-shm` stale files from the previous WAL session.
### Sources
- https://www.sqlite.org/howtocorrupt.html — SQLite corruption pitfalls

### Summary

The backup foundation (`db/backup.py`, config `backup_dir`) is already in place. E019 needs: (1) wire the backup job into APScheduler at startup with configurable interval and retention, (2) expose a `/api/v1/backups` status endpoint, and (3) ship a restore runbook. Retention pruning and configurable schedule interval are the two highest-impact additions beyond what already exists.

### Sources Index

| URL | Topic | Fetched |
|-----|-------|---------|
| https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup | SQLite Online Backup API | 2026-06-01 |
| https://apscheduler.readthedocs.io/en/3.x/userguide.html | APScheduler interval jobs | 2026-06-01 |
| https://www.sqlite.org/backup.html | SQLite backup patterns | 2026-06-01 |
| https://www.sqlite.org/howtocorrupt.html | Restore safety | 2026-06-01 |
