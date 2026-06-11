---
feature_branch: "00018-backup-restore-operations"
created: "2026-06-11"
input: "E018"
spec_type: "operational"
spec_maturity: "draft"
epic_id: "E018"
epic_sources: "{DOD:DDR-003}"
---

# Feature Specification: Backup & Restore Operations

**Feature Branch**: `00018-backup-restore-operations`  
**Created**: 2026-06-11  
**Status**: Draft  
**Spec Type**: operational  
**Spec Maturity**: draft  
**Epic ID**: E018  
**Epic Sources**: {DOD:DDR-003}  
**Product Document**: specs/prd.md  

## Problem Statement

To prevent data loss and ensure system resiliency, operators of self-hosted homelab applications need a reliable way to backup database state. Copying active SQLite files directly can result in corrupted copies if done during write transactions. A scheduled live-safe SQLite backup mechanism and clear restore instructions are required to guarantee data integrity and seamless disaster recovery.

## Scope

### Included

- Scheduled nightly database backup via `VACUUM INTO` on the integrated APScheduler instance.
- Configurable backup path via an environment variable (`BINOCULAR_BACKUP_DIR` / `backup_dir` setting) with a safe default.
- Manual database backup trigger endpoint (POST `/api/v1/backups/trigger`).
- Documentation detailing the restore process and WAL-coupling caveats in the README.

### Excluded

- Automatic backup rotation/cleanup — to keep the MVP simple and robust, managing storage limits (e.g. logrotate or volume management) is left to the operator.
- Direct cloud upload of backup archives — this is out of scope for the zero-config homelab MVP.
- Automatic restoration UI — restores must be performed manually by the operator following the runbook.

### Edge Cases & Boundaries

- **Concurrent Write Operations**: The backup must execute cleanly without blocking concurrent write operations on the main database, using `VACUUM INTO`.
- **Target Folder Missing**: The backup system must automatically create the target backup directory on startup or trigger if it doesn't already exist.
- **Disk Full**: The backup task must fail gracefully with appropriate error logging (using structlog) if the backup folder has insufficient space.

## Operational Objectives

### Objective 1 - Scheduled Nightly Backup (Priority: P1)

Establish a nightly background task inside APScheduler that creates a transactionally consistent copy of the database.

**Why this priority**: Core disaster recovery requirement to ensure data is periodically backed up automatically without human intervention.

**Rationale**: Nightly backups limit potential data loss to under 24 hours.

**Deliverables**:
- APScheduler job configured with cron-like execution (e.g., nightly at 02:00 UTC).
- Scheduled backup executor calling the backup logic.

**Verification Criteria**:
1. **Given** the scheduler is running, **When** the scheduled nightly time is reached, **Then** a backup database file named with timestamp suffix (e.g. `binocular_backup_YYYYMMDD_HHMMSS.db`) is created in the configured backup directory.

### Objective 2 - Manual Backup API Trigger (Priority: P1)

Provide an API route for on-demand backups.

**Why this priority**: Essential for operators to take a snapshot before manual updates, system moves, or configuration changes.

**Rationale**: On-demand manual backups let operators run backups immediately without waiting for the nightly cron or restarting the app.

**Deliverables**:
- POST `/api/v1/backups/trigger` API route.
- BackupService class wrapping `VACUUM INTO` operations.

**Verification Criteria**:
1. **Given** an active authenticated session, **When** a POST request is sent to `/api/v1/backups/trigger`, **Then** the backup is created and the API returns a HTTP 200/201 status with the filename.

### Objective 3 - Restore Runbook (Priority: P1)

Document the restore runbook and WAL-coupling caveats in detail.

**Why this priority**: Backups are useless if they cannot be restored, and WAL-coupling is a common point of failure for SQLite.

**Rationale**: SQLite's WAL journal mode requires specific handling to prevent active writes from corrupting copied files.

**Deliverables**:
- Restore runbook instructions added to the project README.md.

**Verification Criteria**:
1. **Given** a generated backup file, **When** the operator follows the restore procedure (stopping the app, replacing `binocular.db`, and removing any `-wal` and `-shm` files), **Then** the application starts successfully with all data restored.

### Operational Constraints

- Backups must be single-file SQLite databases created using the `VACUUM INTO` command, avoiding incomplete WAL/SHM copy issues.
- Backup location must default to `/app/data/backups` to persist within the standard Docker data volume.

## Integration Points

- **IP-001**: `BackupService` depends on `db/connection.py` to obtain the database path and connection for executing `VACUUM INTO`.
- **IP-002**: `SchedulerService` depends on `BackupService` to register the scheduled nightly job.

## Requirements

### Operational Requirements

- **OR-001**: The system MUST support configuring the backup storage directory via the environment variable `BINOCULAR_BACKUP_DIR`.
- **OR-002**: The nightly backup task MUST run every night at 2:00 AM UTC.
- **OR-003**: The nightly backup task MUST log success/failure states and execution duration via structured logging.
- **OR-004**: The POST `/api/v1/backups/trigger` endpoint MUST be protected by basic auth if basic auth is enabled in the settings.

### Runbook Requirements

- **RR-001**: The restore runbook MUST explicitly instruct the operator to stop the application before restoring to prevent corruption.
- **RR-002**: The restore runbook MUST warn the operator about deleting or renaming existing `.db-wal` and `.db-shm` files during restoration.

## Assumptions & Risks

### Assumptions

- The configured backup directory is writable by the process owner (UID/GID).
- The storage system backing the backup directory has enough space to hold multiple database backups.

### Risks

- **[Risk 1]** *(likelihood: low, impact: high)*: Backup directory fills up disk space over time. Mitigation: Explicitly document in the README that the operator should configure logrotate or a clean-up cron script.
- **[Risk 2]** *(likelihood: low, impact: medium)*: Backup execution fails mid-way due to lack of space. Mitigation: Perform `VACUUM INTO` to a temporary filename in the same directory, then rename to the final target name on success, preventing incomplete backup files.

## Implementation Signals

- `NEW-CONFIG` — Add `backup_dir` to `Settings` default `/app/data/backups` or `data_dir / "backups"`.
- `NEW-API` — Define POST `/api/v1/backups/trigger`.
- `NEW-WORKER` — Add scheduled nightly backup job to APScheduler.

## Success Criteria

### Measurable Outcomes

- **SC-001** [OBJ1]: Database backup runs automatically every night at 02:00 UTC and generates a valid, independent SQLite database file.
- **SC-002** [OBJ2]: The `/api/v1/backups/trigger` endpoint creates a backup within 5 seconds when invoked.
- **SC-003** [OBJ3]: Running the manual restore process on a test database recovers 100% of the device inventory, schedules, and configuration without error.
