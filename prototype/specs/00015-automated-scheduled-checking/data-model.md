# Data Model: Automated Scheduled Checking

## Entities

| Entity | Fields | Relationships | Validation / State |
|--------|--------|---------------|--------------------|
| DeviceTypeSchedule | `device_type_id`, `enabled`, `interval_minutes`, `next_run_at`, `last_started_at`, `last_completed_at`, `last_success_at`, `last_failure_at`, `last_failure_reason`, `last_skip_reason`, `updated_at` | One-to-one with `device_types.id` | `interval_minutes` positive and bounded; disabled schedules do not enqueue jobs. |
| ScheduledCheckRun | `device_type_id`, `started_at`, `completed_at`, `status`, `checked_count`, `failed_count`, `diagnostics` | Derived runtime result for a device type | Status values: `succeeded`, `partial_failed`, `failed`, `skipped`. Persist latest health on schedule row. |
| CheckResult | Existing check-result object | Produced per eligible device by E009/E010 service | Reused without changing status semantics. |

## Migration

| File | Change |
|------|--------|
| `backend/src/binocular/db/migrations/004_schedules.sql` | Add `device_type_schedules` with `device_type_id` unique FK to `device_types`, enabled flag, interval, scheduler health timestamps, and diagnostic fields. |

## Repository Operations

| Operation | Purpose |
|-----------|---------|
| `list_schedules()` | Return all device-type schedule rows joined to device type names. |
| `upsert_schedule()` | Persist UI changes before runtime rescheduling. |
| `record_run_started()` | Mark a schedule run active and update last-started state. |
| `record_run_finished()` | Persist success, partial failure, or failure health. |
| `record_run_skipped()` | Persist overlap/missed-run diagnostics visibly. |

## Invariants

- SQLite is the source of truth; APScheduler jobs are reconstructed from schedule rows.
- At most one active scheduled run per device type is allowed.
- Missed downtime windows are not stored as backlog rows.