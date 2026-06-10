---
feature_branch: "00008-self-hosted-operability"
created: "2026-06-10"
input: "E008 Self-Hosted Operability"
spec_type: "product"
spec_maturity: "draft"
epic_id: "E008"
epic_sources: "{PRD:CAP-009}{SAD:ADR-0008}{DOD:DDR-002}"
---

# Feature Specification: Self-Hosted Operability

**Feature Branch**: `00008-self-hosted-operability`  
**Created**: 2026-06-10  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: draft  
**Epic ID**: E008  
**Epic Sources**: {PRD:CAP-009}{SAD:ADR-0008}{DOD:DDR-002}  
**Product Document**: specs/prd.md

## Problem Statement

Self-hosters deploying applications in home labs require zero-config setup to quickly evaluate the software, but also need secure ways to inject credentials and protect the application from unauthorized access when exposed to their private LAN. If the system only supports raw environment variables for credentials, they risk leaking passwords in logs or container metadata, and if it lacks access controls, anyone on the local network can access the inventory. Providing a secure, zero-config, and optionally authenticated hosting posture ensures both reliability and data safety.

## Scope

### Included

- **Zero-Config Startup**: The application starts out of the box with sensible defaults for data directories, logging, and binding interfaces, with no initial environment configuration needed.
- **Configurable Database Path**: The operator can override the SQLite database file path using the `BINOCULAR_DB_PATH` environment variable.
- **Docker Secret Loading (`_FILE` pattern)**: Any environment variable defined in Settings (such as basic auth password, future SMTP/Gotify secrets) can be loaded from a file specified by a corresponding `<VAR_NAME>_FILE` environment variable.
- **Optional Basic Authentication**: Access control via optional HTTP Basic Authentication middleware, disabled by default, protecting all API and static assets except the container liveness probe `/healthz`.
- **Sensitive Log Masking**: Automatically mask the values of all configured credentials and secrets inside structured log messages, events, and stack traces.
- **Documentation**: A complete `.env.example` file documenting all configurable parameters, their defaults, and instructions for Docker secrets.

### Excluded

- **Multi-user accounts or role-based access control (RBAC)**: Single-user trusted LAN model is assumed; multiple accounts are out of scope.
- **Sandboxed execution of extension modules**: Extension modules run in-process as a vetted trust boundary.
- **HTTPS/TLS termination**: Handled by reverse proxies (e.g. Caddy, Nginx, Traefik) in homelab environments; out of scope for the application container.

### Edge Cases & Boundaries

- **Missing Secret File**: If a `*_FILE` environment variable is defined but points to a non-existent file or a file that is not readable, the application must fail fast during startup with a clear error.
- **Empty Secret File**: If a secret file exists but is empty or contains only whitespace, the system treats it as empty/unset and logs a warning.
- **Basic Auth Enabled but Password Empty**: If basic auth is enabled via env but the password is empty, startup must fail fast to prevent unsecured access under an "enabled" state.
- **Logging Exception Traces**: Stack traces from exceptions containing secret substrings must have the secret values masked before writing to stdout/stderr.

## User Scenarios & Testing

### User Story 1 - Zero-Config Startup & Configurable DB Path (Priority: P1)

As a self-hosting operator, I want to launch the Binocular container with no environment configuration so I can immediately see the web interface and start using the app. I also want the option to configure a custom database path using `BINOCULAR_DB_PATH` if I want to mount the database separately.

**Why this priority**: Core product requirement for prosumer/homelab audience. Zero-config startup lowers adoption friction.

**Independent Test**: Start the application with an empty environment, verify it binds to port 8000 and serves `/healthz` successfully, then stop it, run it with `BINOCULAR_DB_PATH=/tmp/custom.db`, and verify the database is created at `/tmp/custom.db`.

**Acceptance Scenarios**:

1. **Given** no custom database environment variables are set, **When** the application starts up, **Then** it creates and connects to the SQLite database at `/app/data/binocular.db`.
2. **Given** `BINOCULAR_DB_PATH` is set to `/tmp/custom_binocular.db`, **When** the application starts up, **Then** it creates and connects to the SQLite database at `/tmp/custom_binocular.db`.

### User Story 2 - Secure Secret Loading via Files (Priority: P1)

As a security-conscious operator, I want to store my sensitive passwords in files (such as Docker secrets) and supply their file paths using environment variables ending with `_FILE` (e.g. `BINOCULAR_SMTP_PASSWORD_FILE`), so that my plaintext credentials are not exposed in container configuration or environment listings.

**Why this priority**: Essential security measure to satisfy the least-privilege principal in Docker environments.

**Independent Test**: Create a temporary file with a secret password, start the application with `BINOCULAR_SMTP_PASSWORD_FILE` set to that file path, and verify that the application config resolves `smtp_password` to the file contents.

**Acceptance Scenarios**:

1. **Given** a file `/run/secrets/smtp_pass` containing `secure_smtp_password`, **When** `BINOCULAR_SMTP_PASSWORD_FILE=/run/secrets/smtp_pass` is set, **Then** `settings.smtp_password` resolves to `secure_smtp_password`.
2. **Given** both `BINOCULAR_SMTP_PASSWORD` and `BINOCULAR_SMTP_PASSWORD_FILE` are set, **When** settings are initialized, **Then** the file-based secret takes precedence.
3. **Given** `BINOCULAR_SMTP_PASSWORD_FILE` points to a non-existent file, **When** settings are initialized, **Then** the application fails to start and logs the missing path.

### User Story 3 - Optional Basic Authentication (Priority: P1)

