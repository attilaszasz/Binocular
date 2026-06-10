---
feature_branch: "00019-backup-restore-operations"
created: "2026-06-01"
input: "E019 Backup & Restore Operations"
spec_type: "operational"
spec_maturity: "draft"
epic_id: "E019"
epic_sources: "{DOD:DDR-003}"
---

# Feature Specification: Backup & Restore Operations

**Feature Branch**: `00019-backup-restore-operations`
**Created**: 2026-06-01
**Status**: Draft
**Spec Type**: operational
**Spec Maturity**: draft
**Epic ID**: E019
**Epic Sources**: {DOD:DDR-003}
**Product Document**: specs/prd.md

## Problem Statement

Binocular stores all operator state in a single SQLite file, but no scheduled backup job ships with the application. If the data volume is lost or corrupted, the operator has no recovery path and must rebuild their entire device inventory and configuration from scratch. Without a live-safe backup mechanism and a documented restore procedure, the "set-and-forget reliability" and "data ownership" product promises are incomplete.

## Scope

### Included

- A scheduled APScheduler interval job that produces a live-safe SQLite snapshot using the Online Backup API (already in `db/backup.py`).
- Configurable backup schedule (interval in hours) and retention count (number of snapshots to keep) via environment variables.
- Automatic retention pruning: after each successful backup, old snapshots beyond the configured count are deleted.
- A `/api/v1/backups` status endpoint returning the backup directory path, last backup time, snapshot count, and total size.
- A documented restore runbook (`docs/restore.md`) with exact commands for stopping, replacing, and restarting the container.
- Integration with the existing APScheduler instance from E011 (same scheduler, new job).
- Log entries (structlog) on each backup start, success, failure, and prune.

### Excluded

- Offsite transfer (NAS copy, S3, rsync) — operator's responsibility; E019 produces local snapshots only.
- UI-managed backup configuration or a "back up now" button — configuration via environment variable; status read-only via API.
- Backup encryption at rest — operator's storage-layer concern, out of scope.
- Modules directory (`/app/modules`) backup — modules are operator-managed artifacts; restoring from a source or git repo is sufficient.
- Restore automation (API-triggered restore) — too risky without restart coordination; runbook only.

### Edge Cases & Boundaries

