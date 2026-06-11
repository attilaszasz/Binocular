# Technical Research: Backup & Restore Operations

## SQLite Live Backup (VACUUM INTO)
Using SQLite's `VACUUM INTO 'filename'` command is the standard way to create a consistent, live-safe copy of an active SQLite database. Unlike a simple OS copy, `VACUUM INTO` is fully transaction-safe and runs without locking out active database writers. It constructs a fresh, defragmented copy of the database at the target location.
- **Source**: SQLite Vacuum Documentation (sqlite.org/lang_vacuum.html)

## WAL-Coupling Caveats
When SQLite operates in WAL (Write-Ahead Logging) mode, active transactions and uncommitted pages are stored in separate `-wal` and `-shm` files. Copying only the primary `.db` file from a running instance can result in a corrupted or stale backup because the WAL data is missing. `VACUUM INTO` processes all outstanding WAL entries and checkpoints them into the single output database file, completely decoupling the backup from the source WAL files.
- **Source**: SQLite WAL Documentation (sqlite.org/wal.html)

## APScheduler Backup Job
Integrating scheduled operations inside FastAPI is reliably managed using APScheduler. By scheduling a nightly background job on startup, the application performs automated self-contained backups to a configurable local folder. This avoids needing external cron containers or system dependencies.
- **Source**: APScheduler User Guide (apscheduler.readthedocs.io)
