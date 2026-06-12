---
spec_type: technical
epic_id: E021
epic_sources: [specs/project-plan.md]
spec_maturity: draft
---

# Feature Specification: Environment-Based Notification Settings

## Problem Statement
Operators deploying Binocular via Docker need a declarative, GitOps-friendly method to configure notification channels and authentication options directly from container environment variables. Currently, all SMTP and Gotify settings must be manually configured in the web UI, which stores them in SQLite. Fulfilling this need without database synchronization causes the UI to display channels as disabled and empty, confusing operators and preventing end-to-end set-and-forget automation.

## Scope

### Included
- Parsing notification settings (SMTP and Gotify) and basic auth state from container environment variables.
- Supporting both prefixed (e.g., `BINOCULAR_SMTP_HOST`) and non-prefixed (e.g., `SMTP_HOST`) environment variable names.
- Extending the secret file resolution logic (`_FILE` suffix mapping) to allow non-prefixed credential files (e.g. `SMTP_PASSWORD_FILE` and `GOTIFY_TOKEN_FILE`).
- Automatically seeding and updating the `notification_channels` SQLite table on application startup if respective environment variables are provided.
- Ensuring the web UI displays and masks the synced environment configurations seamlessly.

### Excluded
- Dynamic hot-reloading of environment variables while the container is running (requires container restart).
- Support for multiple SMTP servers or multiple Gotify targets (only one active target of each type is supported).

### Edge Cases & Boundaries
- **Credentials Masking in UI**: Seeded passwords/tokens must be masked in the UI as `********` when read, matching UI input protection behavior.
- **Empty Settings Override**: If environment variables are set to empty values (e.g. `SMTP_HOST=""`), the seeding process should not enable the channel or overwrite existing valid database settings.
- **TLS/STARTTLS resolution**: Apprise handles STARTTLS automatically, but if `SMTP_PORT` is set to 465, Apprise secure parameter must be set to `yes`.

## Technical Objectives

### OBJ-001: Environment Configuration Parsing
- **Priority**: P1
- **Rationale**: The Settings model must load the custom environment variables using appropriate fallback aliases.
- **Deliverables**: Updated `Settings` model in `config.py`.
- **Validation**: Mypy strict passes; unit tests verify that values from both `BINOCULAR_` prefixed and non-prefixed env vars are loaded.

### OBJ-002: Automatic Database Seeding
- **Priority**: P1
- **Rationale**: Synchronizing environment configurations to the database on startup is essential for the NotifierService and frontend UI to recognize the active channels.
- **Deliverables**: Seeder utility and hook in app lifecycle startup.
- **Validation**: Seeder updates the database on startup; unit tests verify SQL upserts.

## Requirements

### Technical Requirements
- **TR-001**: Add the following fields to the `Settings` class in [config.py](file:///Users/attila/git/Binocular/backend/src/binocular/config.py):
  - `smtp_host`: string, alias for `SMTP_HOST`
  - `smtp_port`: integer, default `587`, alias for `SMTP_PORT`
  - `smtp_use_tls`: boolean, default `True`, alias for `SMTP_USE_TLS`
  - `smtp_username`: string, alias for `SMTP_USERNAME`
  - `smtp_password`: string, alias for `SMTP_PASSWORD`
  - `smtp_from`: string, alias for `SMTP_FROM`
  - `smtp_to`: string, alias for `SMTP_TO`
  - `gotify_url`: string, alias for `GOTIFY_URL`
  - `gotify_token`: string, alias for `GOTIFY_TOKEN`
  - Allow `basic_auth_enabled` to be read from `BINOCULAR_AUTH_ENABLED` as an alias.
- **TR-002**: Extend the Pydantic validator `load_secret_files` to search for both prefixed and non-prefixed secret files (e.g., `SMTP_PASSWORD_FILE` and `GOTIFY_TOKEN_FILE`).
- **TR-003**: Create a `NotificationSettingsSeeder` service that initializes or updates `notification_channels` in SQLite at startup (after migrations run in lifespan).
- **TR-004**: If `smtp_host` is defined in `settings`, update/insert the `email` row in `notification_channels` with `enabled = 1` and store its settings in the JSON configuration payload.
- **TR-005**: If `gotify_url` is defined in `settings`, update/insert the `gotify` row in `notification_channels` with `enabled = 1` and store its settings in the JSON configuration payload.

## Key Entities
- **Settings**: Configuration attributes loaded from environment.
- **NotificationChannel**: SQLite database entity (`notification_channels` table) stored as `(type, enabled, config)`.

## Assumptions & Risks

### Assumptions
- The operator will restart the container when they change their environment configuration.
- Providing `SMTP_HOST` or `GOTIFY_URL` indicates the operator intends to enable that notification channel.

### Risks
- **Precedence overlap**: The operator edits settings in the UI, then restarts the container, causing environment variables to overwrite database changes. This is a known consequence of container-based configuration.

## Implementation Signals
- `NEW-CONFIG`: Mapped environment settings for SMTP and Gotify in [config.py](file:///Users/attila/git/Binocular/backend/src/binocular/config.py).
- `NEW-WORKER`: Seeder logic executed during application lifespan startup in [app.py](file:///Users/attila/git/Binocular/backend/src/binocular/app.py).

## Success Criteria
- **SC-001**: Setting environment variables like `SMTP_HOST` automatically creates an enabled `email` notification channel database record on application startup.
- **SC-002**: Setting `GOTIFY_URL` and `GOTIFY_TOKEN` creates an enabled `gotify` notification channel database record on application startup.
- **SC-003**: In-app UI and test email/gotify REST routes successfully retrieve and use these configurations with masked secrets.

## Compliance Check

*Status: PASS*
- Standard Pydantic settings parsing obeys strict static typing rules.
- Secrets loading via files does not expose raw credentials in logs or images.
