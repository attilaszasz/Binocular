-- Dormant catalog persistence. No catalog data or work is inferred from V1 rows.
-- Canonical UUID/variant/version values and source authority are validated by
-- typed repositories; these guards enforce structural integrity, not a sandbox.
ALTER TABLE modules ADD COLUMN config_generation INTEGER NOT NULL DEFAULT 1
    CHECK(config_generation > 0);
ALTER TABLE notification_channels ADD COLUMN config_revision INTEGER NOT NULL DEFAULT 1
    CHECK(config_revision > 0);

CREATE TABLE catalog_models (
    id TEXT NOT NULL PRIMARY KEY,
    module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE RESTRICT,
    source_model_key TEXT NOT NULL CHECK(length(trim(source_model_key)) > 0),
    variant_key TEXT NOT NULL CHECK(json_valid(variant_key) AND length(variant_key) <= 2048),
    display_name TEXT NOT NULL CHECK(length(trim(display_name)) > 0 AND length(display_name) <= 240),
    source_url TEXT CHECK(length(source_url) <= 2048),
    presence TEXT NOT NULL DEFAULT 'active' CHECK(presence IN ('active', 'missing')),
    last_seen_at INTEGER NOT NULL CHECK(last_seen_at >= 0),
    last_seen_generation INTEGER NOT NULL CHECK(last_seen_generation > 0),
    observation_generation INTEGER NOT NULL DEFAULT 0 CHECK(observation_generation >= 0),
    identity_verified_at INTEGER CHECK(identity_verified_at >= 0),
    identity_evidence_url TEXT CHECK(length(trim(identity_evidence_url)) > 0 AND length(identity_evidence_url) <= 2048),
    identity_evidence_kind TEXT CHECK(identity_evidence_kind IN ('authoritative_listing', 'authoritative_detail')),
    identity_evidence_digest TEXT CHECK(length(identity_evidence_digest) = 64 AND identity_evidence_digest NOT GLOB '*[^0-9a-f]*'),
    CHECK((identity_verified_at IS NULL AND identity_evidence_url IS NULL
        AND identity_evidence_kind IS NULL AND identity_evidence_digest IS NULL)
        OR (identity_verified_at IS NOT NULL AND identity_evidence_url IS NOT NULL
        AND identity_evidence_kind IS NOT NULL AND identity_evidence_digest IS NOT NULL)),
    UNIQUE(module_id, source_model_key, variant_key),
    UNIQUE(id, module_id)
);
CREATE INDEX idx_catalog_models_page ON catalog_models(module_id, presence, display_name, id);

CREATE TABLE catalog_model_aliases (
    model_id TEXT NOT NULL REFERENCES catalog_models(id) ON DELETE CASCADE,
    alias TEXT NOT NULL CHECK(length(trim(alias)) > 0 AND length(alias) <= 240),
    search_key TEXT NOT NULL CHECK(length(trim(search_key)) > 0 AND length(search_key) <= 480),
    PRIMARY KEY(model_id, alias)
);
CREATE INDEX idx_catalog_alias_search ON catalog_model_aliases(search_key, model_id);
CREATE TABLE catalog_model_source_ids (
    model_id TEXT NOT NULL REFERENCES catalog_models(id) ON DELETE CASCADE,
    namespace TEXT NOT NULL CHECK(length(trim(namespace)) > 0 AND length(namespace) <= 120),
    value TEXT NOT NULL CHECK(length(trim(value)) > 0 AND length(value) <= 512),
    source_url TEXT CHECK(length(source_url) <= 2048),
    PRIMARY KEY(model_id, namespace, value)
);
CREATE INDEX idx_catalog_source_lookup ON catalog_model_source_ids(namespace, value, model_id);

ALTER TABLE devices ADD COLUMN catalog_model_id TEXT DEFAULT NULL
    REFERENCES catalog_models(id) ON DELETE RESTRICT;
ALTER TABLE devices ADD COLUMN catalog_link_state TEXT NOT NULL DEFAULT 'legacy'
    CHECK(catalog_link_state IN ('legacy', 'unresolved', 'linked'));
ALTER TABLE devices ADD COLUMN installed_unknown INTEGER NOT NULL DEFAULT 1
    CHECK(installed_unknown IN (0, 1));
ALTER TABLE devices ADD COLUMN revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0);
ALTER TABLE devices ADD COLUMN comparison_status TEXT NOT NULL DEFAULT 'unverified'
    CHECK(comparison_status IN ('unverified', 'unknown', 'comparison_unknown', 'current',
        'update_available', 'no_firmware', 'stale', 'failed'));
CREATE INDEX idx_device_catalog_model ON devices(catalog_model_id, id);
-- Exactly Python str.strip whitespace, without changing any installed string.
UPDATE devices SET installed_unknown = CASE WHEN length(trim(current_version,
    char(9,10,11,12,13,28,29,30,31,32,133,160,5760,8192,8193,8194,8195,8196,8197,
        8198,8199,8200,8201,8202,8232,8233,8239,8287,12288))) = 0 THEN 1 ELSE 0 END;
UPDATE devices SET comparison_status = 'unknown', has_update = 0 WHERE installed_unknown = 1;

