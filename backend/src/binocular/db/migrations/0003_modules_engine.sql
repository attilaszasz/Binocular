-- Migration 0003: Module engine columns
-- Extends the modules table with engine-required metadata.

ALTER TABLE modules ADD COLUMN version TEXT NOT NULL DEFAULT '';
ALTER TABLE modules ADD COLUMN author TEXT NOT NULL DEFAULT '';
ALTER TABLE modules ADD COLUMN file_path TEXT NOT NULL DEFAULT '';
ALTER TABLE modules ADD COLUMN is_official INTEGER NOT NULL DEFAULT 0 CHECK(is_official IN (0, 1));
ALTER TABLE modules ADD COLUMN status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'error'));
