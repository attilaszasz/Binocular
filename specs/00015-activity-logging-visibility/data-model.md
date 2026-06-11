# Data Model: Activity Logging & Visibility

This document describes the schema and database migrations for the activity log feature.

## Database Migrations

### Migration `0006_activity_log.sql`

```sql
-- Migration: E015 Activity Logging
-- Creates the activity_log table for bounded system logging.

CREATE TABLE activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    level TEXT NOT NULL,
    category TEXT NOT NULL,
    message TEXT NOT NULL,
    device_id INTEGER NULL,
    module_name TEXT NULL,
    traceback TEXT NULL,
    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

-- Indices for performance on sorting and filtering
CREATE INDEX idx_activity_log_timestamp ON activity_log(timestamp DESC);
CREATE INDEX idx_activity_log_level ON activity_log(level);
CREATE INDEX idx_activity_log_category ON activity_log(category);
CREATE INDEX idx_activity_log_device_id ON activity_log(device_id);
```

## Schema Entities

### Entity: `ActivityLogEntry`
Maps directly to the `activity_log` table rows.

| Field | Type | SQLite Type | Description |
|-------|------|-------------|-------------|
| `id` | int | INTEGER | Primary Key, Auto-increment |
| `timestamp` | str / datetime | DATETIME | ISO 8601 timestamp, defaults to current time |
| `level` | str | TEXT | Log severity: `INFO`, `WARNING`, `ERROR` |
| `category` | str | TEXT | Log category: `check`, `notification`, `system` |
| `message` | str | TEXT | Human-readable log message |
| `device_id` | int | INTEGER | Foreign Key to `devices(id)` |
| `module_name` | str | TEXT | Name of the module performing the action (optional) |
| `traceback` | str | TEXT | Traceback details if an error occurred (optional) |