CREATE TABLE catalog_refresh_runs (
    id TEXT NOT NULL PRIMARY KEY,
    module_id INTEGER NOT NULL REFERENCES modules(id) ON DELETE RESTRICT,
    generation INTEGER NOT NULL CHECK(generation > 0),
    config_generation INTEGER NOT NULL CHECK(config_generation > 0),
    scope_key TEXT NOT NULL CHECK(length(trim(scope_key)) > 0 AND length(scope_key) <= 128),
    model_id TEXT REFERENCES catalog_models(id) ON DELETE RESTRICT,
    state TEXT NOT NULL CHECK(state IN ('queued', 'running', 'complete', 'partial', 'failed', 'cancelled', 'obsolete')),
    created_at INTEGER NOT NULL CHECK(created_at >= 0),
    deadline_at INTEGER NOT NULL CHECK(deadline_at > created_at),
    max_requests INTEGER NOT NULL CHECK(max_requests > 0),
    requests_used INTEGER NOT NULL DEFAULT 0 CHECK(requests_used >= 0 AND requests_used <= max_requests),
    max_models INTEGER NOT NULL CHECK(max_models > 0),
    models_used INTEGER NOT NULL DEFAULT 0 CHECK(models_used >= 0 AND models_used <= max_models),
    cursor TEXT CHECK(length(cursor) <= 8192),
    enumeration_complete INTEGER NOT NULL DEFAULT 0 CHECK(enumeration_complete IN (0, 1)),
    authoritative INTEGER NOT NULL DEFAULT 0 CHECK(authoritative IN (0, 1)),
    last_progress_at INTEGER CHECK(last_progress_at >= 0),
    finished_at INTEGER CHECK(finished_at >= created_at),
    error_code TEXT CHECK(length(error_code) <= 120),
    error_detail TEXT CHECK(length(error_detail) <= 2000),
    claim_token TEXT,
    claim_generation INTEGER NOT NULL DEFAULT 0 CHECK(claim_generation >= 0),
    owner_instance TEXT,
    lease_until INTEGER CHECK(lease_until >= 0 AND lease_until <= deadline_at),
    enumeration_outcome TEXT NOT NULL DEFAULT 'not_requested'
        CHECK(enumeration_outcome IN ('not_requested', 'running', 'complete', 'partial', 'failed', 'cancelled')),
    enumeration_started_at INTEGER CHECK(enumeration_started_at >= 0),
    enumeration_finished_at INTEGER CHECK(enumeration_finished_at >= enumeration_started_at),
    enumeration_error_code TEXT CHECK(length(enumeration_error_code) <= 120),
    enumeration_error_detail TEXT CHECK(length(enumeration_error_detail) <= 2000),
    CHECK((scope_key = 'module') = (model_id IS NULL)),
    CHECK((state IN ('queued', 'running')) = (finished_at IS NULL)),
    CHECK(state != 'complete' OR model_id IS NOT NULL OR enumeration_complete = 1),
    CHECK((claim_token IS NULL AND owner_instance IS NULL AND lease_until IS NULL)
        OR (claim_token IS NOT NULL AND owner_instance IS NOT NULL AND lease_until IS NOT NULL AND claim_generation > 0)),
    CHECK((enumeration_complete = 1) = (enumeration_outcome = 'complete')),
    CHECK((enumeration_outcome = 'not_requested' AND enumeration_started_at IS NULL AND enumeration_finished_at IS NULL)
        OR (enumeration_outcome = 'running' AND enumeration_started_at IS NOT NULL AND enumeration_finished_at IS NULL)
        OR (enumeration_outcome IN ('complete', 'partial', 'failed', 'cancelled')
            AND enumeration_started_at IS NOT NULL AND enumeration_finished_at IS NOT NULL)),
    UNIQUE(module_id, generation)
);
CREATE UNIQUE INDEX idx_catalog_run_active_scope ON catalog_refresh_runs(module_id, scope_key)
    WHERE state IN ('queued', 'running');
CREATE INDEX idx_catalog_run_deadline ON catalog_refresh_runs(state, deadline_at);

CREATE TABLE catalog_module_state (
    module_id INTEGER NOT NULL PRIMARY KEY REFERENCES modules(id) ON DELETE CASCADE,
    next_run_generation INTEGER NOT NULL DEFAULT 1 CHECK(next_run_generation > 0),
    enumeration_last_attempt_id TEXT REFERENCES catalog_refresh_runs(id) ON DELETE RESTRICT,
    enumeration_last_success_at INTEGER CHECK(enumeration_last_success_at >= 0),
    enumeration_last_success_generation INTEGER CHECK(enumeration_last_success_generation > 0),
    CHECK((enumeration_last_success_at IS NULL) = (enumeration_last_success_generation IS NULL))
);

CREATE TABLE catalog_verification_attempts (
    id TEXT NOT NULL PRIMARY KEY,
    model_id TEXT NOT NULL REFERENCES catalog_models(id) ON DELETE RESTRICT,
    run_id TEXT REFERENCES catalog_refresh_runs(id) ON DELETE RESTRICT,
    config_generation INTEGER NOT NULL CHECK(config_generation > 0),
    started_at INTEGER NOT NULL CHECK(started_at >= 0),
    finished_at INTEGER CHECK(finished_at >= started_at),
    outcome TEXT NOT NULL CHECK(outcome IN ('running', 'firmware', 'no_firmware', 'unsupported', 'failed', 'cancelled')),
    error_code TEXT CHECK(length(error_code) <= 120),
    error_detail TEXT CHECK(length(error_detail) <= 2000),
    CHECK((outcome = 'running') = (finished_at IS NULL)),
    CHECK(outcome NOT IN ('failed', 'unsupported') OR error_code IS NOT NULL),
    UNIQUE(id, model_id)
);
CREATE INDEX idx_catalog_attempt_latest ON catalog_verification_attempts(model_id, started_at DESC, id);

CREATE TABLE firmware_observations (
    id TEXT NOT NULL PRIMARY KEY,
    model_id TEXT NOT NULL REFERENCES catalog_models(id) ON DELETE RESTRICT,
    generation INTEGER NOT NULL CHECK(generation > 0),
    attempt_id TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL CHECK(kind IN ('firmware', 'no_firmware')),
    version_display TEXT CHECK(length(version_display) <= 240),
    version_key TEXT CHECK(length(version_key) <= 512),
    verified_at INTEGER NOT NULL CHECK(verified_at >= 0),
    provenance_url TEXT NOT NULL CHECK(length(trim(provenance_url)) > 0 AND length(provenance_url) <= 2048),
    provenance_digest TEXT NOT NULL CHECK(length(provenance_digest) = 64 AND provenance_digest NOT GLOB '*[^0-9a-f]*'),
    release_url TEXT CHECK(length(release_url) <= 2048),
    release_notes TEXT CHECK(length(release_notes) <= 10000),
    CHECK((kind = 'firmware' AND version_display IS NOT NULL AND length(trim(version_display)) > 0
        AND version_key IS NOT NULL AND length(trim(version_key)) > 0)
        OR (kind = 'no_firmware' AND version_display IS NULL AND version_key IS NULL)),
    FOREIGN KEY(attempt_id, model_id) REFERENCES catalog_verification_attempts(id, model_id) ON DELETE RESTRICT,
    UNIQUE(model_id, generation),
    UNIQUE(id, model_id, generation)
);

