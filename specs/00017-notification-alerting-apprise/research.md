# Research: Apprise Notification Dispatch & Integration

> Research on Apprise integration, SMTP dispatch, Gotify push, credentials management, and non-blocking notification handling.

## Topic 1: Apprise Integration
Apprise is an excellent Python-based library that abstracts over 80+ notification services using simple URL schemas (e.g., `mailto://`, `gotify://`). It allows setting up multiple notification targets in a single configuration. When integrating Apprise in FastAPI applications, keeping the setup stateless and thread-safe is crucial. Since dispatching notifications involves outbound HTTP/SMTP I/O, runs should be executed in an asynchronous thread executor or via non-blocking async operations to prevent blocking the core FastAPI event loop.
- **Source 1**: Apprise official documentation (https://github.com/caronc/apprise)
- **Source 2**: Apprise URL Schema Reference (https://github.com/caronc/apprise/wiki)

## Topic 2: SMTP/Email & Gotify Dispatch Best Practices
- **SMTP Configuration**: Requires server, port (587 for STARTTLS or 465 for SSL/TLS), username, password, and sender/receiver addresses. Apprise handles this with URLs like `mailtos://user:pass@smtp.server.com:587?to=recip@domain.com`.
- **Gotify Push Configuration**: Gotify uses simple REST-based token authorization over HTTP/HTTPS. Apprise translates this via the `gotify://hostname/token` schema.
- **Resilience**: SMTP/Gotify outbound connections are prone to intermittent network drops, DNS failures, or credential expiration. The calling system must treat dispatch as a non-fatal side effect. The core detection check-result must still be recorded and marked as successful even if notification dispatch fails, adhering to the "honest failure" principle by logging the dispatch failure in the activity log.

## Topic 3: Homelab Security & Credentials Management
- **Environment & Docker Secrets**: Homelab operators expect credentials (e.g., SMTP passwords, Gotify tokens) to be injected securely without baking them into image builds. Binocular uses standard environment variables and the `_FILE` suffix convention to load secrets from Docker/Kubernetes mounted files (e.g., `SMTP_PASSWORD_FILE=/run/secrets/smtp_pass`).
- **LAN Posture**: The UI configuration endpoints for saving Notification Channel definitions must handle passwords/tokens securely, masking them in read requests (e.g., returning `********`) and ensuring raw SQL parameterized queries are used exclusively to persist settings in SQLite.
