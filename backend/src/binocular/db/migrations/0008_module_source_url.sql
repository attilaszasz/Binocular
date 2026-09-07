-- Migration 0008: Optional canonical source metadata for extension modules
ALTER TABLE modules ADD COLUMN source_url TEXT NULL;