CREATE TABLE catalog_refresh_items (
    run_id TEXT NOT NULL REFERENCES catalog_refresh_runs(id) ON DELETE RESTRICT,
    model_id TEXT NOT NULL REFERENCES catalog_models(id) ON DELETE RESTRICT,
    state TEXT NOT NULL CHECK(state IN ('queued', 'running', 'verified', 'no_firmware', 'failed', 'cancelled', 'obsolete')),
    deadline_at INTEGER NOT NULL CHECK(deadline_at >= 0),
    max_requests INTEGER NOT NULL CHECK(max_requests > 0),
    requests_used INTEGER NOT NULL DEFAULT 0 CHECK(requests_used >= 0 AND requests_used <= max_requests),
    attempt_id TEXT REFERENCES catalog_verification_attempts(id) ON DELETE RESTRICT,
    error_code TEXT CHECK(length(error_code) <= 120),
    PRIMARY KEY(run_id, model_id)
);
CREATE INDEX idx_catalog_item_state ON catalog_refresh_items(run_id, state, model_id);

CREATE TABLE catalog_reevaluation_work (
    id TEXT NOT NULL PRIMARY KEY,
    kind TEXT NOT NULL CHECK(kind IN ('model', 'device')),
    model_id TEXT,
    observation_generation INTEGER CHECK(observation_generation > 0),
    device_id INTEGER REFERENCES devices(id) ON DELETE CASCADE,
    device_revision INTEGER CHECK(device_revision > 0),
    state TEXT NOT NULL CHECK(state IN ('pending', 'running', 'complete', 'failed', 'obsolete')),
    cursor_device_id INTEGER NOT NULL DEFAULT 0 CHECK(cursor_device_id >= 0),
    chunk_limit INTEGER NOT NULL CHECK(chunk_limit > 0 AND chunk_limit <= 100),
    max_chunks INTEGER NOT NULL CHECK(max_chunks > 0),
    chunks_used INTEGER NOT NULL DEFAULT 0 CHECK(chunks_used >= 0 AND chunks_used <= max_chunks),
    created_at INTEGER NOT NULL CHECK(created_at >= 0),
    deadline_at INTEGER NOT NULL CHECK(deadline_at > created_at),
    finished_at INTEGER CHECK(finished_at >= created_at),
    error_code TEXT CHECK(length(error_code) <= 120),
    claim_token TEXT,
    claim_generation INTEGER NOT NULL DEFAULT 0 CHECK(claim_generation >= 0),
    owner_instance TEXT,
    lease_until INTEGER CHECK(lease_until >= 0 AND lease_until <= deadline_at),
    CHECK((kind = 'model' AND model_id IS NOT NULL AND observation_generation IS NOT NULL
        AND device_id IS NULL AND device_revision IS NULL)
        OR (kind = 'device' AND device_id IS NOT NULL AND device_revision IS NOT NULL
        AND model_id IS NULL AND observation_generation IS NULL)),
    CHECK((state IN ('pending', 'running')) = (finished_at IS NULL)),
    CHECK((claim_token IS NULL AND owner_instance IS NULL AND lease_until IS NULL)
        OR (claim_token IS NOT NULL AND owner_instance IS NOT NULL AND lease_until IS NOT NULL AND claim_generation > 0)),
    FOREIGN KEY(model_id, observation_generation) REFERENCES firmware_observations(model_id, generation) ON DELETE RESTRICT
);
CREATE UNIQUE INDEX idx_catalog_reevaluation_model ON catalog_reevaluation_work(model_id, observation_generation) WHERE kind = 'model';
CREATE UNIQUE INDEX idx_catalog_reevaluation_device ON catalog_reevaluation_work(device_id, device_revision) WHERE kind = 'device';
CREATE INDEX idx_catalog_reevaluation_deadline ON catalog_reevaluation_work(state, deadline_at);

CREATE TABLE notification_intents (
    id TEXT NOT NULL PRIMARY KEY,
    device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE RESTRICT,
    target_display TEXT NOT NULL CHECK(length(trim(target_display)) > 0 AND length(target_display) <= 240),
    target_key TEXT NOT NULL CHECK(length(trim(target_key)) > 0 AND length(target_key) <= 512),
    channel_id INTEGER NOT NULL REFERENCES notification_channels(id) ON DELETE RESTRICT,
    observation_id TEXT NOT NULL REFERENCES firmware_observations(id) ON DELETE RESTRICT,
    expected_device_revision INTEGER NOT NULL CHECK(expected_device_revision > 0),
    state TEXT NOT NULL DEFAULT 'pending' CHECK(state IN ('pending', 'sending', 'delivered', 'failed', 'uncertain', 'superseded')),
    created_at INTEGER NOT NULL CHECK(created_at >= 0),
    updated_at INTEGER NOT NULL CHECK(updated_at >= created_at),
    next_attempt_at INTEGER CHECK(next_attempt_at >= 0),
    claim_token TEXT,
    claim_generation INTEGER NOT NULL DEFAULT 0 CHECK(claim_generation >= 0),
    owner_instance TEXT,
    lease_until INTEGER CHECK(lease_until >= 0),
    delivered_at INTEGER CHECK(delivered_at >= created_at),
    error_code TEXT CHECK(length(error_code) <= 120),
    CHECK((claim_token IS NULL AND owner_instance IS NULL AND lease_until IS NULL)
        OR (claim_token IS NOT NULL AND owner_instance IS NOT NULL AND lease_until IS NOT NULL AND claim_generation > 0)),
    CHECK(state != 'sending' OR claim_token IS NOT NULL),
    CHECK((state = 'delivered') = (delivered_at IS NOT NULL)),
    UNIQUE(device_id, target_key, channel_id),
    UNIQUE(id, claim_generation)
);
CREATE INDEX idx_notification_intent_due ON notification_intents(state, next_attempt_at, id);

