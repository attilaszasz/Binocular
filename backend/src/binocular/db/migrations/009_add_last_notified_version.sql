-- Migration: Add last_notified_version to devices for notification deduplication
-- Number: 009
-- Requires: PRAGMA foreign_keys = ON

ALTER TABLE devices
    ADD COLUMN last_notified_version TEXT DEFAULT NULL;
