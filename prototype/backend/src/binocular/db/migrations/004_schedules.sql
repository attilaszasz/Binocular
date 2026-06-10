CREATE TABLE device_type_schedules (
    device_type_id INTEGER PRIMARY KEY REFERENCES device_types(id),
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