CREATE TABLE notification_attempts (
    id TEXT NOT NULL PRIMARY KEY,
    intent_id TEXT NOT NULL REFERENCES notification_intents(id) ON DELETE RESTRICT,
    claim_generation INTEGER NOT NULL CHECK(claim_generation > 0),
    claim_token TEXT NOT NULL UNIQUE,
    owner_instance TEXT NOT NULL,
    expected_device_revision INTEGER NOT NULL CHECK(expected_device_revision > 0),
    observation_id TEXT NOT NULL REFERENCES firmware_observations(id) ON DELETE RESTRICT,
    channel_config_revision INTEGER NOT NULL CHECK(channel_config_revision > 0),
    claimed_at INTEGER NOT NULL CHECK(claimed_at >= 0),
    lease_until INTEGER NOT NULL CHECK(lease_until > claimed_at),
    retry_kind TEXT NOT NULL CHECK(retry_kind IN ('initial', 'definite_failure', 'expired_unstarted', 'explicit_uncertain')),
    duplicate_risk_ack_at INTEGER CHECK(duplicate_risk_ack_at >= 0 AND duplicate_risk_ack_at <= claimed_at),
    CHECK((retry_kind = 'explicit_uncertain') = (duplicate_risk_ack_at IS NOT NULL)),
    UNIQUE(intent_id, claim_generation)
);
CREATE TABLE notification_attempt_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id TEXT NOT NULL REFERENCES notification_attempts(id) ON DELETE RESTRICT,
    kind TEXT NOT NULL CHECK(kind IN ('send_authorized', 'accepted', 'definite_failure', 'uncertain', 'owner_stopped', 'late_accepted', 'late_failure')),
    recorded_at INTEGER NOT NULL CHECK(recorded_at >= 0),
    detail TEXT CHECK(length(detail) <= 2000),
    receipt_id TEXT CHECK(length(receipt_id) <= 512)
);
CREATE UNIQUE INDEX idx_notification_authorization ON notification_attempt_events(attempt_id) WHERE kind = 'send_authorized';
CREATE INDEX idx_notification_attempt_events ON notification_attempt_events(attempt_id, id);
CREATE TABLE device_channel_watermarks (
    device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE RESTRICT,
    channel_id INTEGER NOT NULL REFERENCES notification_channels(id) ON DELETE RESTRICT,
    target_key TEXT NOT NULL CHECK(length(trim(target_key)) > 0 AND length(target_key) <= 512),
    target_display TEXT NOT NULL CHECK(length(trim(target_display)) > 0 AND length(target_display) <= 240),
    accepted_at INTEGER NOT NULL CHECK(accepted_at >= 0),
    attempt_id TEXT NOT NULL REFERENCES notification_attempts(id) ON DELETE RESTRICT,
    PRIMARY KEY(device_id, channel_id)
);

-- Install guards only after the legacy backfill. No trigger enqueues work.
CREATE TRIGGER catalog_module_config_generation BEFORE UPDATE OF config_generation ON modules
WHEN NEW.config_generation NOT IN (OLD.config_generation, OLD.config_generation + 1)
BEGIN SELECT RAISE(ABORT, 'invalid module config generation'); END;
CREATE TRIGGER notification_channel_config_revision BEFORE UPDATE ON notification_channels
WHEN NEW.id != OLD.id OR NEW.config_revision NOT IN (OLD.config_revision, OLD.config_revision + 1)
    OR ((NEW.config IS NOT OLD.config OR NEW.enabled IS NOT OLD.enabled OR NEW.type IS NOT OLD.type)
        AND NEW.config_revision != OLD.config_revision + 1)
BEGIN SELECT RAISE(ABORT, 'invalid channel config revision'); END;
CREATE TRIGGER catalog_model_identity_immutable BEFORE UPDATE ON catalog_models
WHEN NEW.id IS NOT OLD.id OR NEW.module_id IS NOT OLD.module_id
    OR NEW.source_model_key IS NOT OLD.source_model_key OR NEW.variant_key IS NOT OLD.variant_key
BEGIN SELECT RAISE(ABORT, 'catalog model identity is immutable'); END;
-- SQLite REPLACE can bypass DELETE triggers when recursive_triggers is off.
-- Preserve identity/evidence even for that SQL spelling, while allowing normal
-- metadata UPSERTs for an unchanged identity.
CREATE TRIGGER catalog_model_insert_identity BEFORE INSERT ON catalog_models
WHEN EXISTS(SELECT 1 FROM catalog_models old WHERE old.id = NEW.id
    AND (old.module_id != NEW.module_id OR old.source_model_key != NEW.source_model_key
        OR old.variant_key != NEW.variant_key
        OR (NEW.identity_verified_at IS NULL AND (
            EXISTS(SELECT 1 FROM devices WHERE catalog_model_id = old.id)
            OR EXISTS(SELECT 1 FROM firmware_observations WHERE model_id = old.id)))))
BEGIN SELECT RAISE(ABORT, 'catalog model identity or referenced evidence is immutable'); END;
CREATE TRIGGER catalog_model_linked_evidence BEFORE UPDATE ON catalog_models
WHEN NEW.identity_verified_at IS NULL AND OLD.identity_verified_at IS NOT NULL
    AND (EXISTS(SELECT 1 FROM devices WHERE catalog_model_id = OLD.id)
        OR EXISTS(SELECT 1 FROM firmware_observations WHERE model_id = OLD.id))
BEGIN SELECT RAISE(ABORT, 'referenced identity evidence is required'); END;
CREATE TRIGGER catalog_model_generation BEFORE UPDATE OF observation_generation ON catalog_models
WHEN NEW.observation_generation != OLD.observation_generation
    AND NEW.observation_generation != OLD.observation_generation + 1
