CREATE TABLE device_types (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE devices (
    id INTEGER PRIMARY KEY,
    device_type_id INTEGER NOT NULL REFERENCES device_types(id),
    name TEXT NOT NULL,
    model TEXT NOT NULL,
    current_version TEXT NOT NULL,
    latest_version TEXT,
    last_checked_at TEXT,
    last_success_at TEXT,
    last_check_status TEXT NOT NULL DEFAULT 'never_checked'
        CHECK (last_check_status IN ('never_checked', 'check_failed', 'update_available', 'up_to_date')),
    is_archived INTEGER NOT NULL DEFAULT 0 CHECK (is_archived IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_devices_active_type_name
ON devices (is_archived, device_type_id, name COLLATE NOCASE);