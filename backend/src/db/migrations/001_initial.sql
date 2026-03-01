-- Binocular initial schema migration.

CREATE TABLE IF NOT EXISTS extension_module (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    filename              TEXT    NOT NULL UNIQUE,
    module_version        TEXT,
    supported_device_type TEXT,
    is_active             INTEGER NOT NULL DEFAULT 0,
    file_hash             TEXT,
    last_error            TEXT,
    loaded_at             TEXT,
    created_at            TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at            TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS device_type (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    name                    TEXT    NOT NULL UNIQUE,
    firmware_source_url     TEXT    NOT NULL,
    extension_module_id     INTEGER,
    check_frequency_minutes INTEGER NOT NULL DEFAULT 360,
    created_at              TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at              TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (extension_module_id) REFERENCES extension_module (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS device (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    device_type_id      INTEGER NOT NULL,
    name                TEXT    NOT NULL,
    current_version     TEXT    NOT NULL,
    latest_seen_version TEXT,
    last_checked_at     TEXT,
    notes               TEXT,
    created_at          TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at          TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (device_type_id, name),
    FOREIGN KEY (device_type_id) REFERENCES device_type (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS check_history (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id         INTEGER NOT NULL,
    checked_at        TEXT    NOT NULL,
    version_found     TEXT,
    outcome           TEXT    NOT NULL CHECK (outcome IN ('success', 'error')),
    error_description TEXT,
    created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    FOREIGN KEY (device_id) REFERENCES device (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS app_config (
    id                              INTEGER PRIMARY KEY CHECK (id = 1),
    default_check_frequency_minutes INTEGER NOT NULL DEFAULT 360,
    smtp_host                       TEXT,
    smtp_port                       INTEGER,
    smtp_username                   TEXT,
    smtp_password                   TEXT,
    smtp_from_address               TEXT,
    gotify_url                      TEXT,
    gotify_token                    TEXT,
    notifications_enabled           INTEGER NOT NULL DEFAULT 0,
    check_history_retention_days    INTEGER NOT NULL DEFAULT 90,
    created_at                      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at                      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

INSERT OR IGNORE INTO app_config (id) VALUES (1);

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

INSERT INTO schema_version (version)
SELECT 0
WHERE NOT EXISTS (SELECT 1 FROM schema_version);
