-- Migration 0007: Module health tracking fields
ALTER TABLE modules ADD COLUMN consecutive_failures INTEGER NOT NULL DEFAULT 0;
ALTER TABLE modules ADD COLUMN last_success TEXT NULL;
