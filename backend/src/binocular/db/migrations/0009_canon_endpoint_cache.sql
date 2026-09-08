CREATE TABLE IF NOT EXISTS canon_firmware_endpoint_mappings (
    catalogue_family TEXT NOT NULL,
    model_key TEXT NOT NULL,
    endpoint_url TEXT NOT NULL,
    discovered_at INTEGER NOT NULL,
    last_validated_at INTEGER,
    invalidated_at INTEGER,
    invalidation_reason TEXT,
    PRIMARY KEY (catalogue_family, model_key),
    CHECK ((invalidated_at IS NULL AND invalidation_reason IS NULL)
        OR (invalidated_at IS NOT NULL AND invalidation_reason IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS idx_canon_endpoint_mapping_freshness
    ON canon_firmware_endpoint_mappings (catalogue_family, model_key, discovered_at);

CREATE TABLE IF NOT EXISTS canon_refresh_leases (
    catalogue_family TEXT NOT NULL,
    model_key TEXT NOT NULL,
    owner_token TEXT NOT NULL,
    fencing_token INTEGER NOT NULL,
    expires_at INTEGER NOT NULL,
    heartbeat_at INTEGER NOT NULL,
    waiter_count INTEGER NOT NULL CHECK (waiter_count >= 0),
    state TEXT NOT NULL CHECK (state IN ('open', 'closing')),
    PRIMARY KEY (catalogue_family, model_key)
);