- If the backup directory does not exist, the job creates it (already handled by `create_backup_snapshot`).
- If a backup fails (disk full, permission error), the failure is logged and the existing snapshots are left intact.
- If the backup interval is 0 or unset with disabled flag, the scheduler job is not registered.
- If retention count is 0, no pruning occurs (unlimited retention).
- Prune only files matching the `binocular-*.db` glob in the backup directory; do not delete other operator files.
- The pre-migration snapshot (created by E004's migration runner at startup) is a separate artifact in the same directory and must not be pruned by the retention policy (different filename pattern or subdirectory).

## Operational Objectives

### Objective 1 - Scheduled Live-Safe Backup Job (Priority: P1)

Wire a nightly (configurable) APScheduler interval job that invokes `create_backup_snapshot` from `db/backup.py`, prunes old snapshots to the configured retention count, and logs outcomes to structlog.

**Why this priority**: Core of this epic — without a running backup job the RPO ≤ 24h target from DOD:DDR-003 cannot be met.

**Rationale**: The backup utility (`db/backup.py`) and config fields (`backup_dir`, `resolved_backup_dir`) already exist from E004. E019 only needs to schedule the job, add retention, and wire it into the app lifespan.

**Deliverables**:
- `backend/src/binocular/services/backup.py` — `BackupService` with `run_backup()` (creates snapshot, prunes, logs) and `list_snapshots()`.
- Wiring in `app.py` lifespan: register the APScheduler backup job when `backup_schedule_hours > 0`.
- Two new config fields: `backup_schedule_hours: int = 24` and `backup_retention_count: int = 7`.

**Verification Criteria**:
1. **Given** the app starts with default config, **When** the backup interval elapses, **Then** a timestamped `.db` file appears in the backup directory.
2. **Given** more snapshots exist than `backup_retention_count`, **When** a new backup completes, **Then** the oldest excess files are deleted.
3. **Given** `backup_schedule_hours = 0`, **When** the app starts, **Then** no backup job is registered and the app starts cleanly.
4. **Given** a backup job fails (simulated disk error), **When** the run completes, **Then** the failure is logged and existing snapshots are untouched.

### Objective 2 - Backup Status API Endpoint (Priority: P1)

Expose a read-only `/api/v1/backups` GET endpoint that returns current backup configuration and the list of existing snapshot files.

**Why this priority**: Operators need a way to verify backups are running without shelling into the container; the endpoint also enables future UI integration.

**Rationale**: Consistent with the existing pattern of exposing operational state via the API (schedules, activity log). Read-only is sufficient and safe.

**Deliverables**:
- `backend/src/binocular/routes/backups.py` — `GET /api/v1/backups` returning `BackupStatusResponse`.
- Router registration in `backend/src/binocular/routes/__init__.py`.

**Verification Criteria**:
1. **Given** no backups exist yet, **When** `GET /api/v1/backups` is called, **Then** the response includes an empty snapshot list and the configured backup directory.
2. **Given** snapshots exist, **When** `GET /api/v1/backups` is called, **Then** the response includes each snapshot filename, size, and timestamp.

### Objective 3 - Restore Runbook (Priority: P1)

Publish a documented, step-by-step restore procedure so operators can recover the database from any snapshot within the RTO ≤ 1h target.

**Why this priority**: A backup without a tested, documented restore procedure does not meet the DOD:DDR-003 acceptance criterion.

**Rationale**: Restore is a manual operation (container must stop for a clean file swap). A markdown runbook with exact Docker Compose commands is the appropriate homelab artifact.

**Deliverables**:
- `docs/restore.md` — step-by-step runbook: stop container → identify snapshot → replace DB file → remove stale WAL/SHM → start container → verify `/healthz` → post-restore integrity note.

**Verification Criteria**:
1. **Given** a backup snapshot file, **When** the restore runbook steps are followed in a test environment, **Then** the app starts, passes `/healthz`, and all data from the snapshot is accessible.
2. **Given** the runbook covers rollback-after-migration, **When** an operator rolls back an image tag that crossed a schema version, **Then** the runbook guides them to use the pre-migration snapshot.

### Operational Constraints

- Backup must not stop or lock the SQLite database during operation (Online Backup API guarantees this).
- Backup directory path defaults to `data/backups/` within the data volume — no additional volume mount required.
- Backup schedule interval and retention count must be configurable without a code change (env vars only).
- RPO ≤ 24h and RTO ≤ 1h targets from DOD:DDR-003 must be achievable with default settings.
- Pre-migration snapshots (created by E004 migration runner at startup) must not be pruned by the retention policy.

## Integration Points

- **IP-001**: Backup job depends on `db/backup.py::create_backup_snapshot` (E004) for the live-safe snapshot primitive.
- **IP-002**: Backup job integrates with the APScheduler instance established by E011's scheduler service; the job is added alongside existing device-type check jobs.
- **IP-003**: `BackupService` reads `Settings.resolved_backup_dir`, `backup_schedule_hours`, and `backup_retention_count` from the config system (E001/E013).
- **IP-004**: `/api/v1/backups` route follows the route+repository pattern established across all existing routes; no new repository is needed (filesystem-backed).

## Requirements

### Operational Requirements

- **OR-001**: System MUST produce a live-safe SQLite snapshot via the Online Backup API on each scheduled backup run.
- **OR-002**: System MUST prune backup snapshots beyond the configured retention count after each successful backup, preserving the most-recent N files.
- **OR-003**: System MUST log the outcome (success with path, failure with error) of every scheduled backup run via structlog.
- **OR-004**: System MUST expose a `GET /api/v1/backups` endpoint returning backup status and snapshot inventory.
- **OR-005**: System MUST allow configuring backup interval (hours) and retention count via environment variables without a code change.
- **OR-006**: System MUST default to a 24-hour backup interval and 7-snapshot retention when no configuration is provided.
- **OR-007**: System MUST NOT register the backup job when `BINOCULAR_BACKUP_SCHEDULE_HOURS=0`.
- **OR-008**: System MUST NOT prune pre-migration snapshot files produced by the E004 migration runner.

### Runbook Requirements

- **RR-001**: A runbook MUST exist for restoring the database from a backup snapshot, covering: stop container, replace DB file, remove stale WAL/SHM, start container, verify health.
- **RR-002**: A runbook MUST exist for rollback-after-migration, directing operators to use the pre-migration snapshot when rolling back across a schema change.

## Assumptions & Risks

### Assumptions

- The APScheduler instance from E011 is available at app lifespan startup; the backup job can be added alongside device-type check jobs.
- The backup directory (`data/backups/`) is within the same `/app/data` volume as the database — no additional mount is required.
- The operator runs on a platform where the backup directory is writable by the container's non-root user.
- Pre-migration snapshots use the filename pattern `binocular-<timestamp>.db` in the same backup dir — the retention pruner must target a distinct pattern or subdirectory to avoid deleting them.

### Risks

- **Pre-migration snapshot collision** *(likelihood: medium, impact: high)*: If E004's migration runner writes pre-migration snapshots to the same directory with the same filename pattern, the retention pruner could delete them. Mitigation: use a subdirectory (`backups/scheduled/`) for scheduled snapshots or use a distinct filename prefix.
- **Disk exhaustion** *(likelihood: low, impact: medium)*: If `backup_retention_count` is set very high or 0, backup files accumulate. Mitigation: default of 7 is conservative; log directory size on each run.
- **APScheduler job duplication** *(likelihood: low, impact: low)*: Re-registering the same job ID on restart. Mitigation: use `replace_existing=True` and a stable job ID `'binocular_backup'`.

## Implementation Signals

- `NEW-CONFIG` — Two new settings: `backup_schedule_hours` (int, default 24) and `backup_retention_count` (int, default 7) in `Settings`.
- `NEW-WORKER` — APScheduler interval job `'binocular_backup'` added to the existing scheduler at app lifespan startup.
- `NEW-API` — `GET /api/v1/backups` route and `BackupStatusResponse` Pydantic model.
- `NEW-ENTITY` — `BackupService` class in `services/backup.py` wrapping `create_backup_snapshot` and retention pruning.

## Success Criteria

### Measurable Outcomes

- **SC-001** [OBJ1]: A timestamped snapshot file exists in the backup directory within 24 hours of first app start with default configuration.
- **SC-002** [OBJ1]: After N+1 successful backups where N = `backup_retention_count`, only N files remain in the scheduled backup directory.
- **SC-003** [OBJ2]: `GET /api/v1/backups` returns HTTP 200 with a valid JSON body listing all current snapshots in under 200ms.
- **SC-004** [OBJ3]: Following the restore runbook from a test snapshot, the app starts and `/healthz` returns 200 within 60 seconds.
- **SC-005** [OBJ1]: A simulated backup failure logs a structured error event and leaves existing snapshots intact.

## Glossary

| Term | Definition |
|------|------------|
| Online Backup API | Python's `sqlite3.Connection.backup()` method — copies a live SQLite database page-by-page without blocking readers. |
| Pre-migration snapshot | An automatic backup taken by the E004 migration runner before applying pending schema migrations at startup. |
| WAL/SHM files | `binocular.db-wal` and `binocular.db-shm` — SQLite Write-Ahead Log files that must be removed before a restore to avoid corruption. |
| Retention count | The maximum number of scheduled backup snapshots kept on disk; older snapshots beyond this count are pruned. |

## Compliance Check

- No CRITICAL `project-instructions.md` violations detected.
- Spec type: operational. Requirements use `OR-###` and `RR-###` families. Integration Points section present. Mandatory sections complete.
