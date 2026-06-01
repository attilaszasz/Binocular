-- Migration: Create activity_log table and pruning trigger
-- Number: 006

CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL CHECK(event_type IN ('check', 'notification')),
    status TEXT NOT NULL CHECK(status IN ('success', 'failed')),
    device_name TEXT,
    module_name TEXT,
    message TEXT NOT NULL,
    traceback TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Index for reverse chronological listing
CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON activity_log(created_at DESC, id DESC);

-- rolling log pruning trigger capping rows at 1000
CREATE TRIGGER IF NOT EXISTS prune_activity_log
AFTER INSERT ON activity_log
BEGIN
    DELETE FROM activity_log
    WHERE id IN (
        SELECT id FROM activity_log
        ORDER BY created_at DESC, id DESC
        LIMIT -1 OFFSET 1000
    );
END;
