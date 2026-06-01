# QC Report: Backup & Restore Operations

**Feature**: `00019-backup-restore-operations`
**Date**: 2026-06-01T14:47:00Z
**Run Type**: Full run (no prior report)

## Overall Verdict: PASS ✅

---

## Test Results

| Runner | Total | Passed | Failed | Skipped |
|--------|-------|--------|--------|---------|
| pytest (asyncio) | 155 | 155 | 0 | 0 |

**New tests added**: 28 (across `test_config.py`, `test_scheduler_service.py`, `test_backup_service.py`, `test_backups_routes.py`)

---

## Code Coverage

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Total coverage | 87.05% | 80% | ✅ PASS |
| `services/backup.py` | 96% | — | ✅ |
| `routes/backups.py` | 100% | — | ✅ |
| `config.py` | 98% | — | ✅ |

**Uncovered** (non-critical): `services/backup.py:73-74` (prune iteration over empty list — defensive path), `services/scheduler.py:103-164` (existing check execution code — not part of E019).

---

## Static Analysis

| Tool | Status | Issues |
|------|--------|--------|
| ruff | ✅ PASS | 0 errors (1 E501 fixed during QC) |
| mypy --strict | ✅ PASS | 0 errors in 49 source files |

---

## Security Audit

| Tool | Status | Findings |
|------|--------|---------|
| pip-audit | ✅ PASS | No known vulnerabilities found |

---

## PI Compliance

| Principle | Status | Evidence |
|-----------|--------|---------|
| I. Honest Failure | ✅ PASS | `backup_failed` error event logged; failures leave existing snapshots intact (tested) |
| III. Data Ownership | ✅ PASS | Snapshots stay in `/app/data` volume; no external dependency |
| IV. Least-Privilege | ✅ PASS | No new privileges; backup subdir created on demand |
| V. Type Safety | ✅ PASS | mypy --strict: 0 errors across 49 source files |
| VI. Set-and-forget | ✅ PASS | 24h/7-snapshot defaults enabled out of box; `BINOCULAR_BACKUP_SCHEDULE_HOURS=0` to disable |

**No PI violations found.**

---

## Requirements Traceability

| Req ID | Status | Tasks | Evidence |
|--------|--------|-------|---------|
| OR-001 | ✅ PASS | T005, T009 | `BackupService.run_backup()` creates `.db` in `scheduled/`; `test_run_backup_creates_file_in_scheduled_subdir` |
| OR-002 | ✅ PASS | T006, T009 | `_prune_old_snapshots()` deletes oldest N+; `test_run_backup_prunes_oldest_beyond_retention` |
| OR-003 | ✅ PASS | T007 | structlog events `backup_started`, `backup_succeeded`, `backup_failed`, `backup_prune_failed` present in code |
| OR-004 | ✅ PASS | T010-T012 | `GET /api/v1/backups` → 200, `BackupStatusResponse`; 4 route tests pass |
| OR-005 | ✅ PASS | T001, T015 | `backup_schedule_hours: int = Field(default=24, ge=0)`; compose.yaml doc comment added |
| OR-006 | ✅ PASS | T001 | Default 24h, retention 7 in Settings |
| OR-007 | ✅ PASS | T003, T008 | Scheduler guard `if hours > 0`; backup job wired in `app.py` lifespan |
| OR-008 | ✅ PASS | T009 | `test_run_backup_failure_leaves_existing_snapshots_intact` — prune only runs after successful backup |
| RR-001 | ✅ PASS | T013 | `docs/restore.md` — step-by-step restore procedure including WAL/SHM removal and `/healthz` check |
| RR-002 | ✅ PASS | T014 | `docs/restore.md` — Rollback After Migration section with forward-only migration note |

---

## Success Criteria

| SC | Status | Evidence |
|----|--------|---------|
| SC-001 [OBJ1] | ✅ PASS | `test_run_backup_creates_file_in_scheduled_subdir` — snapshot in `scheduled/` verified |
| SC-002 [OBJ1] | ✅ PASS | `test_run_backup_prunes_oldest_beyond_retention` — N files remain after N+1 backups |
| SC-003 [OBJ2] | ✅ PASS | `test_get_backups_returns_200_with_empty_snapshots_on_fresh_dir` — HTTP 200; filesystem-only response is O(n snapshots), well under 200ms |
| SC-004 [OBJ3] | ✅ PASS | `docs/restore.md` exists; procedure ends with `curl -f http://localhost:8000/healthz` |
| SC-005 [OBJ1] | ✅ PASS | `test_run_backup_failure_leaves_existing_snapshots_intact` — OSError on create_backup_snapshot; existing snapshots present after failure |

---

## Traceability Gaps

None.

---

## Performance

SC-003 specifies response under 200ms. `GET /api/v1/backups` performs only synchronous filesystem iteration (no DB query). In tests: ~5ms. Performance NFR: PASS.

---

## Accessibility

Not applicable (pure backend API feature).

---

## Browser Runtime Validation

Not required — backend API, no UI changes.

---

## Manual Testing

Not required for this iteration.

---

## Checklist Fulfillment

No checklists generated (skip_checklist=true per epic hint).

---

## Architecture Decision Note (AD-001 Adaptation)

Plan AD-001 intended to add the backup job to the existing `SchedulerService` instance. However, `SchedulerService` was not wired into `app.py`'s lifespan (E011 left this incomplete). The implementation adapted to use a standalone `AsyncIOScheduler` in `app.py`'s lifespan, which:
- Avoids any dependency on E011's incomplete wiring
- Is functionally equivalent (same APScheduler behavior, same `IntervalTrigger`)
- Is the pattern used by `SchedulerService` internally
- Does not create scheduling conflicts (backup job is independent of check jobs)
- `SchedulerService.add_backup_job()` is still implemented and tested, enabling future consolidation

This adaptation is recorded as `IMPLEMENTATION_DEVIATION` from AD-001 — not a violation.

---

## Tool Recommendations

None.

---

## Bug Tasks Generated

None.
