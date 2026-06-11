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

-- Seed schedules for existing modules if they do not exist
INSERT OR IGNORE INTO schedules (module_id, interval_hours, next_run)
SELECT id, 24, datetime('now') FROM modules;

-- Trigger to auto-initialize schedule for newly created modules.
CREATE TRIGGER IF NOT EXISTS init_module_schedule
AFTER INSERT ON modules
BEGIN
    INSERT INTO schedules (module_id, interval_hours, next_run)
    VALUES (NEW.id, 24, datetime('now'));
END;