BEGIN SELECT RAISE(ABORT, 'observation generation must advance by one'); END;
CREATE TRIGGER catalog_model_missing BEFORE UPDATE OF presence ON catalog_models
WHEN NEW.presence = 'missing' AND OLD.presence != 'missing' AND NOT EXISTS(
    SELECT 1 FROM catalog_refresh_runs r JOIN modules s ON s.id = r.module_id
    WHERE r.module_id = OLD.module_id AND r.model_id IS NULL AND r.authoritative = 1
        AND r.enumeration_outcome = 'complete' AND r.config_generation = s.config_generation
        AND r.generation > OLD.last_seen_generation)
BEGIN SELECT RAISE(ABORT, 'missing status requires authoritative complete enumeration'); END;

CREATE TRIGGER catalog_device_insert BEFORE INSERT ON devices
BEGIN
    SELECT RAISE(ABORT, 'invalid catalog device link')
    WHERE (NEW.catalog_model_id IS NOT NULL) != (NEW.catalog_link_state = 'linked')
        OR (NEW.catalog_model_id IS NOT NULL AND NOT EXISTS(
            SELECT 1 FROM catalog_models WHERE id = NEW.catalog_model_id
                AND module_id = NEW.module_id AND identity_verified_at IS NOT NULL));
    SELECT RAISE(ABORT, 'known installed version must be nonblank')
    WHERE NEW.installed_unknown = 0 AND length(trim(NEW.current_version,
        char(9,10,11,12,13,28,29,30,31,32,133,160,5760,8192,8193,8194,8195,8196,8197,
            8198,8199,8200,8201,8202,8232,8233,8239,8287,12288))) = 0;
END;
CREATE TRIGGER catalog_device_update BEFORE UPDATE ON devices
BEGIN
    SELECT RAISE(ABORT, 'invalid catalog device link')
    WHERE (NEW.catalog_model_id IS NOT NULL) != (NEW.catalog_link_state = 'linked')
        OR (NEW.catalog_model_id IS NOT NULL AND NOT EXISTS(
            SELECT 1 FROM catalog_models WHERE id = NEW.catalog_model_id
                AND module_id = NEW.module_id AND identity_verified_at IS NOT NULL));
    SELECT RAISE(ABORT, 'known installed version must be nonblank')
    WHERE NEW.installed_unknown = 0 AND length(trim(NEW.current_version,
        char(9,10,11,12,13,28,29,30,31,32,133,160,5760,8192,8193,8194,8195,8196,8197,
            8198,8199,8200,8201,8202,8232,8233,8239,8287,12288))) = 0;
    SELECT RAISE(ABORT, 'invalid device revision')
    WHERE NEW.revision NOT IN (OLD.revision, OLD.revision + 1)
        OR ((NEW.current_version IS NOT OLD.current_version OR NEW.installed_unknown IS NOT OLD.installed_unknown
            OR NEW.module_id IS NOT OLD.module_id OR NEW.model IS NOT OLD.model
            OR NEW.catalog_model_id IS NOT OLD.catalog_model_id OR NEW.catalog_link_state IS NOT OLD.catalog_link_state)
            AND NEW.revision != OLD.revision + 1);
END;

CREATE TRIGGER catalog_run_insert BEFORE INSERT ON catalog_refresh_runs
BEGIN
    SELECT RAISE(ABORT, 'invalid refresh scope') WHERE NEW.model_id IS NOT NULL
        AND (NEW.scope_key != 'model:' || NEW.model_id OR NEW.enumeration_outcome != 'not_requested'
            OR NOT EXISTS(SELECT 1 FROM catalog_models WHERE id = NEW.model_id AND module_id = NEW.module_id));
END;
CREATE TRIGGER catalog_run_update BEFORE UPDATE ON catalog_refresh_runs
BEGIN
    SELECT RAISE(ABORT, 'refresh identity and bounds are immutable')
    WHERE NEW.id IS NOT OLD.id OR NEW.module_id IS NOT OLD.module_id OR NEW.model_id IS NOT OLD.model_id
        OR NEW.scope_key IS NOT OLD.scope_key OR NEW.generation != OLD.generation
        OR NEW.config_generation != OLD.config_generation OR NEW.created_at != OLD.created_at
        OR NEW.deadline_at != OLD.deadline_at OR NEW.max_requests != OLD.max_requests OR NEW.max_models != OLD.max_models;
    SELECT RAISE(ABORT, 'invalid refresh progress')
    WHERE NEW.requests_used < OLD.requests_used OR NEW.models_used < OLD.models_used
        OR NEW.claim_generation < OLD.claim_generation
        OR NEW.claim_generation > OLD.claim_generation + 1
        OR (OLD.state NOT IN ('queued', 'running') AND NEW.state != OLD.state)
        OR (OLD.state = 'running' AND NEW.state = 'queued')
        OR (OLD.model_id IS NOT NULL AND NEW.enumeration_outcome != 'not_requested')
        OR (OLD.enumeration_outcome NOT IN ('not_requested', 'running')
            AND NEW.enumeration_outcome != OLD.enumeration_outcome)
        OR (OLD.enumeration_outcome = 'running' AND NEW.enumeration_outcome = 'not_requested');
    SELECT RAISE(ABORT, 'completed enumeration evidence is immutable')
    WHERE OLD.enumeration_outcome NOT IN ('not_requested', 'running')
        AND (NEW.enumeration_started_at IS NOT OLD.enumeration_started_at
            OR NEW.enumeration_finished_at IS NOT OLD.enumeration_finished_at
            OR NEW.authoritative != OLD.authoritative);
    SELECT RAISE(ABORT, 'new refresh token requires next claim generation')
    WHERE NEW.claim_token IS NOT NULL AND NEW.claim_token IS NOT OLD.claim_token
        AND NEW.claim_generation != OLD.claim_generation + 1;
END;
CREATE TRIGGER catalog_run_retain_success BEFORE DELETE ON catalog_refresh_runs
WHEN EXISTS(SELECT 1 FROM catalog_module_state WHERE module_id = OLD.module_id
    AND enumeration_last_success_generation = OLD.generation)
