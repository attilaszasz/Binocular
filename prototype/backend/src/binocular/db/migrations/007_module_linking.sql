-- Migration: Link devices to modules, drop device_types entity
-- Number: 007
-- Requires: PRAGMA foreign_keys = ON

PRAGMA foreign_keys = ON;

-- ──────────────────────────────────────────────
-- Step 1: Add module_id FK column to devices
-- ──────────────────────────────────────────────
-- NULLABLE at schema level (application enforces NOT NULL on create/update).
ALTER TABLE devices
    ADD COLUMN module_id INTEGER REFERENCES modules(id) DEFAULT NULL;

-- ──────────────────────────────────────────────
-- Step 2: Best-effort backfill
-- ──────────────────────────────────────────────
-- Match existing device_types.name to modules.display_name
-- case-insensitively. Unmatchable devices remain NULL
-- (will appear as "unlinked" in the UI).
UPDATE devices
SET module_id = (
    SELECT m.id
    FROM modules m
    JOIN device_types dt ON dt.id = devices.device_type_id
    WHERE lower(m.display_name) = lower(dt.name)
    LIMIT 1
);

-- ──────────────────────────────────────────────
-- Step 3: Drop the old composite index
-- ──────────────────────────────────────────────
-- Must drop before the column because SQLite rejects
-- DROP COLUMN while an index references the column.
DROP INDEX IF EXISTS idx_devices_active_type_name;

-- ──────────────────────────────────────────────
-- Step 4: Drop the old device_type_id column
-- ──────────────────────────────────────────────
-- SQLite 3.35.0+ supports ALTER TABLE ... DROP COLUMN.
-- The backup snapshot created before migration provides
-- rollback if needed.
ALTER TABLE devices DROP COLUMN device_type_id;

-- ──────────────────────────────────────────────
-- Step 5: Create new index for the new FK
-- ──────────────────────────────────────────────
-- Supports common queries: list active devices by module,
-- ordered by module display name then device name.
CREATE INDEX idx_devices_active_module_name
    ON devices (is_archived, module_id, name COLLATE NOCASE);

-- ──────────────────────────────────────────────
-- Step 6: Clear device_type_schedules
-- ──────────────────────────────────────────────
-- Operator reconfigures per-module schedules post-migration.
-- The table structure is retained for future per-module
-- scheduling (out of scope for E022).
DELETE FROM device_type_schedules;

-- ──────────────────────────────────────────────
-- Step 7: Drop the device_types table
-- ──────────────────────────────────────────────
-- No remaining FKs point to it (devices column dropped,
-- schedule rows deleted). The table is no longer needed.
DROP TABLE IF EXISTS device_types;

-- ──────────────────────────────────────────────
-- Step 8: Fix device_type_schedules FK to reference modules
-- ──────────────────────────────────────────────
-- The device_type_schedules FK REFERENCES device_types(id) is now
-- orphaned. Recreate the table with FK pointing to modules(id).
-- All rows were deleted in Step 6, so no data is lost.
PRAGMA foreign_keys = OFF;
CREATE TABLE device_type_schedules_new (
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
INSERT INTO device_type_schedules_new SELECT * FROM device_type_schedules;
DROP TABLE device_type_schedules;
ALTER TABLE device_type_schedules_new RENAME TO device_type_schedules;
PRAGMA foreign_keys = ON;
