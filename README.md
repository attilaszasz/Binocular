# Binocular

Binocular is a self-hosted firmware-update watcher for offline devices — cameras, lenses, and homelab hardware that manufacturers never auto-update. It runs as a single Docker container on your private LAN, periodically checking manufacturer firmware pages through user-installed extension modules, and notifying you via Email/SMTP or Gotify when a newer version is detected.

**The value**: replace a manual, easy-to-forget, fragmented chore with reliable, unattended monitoring that surfaces only when action is needed.

**The promise**: honest failure signaling (never silently miss an update), zero-config startup, single-volume data persistence, non-root container execution, and respectful scraping of third-party sites — all with no external database, no cloud dependency, no telemetry, and no account.

---

## How It Works

1. **You maintain an inventory** of your offline devices, each linked to an extension module that defines its device type (e.g., "Sony E-Mount Lenses").
2. **You record the current firmware version** for each device as you physically update it.
3. **Binocular periodically checks** manufacturer pages using the linked module — on a configurable per-device-type schedule — comparing the latest published version against your recorded version.
4. **When a newer version is found**, Binocular dispatches a notification through your configured channels (Email/SMTP, Gotify).
5. **You update the device physically**, then confirm the new version in one click — resetting alert status until the next update appears.

Extension modules are user-authored Python scripts that implement a documented authoring contract. They run unsandboxed, in-process, with full application privileges — an explicit, user-vetted trust boundary. Two official starter modules for Sony Alpha and Panasonic Lumix are bundled and automatically seeded on startup.

---

## Quick Start (Docker Compose)

```yaml
services:
  binocular:
    image: ghcr.io/attilaszasz/binocular:latest
    container_name: binocular
    restart: unless-stopped
    env_file:
      - .env
    ports:
      - "8000:8000"
    volumes:
      - binocular-data:/app/data
      - binocular-modules:/app/modules
    environment:
      BINOCULAR_AUTH_ENABLED: "false"

volumes:
  binocular-data:
  binocular-modules:
```

Save as `compose.yaml`, create an `.env` file (see below), then:

```bash
docker compose up -d
```

Open `http://<your-host>:8000` in a browser.

### .env File

Create an `.env` file next to `compose.yaml`:

```dotenv
# Network
BINOCULAR_HOST=0.0.0.0
BINOCULAR_PORT=8000

# Data directories (must match volume mounts)
BINOCULAR_DATA_DIR=/app/data
BINOCULAR_MODULES_DIR=/app/modules

# Optional basic auth (disabled by default)
BINOCULAR_AUTH_ENABLED=false
BINOCULAR_AUTH_USERNAME=
BINOCULAR_AUTH_PASSWORD=
# Use _FILE variant for Docker secrets:
# BINOCULAR_AUTH_PASSWORD_FILE=/run/secrets/binocular_auth_password

# Notification — SMTP
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=user@example.com
SMTP_PASSWORD=your-password
SMTP_FROM=noreply@example.com
SMTP_USE_TLS=true

# Notification — Gotify
GOTIFY_URL=https://gotify.example.com
GOTIFY_TOKEN=your-gotify-app-token

# Backup (optional)
BINOCULAR_BACKUP_SCHEDULE_HOURS=24
BINOCULAR_BACKUP_RETENTION_COUNT=7
```

All environment variables support a `_FILE` suffix convention for Docker secrets — set `SMTP_PASSWORD_FILE` to read the credential from a file instead of `SMTP_PASSWORD`.

Binocular starts with zero required configuration. Only `BINOCULAR_HOST`, `BINOCULAR_PORT`, and the volume mounts are truly needed for first run.

---

## Container Image

Binocular is distributed as a single multi-architecture Docker image published to GitHub Container Registry:

```
ghcr.io/attilaszasz/binocular
```

The image covers both `linux/amd64` (x86 servers, mini-PCs) and `linux/arm64` (Raspberry Pi 4/5, ARM SBCs).

### Tags

| Tag | Description |
|-----|-------------|
| `latest` | Most recent release |
| `v<major>.<minor>` | Pinned to a minor release line (e.g., `v1.0`) |
| `v<major>.<minor>.<patch>` | Pinned to an exact release (e.g., `v1.0.0`) |

**Pin a specific version tag** for production deployments. Relying on `latest` makes rollbacks and support harder.

To upgrade to a new release, update the image tag in `compose.yaml` and run:

```bash
docker compose pull && docker compose up -d
```

The container runs as the non-root `binocular` user and uses a shallow `/healthz` HEALTHCHECK every 30 seconds.

---

## Volumes

| Volume | Container Path | Purpose |
|--------|---------------|---------|
| `binocular-data` | `/app/data` | SQLite database (`binocular.db`), backup snapshots, migration pre-backups |
| `binocular-modules` | `/app/modules` | User-uploaded and auto-seeded extension modules (`.py` files) |

Both volumes must be persistent. Backing up Binocular means backing up the `binocular-data` volume — a single SQLite file contains all state. Copy the volume files or use the built-in scheduled backup job (see below).

---

## Ports

A single port is exposed:

| Port | Protocol | Purpose |
|------|----------|---------|
| `8000` | HTTP | Serves the React SPA, REST API (`/api/v1`), and `/healthz` |

The application does not expose TLS itself — place a reverse proxy (Caddy, Traefik, Nginx) in front of it if you need HTTPS or expose the UI beyond your trusted LAN.

---

## Optional Basic Auth

By default, Binocular has no authentication — it assumes a private, trusted LAN with a single user. Optional HTTP Basic Auth can be enabled for operators who expose the UI more broadly or reverse-proxy it:

```dotenv
BINOCULAR_AUTH_ENABLED=true
BINOCULAR_AUTH_USERNAME=admin
BINOCULAR_AUTH_PASSWORD=your-strong-password
```

Basic auth is light protection for trusted-network or TLS reverse-proxy deployments. **It is not a substitute for network isolation, TLS, or a public-internet security model.** Do not expose Binocular directly to untrusted networks.

---

## Extension Modules

Extension modules are the pluggable intelligence that teaches Binocular how to check firmware versions for a specific device type. Each module is a Python script implementing the authoring contract — it receives a polite HTTP client from the host and returns the latest available firmware version in a standardized format.

### Official Modules (Bundled)

Two starter modules ship with the image and are automatically seeded into the database on startup:

- **Sony Alpha** — covers Sony E-mount camera bodies and lenses
- **Panasonic Lumix** — covers Panasonic Lumix camera bodies and lenses

These serve as both immediate value and working examples for writing your own modules.

### Adding Modules

Upload, update, and delete modules through the UI (Settings > Modules). Uploads are gated by two-phase validation (static AST checks + optional runtime proof) — invalid modules are rejected before they reach the modules directory, with structured per-phase feedback.

### Trust Boundary

**Extension modules execute unsandboxed, in-process, with full application privileges.** Installing a module is equivalent to running arbitrary code. You are responsible for vetting any module you install — whether written by you, imported from a friend, or obtained from a community source. Non-root container execution limits host-level blast radius but is not a sandbox.

For module authoring guidance, see `docs/modules-authoring-guide.md`.

---

## Notifications

