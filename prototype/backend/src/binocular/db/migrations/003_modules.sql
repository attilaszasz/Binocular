CREATE TABLE modules (
    id INTEGER PRIMARY KEY,
    module_id TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    source_path TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    author TEXT,
    version TEXT,
    status TEXT NOT NULL DEFAULT 'installed'
        CHECK (status IN ('installed', 'disabled')),
    validation_status TEXT NOT NULL DEFAULT 'unvalidated'
        CHECK (validation_status IN ('unvalidated', 'valid', 'invalid')),
    validation_summary_json TEXT NOT NULL DEFAULT '{}',
    last_validated_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_modules_status_name
ON modules (status, display_name COLLATE NOCASE);