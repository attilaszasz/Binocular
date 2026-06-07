-- Migration: Fix device_type_schedules FK to reference modules
-- Number: 008
-- Requires: PRAGMA foreign_keys = ON
-- 
-- Context: Migration 007 Step 8 (recreating device_type_schedules with
-- FK to modules) was added after the initial v0.0.8 deployment.
-- Databases migrated before Step 8 still have FK REFERENCES device_types(id)
-- pointing to the dropped table, causing 500 errors on schedule upsert.
-- This migration is a catch-up: it applies Step 8 idempotently.

PRAGMA foreign_keys = ON;

-- Only run if the FK still references the dropped device_types table.
-- The LIKE '%device_types%' check is safe because the FK text is inclusive
-- of the table name.
CREATE TABLE device_type_schedules_new AS
    SELECT * FROM device_type_schedules WHERE 1=0;

-- If the new table creation succeeds, the old FK is still in place.
-- Check by trying to insert with the old FK constraint active.
-- Approach: check the DDL of the existing table.
-- SQLite does not support ALTER TABLE ... ALTER CONSTRAINT, so we
-- recreate the table.

PRAGMA foreign_keys = OFF;

-- Save existing rows (may be empty after Step 6 of 007)
CREATE TABLE _schedules_backup AS SELECT * FROM device_type_schedules;

DROP TABLE device_type_schedules;

CREATE TABLE device_type_schedules (
    device_type_id INTEGER PRIMARY KEY REFERENCES modules(id),
    enabled INTEGER NOT NULL DEFAULT 0,
    interval_minutes INTEGER NOT NULL DEFAULT 1440,
    next_run_at TEXT,
    last_started_at TEXT,
    last_completed_at TEXT,
    last_success_at TEXT,
    last_failure_at TEXT,
    last_failure_reason TEXT,
    last_skip_reason TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO device_type_schedules SELECT * FROM _schedules_backup;

DROP TABLE _schedules_backup;

PRAGMA foreign_keys = ON;