BEGIN SELECT RAISE(ABORT, 'successful enumeration must be retained'); END;
CREATE TRIGGER catalog_module_state_insert BEFORE INSERT ON catalog_module_state
WHEN NEW.enumeration_last_attempt_id IS NOT NULL AND NOT EXISTS(
    SELECT 1 FROM catalog_refresh_runs WHERE id = NEW.enumeration_last_attempt_id
        AND module_id = NEW.module_id AND model_id IS NULL)
BEGIN SELECT RAISE(ABORT, 'enumeration attempt must have module scope'); END;
CREATE TRIGGER catalog_module_success_insert BEFORE INSERT ON catalog_module_state
WHEN NEW.enumeration_last_success_generation IS NOT NULL AND NOT EXISTS(
    SELECT 1 FROM catalog_refresh_runs r JOIN modules s ON s.id = r.module_id
    WHERE r.module_id = NEW.module_id AND r.model_id IS NULL
        AND r.generation = NEW.enumeration_last_success_generation AND r.enumeration_outcome = 'complete'
        AND r.authoritative = 1 AND r.enumeration_finished_at = NEW.enumeration_last_success_at
        AND r.config_generation = s.config_generation)
BEGIN SELECT RAISE(ABORT, 'enumeration success requires authoritative complete scan'); END;
CREATE TRIGGER catalog_module_state_update BEFORE UPDATE ON catalog_module_state
BEGIN
    SELECT RAISE(ABORT, 'invalid catalog module state')
    WHERE NEW.module_id != OLD.module_id OR NEW.next_run_generation < OLD.next_run_generation
        OR (NEW.enumeration_last_attempt_id IS NOT NULL AND NOT EXISTS(
            SELECT 1 FROM catalog_refresh_runs WHERE id = NEW.enumeration_last_attempt_id
                AND module_id = NEW.module_id AND model_id IS NULL));
    SELECT RAISE(ABORT, 'enumeration success requires authoritative complete scan')
    WHERE (NEW.enumeration_last_success_generation IS NOT OLD.enumeration_last_success_generation
        OR NEW.enumeration_last_success_at IS NOT OLD.enumeration_last_success_at)
        AND (NEW.enumeration_last_success_generation IS NULL OR NOT EXISTS(
            SELECT 1 FROM catalog_refresh_runs r JOIN modules s ON s.id = r.module_id
            WHERE r.module_id = NEW.module_id AND r.model_id IS NULL
                AND r.generation = NEW.enumeration_last_success_generation AND r.enumeration_outcome = 'complete'
                AND r.authoritative = 1 AND r.enumeration_finished_at = NEW.enumeration_last_success_at
                AND r.config_generation = s.config_generation));
END;

CREATE TRIGGER catalog_verification_insert BEFORE INSERT ON catalog_verification_attempts
WHEN NEW.run_id IS NOT NULL AND NOT EXISTS(
    SELECT 1 FROM catalog_refresh_runs r JOIN catalog_models m ON m.id = NEW.model_id
    WHERE r.id = NEW.run_id AND r.module_id = m.module_id
        AND (r.model_id IS NULL OR r.model_id = NEW.model_id) AND r.config_generation = NEW.config_generation)
BEGIN SELECT RAISE(ABORT, 'verification attempt ownership mismatch'); END;
CREATE TRIGGER catalog_verification_update BEFORE UPDATE ON catalog_verification_attempts
BEGIN
    SELECT RAISE(ABORT, 'verification identity is immutable')
    WHERE NEW.id IS NOT OLD.id OR NEW.model_id IS NOT OLD.model_id OR NEW.run_id IS NOT OLD.run_id
        OR NEW.config_generation != OLD.config_generation OR NEW.started_at != OLD.started_at;
    SELECT RAISE(ABORT, 'terminal verification is immutable') WHERE OLD.outcome != 'running';
END;

-- Success sequence inside one unit: finish attempt, increment model generation,
-- insert observation, enqueue work. A trigger cannot require the future enqueue.
CREATE TRIGGER catalog_observation_insert BEFORE INSERT ON firmware_observations
WHEN NOT EXISTS(
    SELECT 1 FROM catalog_verification_attempts a
    JOIN catalog_models m ON m.id = a.model_id JOIN modules s ON s.id = m.module_id
    LEFT JOIN catalog_refresh_runs r ON r.id = a.run_id
    WHERE a.id = NEW.attempt_id AND a.model_id = NEW.model_id AND a.outcome = NEW.kind
        AND NEW.verified_at BETWEEN a.started_at AND a.finished_at
        AND m.identity_verified_at IS NOT NULL AND m.observation_generation = NEW.generation
        AND a.config_generation = s.config_generation
        AND (a.run_id IS NULL OR (r.state = 'running' AND r.config_generation = s.config_generation
            AND r.claim_token IS NOT NULL AND NEW.verified_at < r.lease_until AND NEW.verified_at < r.deadline_at)))
BEGIN SELECT RAISE(ABORT, 'observation requires current verified attempt and identity'); END;
CREATE TRIGGER catalog_observation_no_replace BEFORE INSERT ON firmware_observations
WHEN EXISTS(SELECT 1 FROM firmware_observations WHERE id = NEW.id OR attempt_id = NEW.attempt_id
    OR (model_id = NEW.model_id AND generation = NEW.generation))
BEGIN SELECT RAISE(ABORT, 'observations are immutable'); END;
CREATE TRIGGER catalog_observation_no_update BEFORE UPDATE ON firmware_observations
BEGIN SELECT RAISE(ABORT, 'observations are immutable'); END;
CREATE TRIGGER catalog_observation_no_delete BEFORE DELETE ON firmware_observations
BEGIN SELECT RAISE(ABORT, 'observations are immutable'); END;