As an operator exposing Binocular to my local network, I want to enable HTTP Basic Authentication by configuring a username and password, so that unauthorized devices on my LAN cannot view my inventory or change my settings.

**Why this priority**: Crucial capability for LAN exposure, resolving security requirements for trusted-LAN environments.

**Independent Test**: Start the app with `BINOCULAR_BASIC_AUTH_ENABLED=true`, request `/api/v1/devices` without headers and verify it returns a 401 response, request `/healthz` and verify it returns a 200 response, then request `/api/v1/devices` with valid credentials and verify it returns a 200 response.

**Acceptance Scenarios**:

1. **Given** `BINOCULAR_BASIC_AUTH_ENABLED=true` and basic auth credentials are set, **When** a client requests a page or API endpoint without an Authorization header, **Then** the server returns a 401 Unauthorized with a WWW-Authenticate header.
2. **Given** `BINOCULAR_BASIC_AUTH_ENABLED=true` and basic auth credentials are set, **When** a client requests `/healthz` without credentials, **Then** the server returns a 200 OK.
3. **Given** `BINOCULAR_BASIC_AUTH_ENABLED=true` and basic auth credentials are set, **When** a client sends correct basic auth headers, **Then** the server processes the request normally.

### User Story 4 - Sensitive Log Masking (Priority: P2)

As an operator monitoring container logs, I want any sensitive credentials (such as the basic auth password or SMTP password) to be automatically masked in the log output, so that secrets are not accidentally written to stdout or persistent log aggregators.

**Why this priority**: Hardening requirement to prevent secret leakage in operations.

**Independent Test**: Log a message containing the basic auth password value, and verify that the output console contains the masked string `********` instead of the plaintext password.

**Acceptance Scenarios**:

1. **Given** `BINOCULAR_BASIC_AUTH_PASSWORD` is set, **When** any component logs a message containing the password, **Then** the password value is replaced with `********` in the logged output.

## Integration Points

- **IP-001**: Application entrypoint (`app.py`) integrates the optional Basic Auth middleware using configured settings.
- **IP-002**: Database connection management (`db/connection.py`) resolves its SQLite connection path via the resolved settings `db_path` or `data_dir` fallback.
- **IP-003**: Future alerting dispatchers (Email, Gotify) depend on the secret file loader initialized by E008 settings.

## Requirements

### Functional Requirements

- **FR-001**: System MUST start with zero environment configuration.
- **FR-002**: System MUST allow configuring the SQLite database path via `BINOCULAR_DB_PATH`.
- **FR-003**: System MUST support the `_FILE` suffix pattern for all settings marked as secrets, reading the value from the specified file path.
- **FR-004**: System MUST fail fast during startup if a configured `_FILE` secret path does not exist or is unreadable.
- **FR-005**: System MUST provide optional basic-auth middleware, disabled by default.
- **FR-006**: System MUST bypass basic authentication for the `/healthz` endpoint.
- **FR-007**: System MUST fail fast during startup if basic-auth is enabled but the password is empty or not set.
- **FR-008**: System MUST mask all configured secrets (basic auth password, SMTP password, Gotify token) in log output.
- **FR-009**: System MUST ship a `.env.example` containing default parameters, descriptions, and instructions.

## Key Entities

- **Settings**: Configuration structure holding application parameters. Key attributes: `data_dir`, `modules_dir`, `db_path`, `basic_auth_enabled`, `basic_auth_username`, `basic_auth_password`, `smtp_password`, `gotify_token`.

## Assumptions & Risks

### Assumptions

- The operator is responsible for protecting the `.env` file and mounting secret files securely.
- Basic auth credentials do not need to support multiple user accounts.
- The `/healthz` endpoint does not expose any sensitive information and is safe to exclude from auth checks.

### Risks

- **[Risk 1]** *(likelihood: low, impact: high)*: Basic auth middleware fails to intercept a new route. Mitigation: Verify middleware is registered at the FastAPI application level, wrapping all routes, and specifically check both static and API paths.
- **[Risk 2]** *(likelihood: medium, impact: medium)*: Secrets are printed in logs via tracebacks. Mitigation: Configure the structlog processor to inspect and recursively mask secrets from exception text and event arguments.

## Implementation Signals

- `NEW-CONFIG` — Add `db_path`, `basic_auth_enabled`, `basic_auth_username`, `basic_auth_password`, `smtp_password`, and `gotify_token` to `Settings`.
- `NEW-API` — Implement Basic Auth ASGI middleware in `auth.py`.
- `BREAKING-CHANGE` — Change database connection logic in `db/connection.py` to use settings-resolved database path.
- `NEW-WORKER` — Add structlog secret masking processor in `utils/masking.py`.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: Application starts with no environment variables defined, and creates a database file at `/app/data/binocular.db`.
- **SC-002** [US1]: Setting `BINOCULAR_DB_PATH=/tmp/custom.db` creates a database file at `/tmp/custom.db`.
- **SC-003** [US2]: Setting `BINOCULAR_SMTP_PASSWORD_FILE=/path/to/file` successfully reads the password from the file.
- **SC-004** [US3]: Enabling basic auth protects API routes and static paths with a 401 response when unauthorized, but allows `/healthz` through.
- **SC-005** [US4]: Plaintext secrets are replaced by `********` in Console and JSON logs.

## Glossary

| Term | Definition |
|------|------------|
| Docker Secrets / `_FILE` pattern | A configuration pattern where an environment variable points to a file containing a secret, rather than holding the secret directly. |
| Basic Auth | Standard HTTP authentication protocol using a Base64-encoded username and password in the Authorization header. |
| Log Masking | The process of detecting and replacing sensitive values in logs with asterisks or dummy strings to prevent accidental leakage. |
