-- Migration 0002: Device inventory tables
-- Creates the modules seed table and devices table.

CREATE TABLE IF NOT EXISTS modules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    device_type TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS devices (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    name                    TEXT    NOT NULL,
    model                   TEXT    NOT NULL DEFAULT '',
    module_id               INTEGER NOT NULL REFERENCES modules(id) ON DELETE RESTRICT,
    current_version         TEXT    NOT NULL DEFAULT '',
    has_update              INTEGER NOT NULL DEFAULT 0 CHECK(has_update IN (0, 1)),
    latest_detected_version TEXT,
    last_checked            TEXT,
    last_notified_version   TEXT,
    created_at              TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at              TEXT    NOT NULL DEFAULT (datetime('now'))
);
