# Data Model Design: Automated Scheduled Checking

This document specifies the database updates required to support automated scheduled checks per module.

## Database Migrations

A new migration file `0004_schedules.sql` will be added to `backend/src/binocular/db/migrations/`.

### Migration SQL: `0004_schedules.sql`

```sql
-- Migration 0004: Schedules table for automated checks
-- Creates the schedules table which links each module to an interval.

CREATE TABLE IF NOT EXISTS schedules (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id      INTEGER NOT NULL UNIQUE REFERENCES modules(id) ON DELETE CASCADE,
    interval_hours INTEGER NOT NULL DEFAULT 24 CHECK(interval_hours > 0),
    last_run       TEXT, -- ISO 8601 UTC timestamp of last check run
    next_run       TEXT, -- ISO 8601 UTC timestamp of next scheduled check run
    created_at     TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Trigger to auto-initialize schedule for newly created modules.
CREATE TRIGGER IF NOT EXISTS init_module_schedule
AFTER INSERT ON modules
BEGIN
    INSERT INTO schedules (module_id, interval_hours, next_run)
    VALUES (NEW.id, 24, datetime('now'));
END;
```

Wait, does the seeder or repository handle inserts? An `AFTER INSERT` trigger on the `modules` table is extremely elegant and guarantees that any new module (either seeded or uploaded) gets a default schedule created automatically! This is standard and beautiful.
Let's make sure it handles existing modules during migration:
```sql
-- Seed schedules for existing modules if they do not exist
INSERT OR IGNORE INTO schedules (module_id, interval_hours, next_run)
SELECT id, 24, datetime('now') FROM modules;
```
Yes! This is perfect.
Let's document the schedule schema fields:
- `module_id`: Foreign key referencing `modules.id`, marked `UNIQUE` to ensure 1-to-1 relationship.
- `interval_hours`: Frequency of check in hours, default is 24, must be positive.
- `last_run`: Timestamp of the last run.
- `next_run`: Timestamp of the next scheduled run.
- `created_at` and `updated_at`: Standard creation and update audit columns.