Binocular dispatches notifications through [Apprise](https://github.com/caronc/apprise). Two channels are supported at launch:

- **Email / SMTP** — any SMTP server you control or have credentials for
- **Gotify** — a self-hosted push notification server

Configure channels in the UI (Settings > Notifications) or via environment variables in `.env`. A detected update dispatches to all configured channels. Dispatch failures are logged in the activity log for visibility; the check result is preserved regardless.

---

## Backups

All state lives in `binocular.db` on the `/app/data` volume. Binocular provides two backup mechanisms:

### Scheduled Backups

A built-in scheduler produces live-safe, consistent single-file snapshots using SQLite's Online Backup API:

| Environment Variable | Default | Description |
|---|---|---|
| `BINOCULAR_BACKUP_SCHEDULE_HOURS` | `24` | Interval in hours; `0` disables |
| `BINOCULAR_BACKUP_RETENTION_COUNT` | `7` | Snapshots to keep; `0` = unlimited |

Snapshots are written to `<data_dir>/backups/scheduled/`. Copy these off-host to a NAS or second disk for disaster recovery.

### Pre-Migration Snapshots

Before applying any pending database migration on startup, Binocular takes an automatic pre-migration snapshot at `<data_dir>/backups/`. This guarantees a known-good rollback point if a migration causes issues.

### Restore

See `docs/restore.md` for the full restore runbook. The short version: stop the container, copy the snapshot over `binocular.db`, remove stale `-wal`/`-shm` files, and start.

**Do not plain-`cp` the database file while the container is running** — SQLite uses WAL-mode journaling, and copying the `.db` without its `-wal` and `-shm` sidecar files risks data loss.

---

## Application Settings

All configuration is done through environment variables. No config files inside the container.

| Variable | Default | Description |
|---|---|---|
| `BINOCULAR_HOST` | `0.0.0.0` | Host to bind |
| `BINOCULAR_PORT` | `8000` | Port to bind |
| `BINOCULAR_DATA_DIR` | `/app/data` | Path to the data directory |
| `BINOCULAR_MODULES_DIR` | `/app/modules` | Path to the modules directory |
| `BINOCULAR_AUTH_ENABLED` | `false` | Enable optional HTTP Basic Auth |
| `BINOCULAR_AUTH_USERNAME` | — | Auth username (required if enabled) |
| `BINOCULAR_AUTH_PASSWORD` | — | Auth password |
| `BINOCULAR_AUTH_PASSWORD_FILE` | — | Path to a file containing the password |
| `SMTP_HOST` | — | SMTP server hostname |
| `SMTP_PORT` | — | SMTP server port |
| `SMTP_USERNAME` | — | SMTP username |
| `SMTP_PASSWORD` | — | SMTP password |
| `SMTP_PASSWORD_FILE` | — | Path to file containing SMTP password |
| `SMTP_FROM` | — | From address for notification emails |
| `SMTP_USE_TLS` | `true` | Use STARTTLS for SMTP |
| `GOTIFY_URL` | — | Gotify server URL |
| `GOTIFY_TOKEN` | — | Gotify application token |
| `GOTIFY_TOKEN_FILE` | — | Path to file containing Gotify token |
| `BINOCULAR_BACKUP_SCHEDULE_HOURS` | `24` | Backup interval; `0` to disable |
| `BINOCULAR_BACKUP_RETENTION_COUNT` | `7` | Snapshots to retain; `0` for unlimited |

---

## Updating

1. Update the image tag in `compose.yaml` to the desired version.
2. Pull the new image and recreate the container:

   ```bash
   docker compose pull && docker compose up -d
   ```

3. Verify:

   ```bash
   curl -f http://localhost:8000/healthz
   docker compose logs -f binocular
   ```

Data persists across upgrades — the SQLite database on the `binocular-data` volume is untouched. Database migrations apply automatically on startup. A pre-migration backup is taken before any pending migration runs, so you can roll back safely if needed.

### Rollback

Pin the previous known-good version tag in `compose.yaml`, then:

```bash
docker compose pull && docker compose up -d
```

If the upgrade included a schema migration, restore the pre-migration backup first (see `docs/restore.md`).

---

## Activity Log

All check activity and errors are recorded in a size-bounded, rolling activity log persisted in SQLite and viewable in the UI. Each entry includes contextual fields — device, module name, timestamp — so you can see honest status and history at a glance. Failed scrapes, notification dispatch errors, and module timeouts all appear here.

---

## Observability

- **Structured logging**: JSON/key=value logs via `structlog` emit to stdout/stderr — use `docker compose logs -f` to follow.
- **Health check**: `GET /healthz` returns process liveness + SQLite reachability — used by Docker HEALTHCHECK.
- **Activity log**: In-UI, size-bounded view of all check activity and errors.
- **No telemetry**: Binocular collects no usage data, analytics, or external telemetry — by design.

---

## Security Posture

- **Trusted LAN only** — the application is designed for a private, trusted network with a single operator.
- **Non-root container** — runs as the `binocular` user with `no-new-privileges` and all capabilities dropped.
- **No hardcoded secrets** — credentials load from environment variables or `_FILE` Docker-secret paths.
- **Parameterized SQL** — all queries use parameter binding; no raw string interpolation.
- **Extension trust boundary** — modules execute unsandboxed with full app privileges. This is an explicit, accepted arbitrary-code-execution risk mitigated by non-root execution and operator vetting, not by sandboxing.
- **Polite scraping** — all outbound requests flow through a central HTTP client that honors `robots.txt` (RFC 9309), sends an identifiable User-Agent, and enforces per-domain rate limiting with exponential backoff.

---

## Architecture

Binocular is a single-process modular monolith:

- **Backend**: Python 3.13, FastAPI, Uvicorn, aiosqlite, APScheduler, Apprise, httpx, structlog
- **Frontend**: TypeScript 5.x, React 18, Vite, Tailwind CSS, React Router, TanStack Query
- **Storage**: SQLite single file via aiosqlite — no ORM, no external database server
- **Container**: `python:3.13-slim`, single port 8000, two volumes, non-root

The SPA is compiled by Vite during the multi-stage Docker build and served by FastAPI via `StaticFiles` — single image, single port.

For full architectural context, see `docs/tech-context.md` and `specs/sad.md`.

---

## Building from Source

```bash
# Clone and build
git clone https://github.com/attilaszasz/Binocular.git
cd Binocular
docker build -t binocular:local .

# Run with compose
docker compose up -d
```

### Development (Without Docker)

**Backend:**

```bash
cd backend
python -m pip install -e ".[dev]"
uvicorn binocular.main:app --host 0.0.0.0 --port 8000
```

**Frontend:**

```bash
cd frontend
npm ci
npm run dev
```

Health check:

```bash
curl http://127.0.0.1:8000/healthz
```

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend runtime | Python 3.13 |
| Backend framework | FastAPI + Uvicorn |
| Database | SQLite via aiosqlite (raw SQL, no ORM) |
| Scheduling | APScheduler (in-process) |
| Notifications | Apprise (Email/SMTP, Gotify) |
| HTTP client | httpx (async) |
| Logging | structlog (structured, stdout) |
| Frontend runtime | Node.js 22 |
| Frontend framework | React 18 + TypeScript 5.x |
| Build tool | Vite |
| Styling | Tailwind CSS |
| Routing | React Router |
| Data fetching | TanStack Query |
| Form handling | React Hook Form |
| Container base | `python:3.13-slim` |
| CI/CD | GitHub Actions |
| Registry | GitHub Container Registry (GHCR) |

---

## Documentation

| Document | Purpose |
|---|---|
| `docs/restore.md` | Database backup and restore procedures |
| `docs/release.md` | Maintainer release runbook |
| `docs/modules-authoring-guide.md` | How to write extension modules |
| `specs/prd.md` | Product Requirements Document |
| `specs/sad.md` | Software Architecture Document |
| `specs/dod.md` | Deployment & Operations Document |
| `specs/project-plan.md` | Project Implementation Plan |

---

## License

See [LICENSE](LICENSE).