CREATE TRIGGER catalog_item_insert BEFORE INSERT ON catalog_refresh_items
BEGIN
    SELECT RAISE(ABORT, 'refresh item ownership or bounds mismatch') WHERE NOT EXISTS(
        SELECT 1 FROM catalog_refresh_runs r JOIN catalog_models m ON m.id = NEW.model_id
        WHERE r.id = NEW.run_id AND r.module_id = m.module_id
            AND (r.model_id IS NULL OR r.model_id = NEW.model_id)
            AND NEW.deadline_at > r.created_at AND NEW.deadline_at <= r.deadline_at
            AND NEW.max_requests <= r.max_requests
            AND (SELECT count(*) FROM catalog_refresh_items WHERE run_id = r.id) < r.max_models);
    SELECT RAISE(ABORT, 'refresh item attempt mismatch') WHERE NEW.attempt_id IS NOT NULL AND NOT EXISTS(
        SELECT 1 FROM catalog_verification_attempts WHERE id = NEW.attempt_id
            AND model_id = NEW.model_id AND run_id = NEW.run_id);
END;
CREATE TRIGGER catalog_item_update BEFORE UPDATE ON catalog_refresh_items
BEGIN
    SELECT RAISE(ABORT, 'refresh item identity and bounds are immutable')
    WHERE NEW.run_id IS NOT OLD.run_id OR NEW.model_id IS NOT OLD.model_id
        OR NEW.deadline_at != OLD.deadline_at OR NEW.max_requests != OLD.max_requests;
    SELECT RAISE(ABORT, 'refresh item attempt mismatch') WHERE NEW.attempt_id IS NOT NULL AND NOT EXISTS(
        SELECT 1 FROM catalog_verification_attempts WHERE id = NEW.attempt_id
            AND model_id = NEW.model_id AND run_id = NEW.run_id);
    SELECT RAISE(ABORT, 'invalid refresh item progress') WHERE NEW.requests_used < OLD.requests_used
        OR (OLD.state NOT IN ('queued', 'running') AND NEW.state != OLD.state)
        OR (OLD.state = 'running' AND NEW.state = 'queued');
END;
CREATE TRIGGER catalog_item_no_delete BEFORE DELETE ON catalog_refresh_items
BEGIN SELECT RAISE(ABORT, 'admitted refresh items must be retained'); END;
CREATE TRIGGER catalog_reevaluation_update BEFORE UPDATE ON catalog_reevaluation_work
BEGIN
    SELECT RAISE(ABORT, 'reevaluation identity and bounds are immutable')
    WHERE NEW.id IS NOT OLD.id OR NEW.kind != OLD.kind OR NEW.model_id IS NOT OLD.model_id
        OR NEW.observation_generation IS NOT OLD.observation_generation OR NEW.device_id IS NOT OLD.device_id
        OR NEW.device_revision IS NOT OLD.device_revision OR NEW.chunk_limit != OLD.chunk_limit
        OR NEW.max_chunks != OLD.max_chunks OR NEW.created_at != OLD.created_at OR NEW.deadline_at != OLD.deadline_at;
    SELECT RAISE(ABORT, 'invalid reevaluation progress') WHERE NEW.chunks_used < OLD.chunks_used
        OR NEW.cursor_device_id < OLD.cursor_device_id OR NEW.claim_generation < OLD.claim_generation
        OR NEW.claim_generation > OLD.claim_generation + 1
        OR (OLD.state NOT IN ('pending', 'running') AND NEW.state != OLD.state)
        OR (OLD.state = 'running' AND NEW.state = 'pending');
    SELECT RAISE(ABORT, 'new reevaluation token requires next claim generation')
    WHERE NEW.claim_token IS NOT NULL AND NEW.claim_token IS NOT OLD.claim_token
        AND NEW.claim_generation != OLD.claim_generation + 1;
END;

CREATE TRIGGER notification_intent_insert BEFORE INSERT ON notification_intents
WHEN NOT EXISTS(SELECT 1 FROM devices d JOIN firmware_observations o ON o.model_id = d.catalog_model_id
    WHERE d.id = NEW.device_id AND o.id = NEW.observation_id AND d.catalog_link_state = 'linked'
        AND d.revision = NEW.expected_device_revision AND o.kind = 'firmware'
        AND o.version_key = NEW.target_key AND o.version_display = NEW.target_display)
BEGIN SELECT RAISE(ABORT, 'intent observation ownership or target mismatch'); END;
CREATE TRIGGER notification_intent_update BEFORE UPDATE ON notification_intents
BEGIN
    SELECT RAISE(ABORT, 'intent identity is immutable')
    WHERE NEW.id IS NOT OLD.id OR NEW.device_id != OLD.device_id OR NEW.channel_id != OLD.channel_id
        OR NEW.target_key IS NOT OLD.target_key OR NEW.target_display IS NOT OLD.target_display
        OR NEW.created_at != OLD.created_at;
    -- Historical captured revisions remain valid after an unrelated device edit.
    SELECT RAISE(ABORT, 'intent observation ownership or target mismatch')
    WHERE (NEW.observation_id IS NOT OLD.observation_id OR NEW.expected_device_revision != OLD.expected_device_revision)
        AND NOT EXISTS(SELECT 1 FROM devices d JOIN firmware_observations o ON o.model_id = d.catalog_model_id
            WHERE d.id = NEW.device_id AND o.id = NEW.observation_id AND d.catalog_link_state = 'linked'
                AND d.revision = NEW.expected_device_revision AND o.kind = 'firmware'
                AND o.version_key = NEW.target_key AND o.version_display = NEW.target_display);
    SELECT RAISE(ABORT, 'delivered intent is terminal') WHERE OLD.state = 'delivered';
    SELECT RAISE(ABORT, 'invalid intent generation')
    WHERE NEW.claim_generation < OLD.claim_generation OR NEW.claim_generation > OLD.claim_generation + 1;
    SELECT RAISE(ABORT, 'new intent token requires next claim generation')
    WHERE NEW.claim_token IS NOT NULL AND NEW.claim_token IS NOT OLD.claim_token
        AND NEW.claim_generation != OLD.claim_generation + 1;
END;
CREATE TRIGGER notification_watermark_no_delete BEFORE DELETE ON device_channel_watermarks
BEGIN SELECT RAISE(ABORT, 'accepted channel history must be retained'); END;

-- Claim sequence: CAS intent claim, insert immutable header; authorization CAS
-- precedes send_authorized. Completion appends evidence before projecting state
-- and watermark. Repositories enforce time/token/config and retry policy CASes.
CREATE TRIGGER notification_attempt_insert BEFORE INSERT ON notification_attempts
WHEN NOT EXISTS(SELECT 1 FROM notification_intents i JOIN notification_channels c ON c.id = i.channel_id
    WHERE i.id = NEW.intent_id AND i.claim_token = NEW.claim_token AND i.owner_instance = NEW.owner_instance
        AND i.claim_generation = NEW.claim_generation AND i.lease_until = NEW.lease_until
        AND i.expected_device_revision = NEW.expected_device_revision AND i.observation_id = NEW.observation_id
        AND c.config_revision = NEW.channel_config_revision AND i.state IN ('pending', 'failed'))
BEGIN SELECT RAISE(ABORT, 'attempt does not match intent claim'); END;
CREATE TRIGGER notification_attempt_no_replace BEFORE INSERT ON notification_attempts
WHEN EXISTS(SELECT 1 FROM notification_attempts WHERE id = NEW.id OR claim_token = NEW.claim_token
    OR (intent_id = NEW.intent_id AND claim_generation = NEW.claim_generation))
BEGIN SELECT RAISE(ABORT, 'notification attempts are immutable'); END;
CREATE TRIGGER notification_attempt_no_update BEFORE UPDATE ON notification_attempts
BEGIN SELECT RAISE(ABORT, 'notification attempts are immutable'); END;
CREATE TRIGGER notification_attempt_no_delete BEFORE DELETE ON notification_attempts
BEGIN SELECT RAISE(ABORT, 'notification attempts are immutable'); END;
CREATE TRIGGER notification_event_no_update BEFORE UPDATE ON notification_attempt_events
BEGIN SELECT RAISE(ABORT, 'notification evidence is immutable'); END;
CREATE TRIGGER notification_event_no_delete BEFORE DELETE ON notification_attempt_events
BEGIN SELECT RAISE(ABORT, 'notification evidence is immutable'); END;
CREATE TRIGGER notification_event_no_replace BEFORE INSERT ON notification_attempt_events
WHEN EXISTS(SELECT 1 FROM notification_attempt_events WHERE id = NEW.id
    OR (attempt_id = NEW.attempt_id AND kind = 'send_authorized' AND NEW.kind = 'send_authorized'))
BEGIN SELECT RAISE(ABORT, 'notification evidence is immutable'); END;

CREATE TRIGGER notification_watermark_insert BEFORE INSERT ON device_channel_watermarks
WHEN NOT EXISTS(SELECT 1 FROM notification_attempts a JOIN notification_intents i ON i.id = a.intent_id
    JOIN devices d ON d.id = i.device_id
    JOIN firmware_observations o ON o.id = a.observation_id
    JOIN notification_channels c ON c.id = i.channel_id
    JOIN catalog_models m ON m.id = o.model_id
    JOIN modules s ON s.id = m.module_id
    JOIN catalog_verification_attempts v ON v.id = o.attempt_id
    WHERE a.id = NEW.attempt_id AND i.device_id = NEW.device_id AND i.channel_id = NEW.channel_id
        AND i.target_key = NEW.target_key AND i.target_display = NEW.target_display AND i.state = 'delivered'
        AND i.delivered_at = NEW.accepted_at AND i.claim_token = a.claim_token AND i.claim_generation = a.claim_generation
        AND d.revision = a.expected_device_revision AND d.catalog_model_id = o.model_id
        AND i.owner_instance = a.owner_instance AND i.observation_id = a.observation_id
        AND i.expected_device_revision = a.expected_device_revision
        AND c.config_revision = a.channel_config_revision
        AND v.config_generation = s.config_generation AND m.observation_generation = o.generation
        AND NEW.accepted_at >= a.claimed_at AND NEW.accepted_at < i.lease_until
        AND EXISTS(SELECT 1 FROM notification_attempt_events e WHERE e.attempt_id = a.id AND e.kind = 'accepted'))
BEGIN SELECT RAISE(ABORT, 'watermark requires current accepted delivery'); END;
CREATE TRIGGER notification_watermark_update BEFORE UPDATE ON device_channel_watermarks
BEGIN
    SELECT RAISE(ABORT, 'watermark identity and history must be retained')
    WHERE NEW.device_id != OLD.device_id OR NEW.channel_id != OLD.channel_id OR NEW.accepted_at < OLD.accepted_at;
    SELECT RAISE(ABORT, 'watermark requires current accepted delivery') WHERE NOT EXISTS(
        SELECT 1 FROM notification_attempts a JOIN notification_intents i ON i.id = a.intent_id
        JOIN devices d ON d.id = i.device_id JOIN firmware_observations o ON o.id = a.observation_id
        JOIN notification_channels c ON c.id = i.channel_id
        JOIN catalog_models m ON m.id = o.model_id
        JOIN modules s ON s.id = m.module_id
        JOIN catalog_verification_attempts v ON v.id = o.attempt_id
        WHERE a.id = NEW.attempt_id AND i.device_id = NEW.device_id AND i.channel_id = NEW.channel_id
            AND i.target_key = NEW.target_key AND i.target_display = NEW.target_display AND i.state = 'delivered'
            AND i.delivered_at = NEW.accepted_at AND i.claim_token = a.claim_token AND i.claim_generation = a.claim_generation
            AND d.revision = a.expected_device_revision AND d.catalog_model_id = o.model_id
            AND i.owner_instance = a.owner_instance AND i.observation_id = a.observation_id
            AND i.expected_device_revision = a.expected_device_revision
            AND c.config_revision = a.channel_config_revision
            AND v.config_generation = s.config_generation AND m.observation_generation = o.generation
            AND NEW.accepted_at >= a.claimed_at AND NEW.accepted_at < i.lease_until
            AND EXISTS(SELECT 1 FROM notification_attempt_events e WHERE e.attempt_id = a.id AND e.kind = 'accepted'));
END;
