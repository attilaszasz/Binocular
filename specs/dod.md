# Deployment & Operations Document: Binocular

> Date: 2026-06-10 | Status: Draft

## Deployment Summary and Context

Binocular ships as a **single, self-contained Docker image** that an operator runs on a private, trusted LAN. The deployment goal is set-and-forget homelab operation: one container, one port, one data volume, non-root, zero external dependencies (no database server, broker, or cloud service). This document covers how that image is built, distributed, configured, backed up, and operated. It complements — and does not repeat — the architecture in [specs/sad.md](sad.md).

Operational ambition is intentionally **homelab-grade and minimal**: there is no environment ladder, no SLO/error-budget/on-call machinery, no IaC, and no external telemetry.

## Environment Strategy

Binocular has two effective environments: a developer workstation and the operator's production instance. They run the same image; there is no shared staging tier.

| Environment | Purpose | Promotion Gate | Data Strategy | Parity with Prod |
|-------------|---------|----------------|---------------|------------------|
| Local (dev) | Build, test, and validate modules locally | CI green on PR | Seed/fixtures + golden module tests | High — identical image build |
| Production (operator) | The operator's live homelab instance | Operator pulls a published SemVer tag | Real SQLite data on a persistent volume | Baseline |

### Environment Flow

```mermaid
flowchart LR
    Dev["Local<br>build + test"] --> CI["GitHub Actions<br>lint, test, scan, build"]
    CI --> GHCR["GHCR<br>versioned + latest image"]
    GHCR --> Prod["Operator instance<br>docker compose pull + up"]
```

### Progressive Rollout

- **Feature flags**: None. Behavior is controlled by environment variables and the operator's chosen image tag.
- **Rollout strategy**: Operator-driven. Each release is a published image tag; the operator updates when they choose.
- **Rollback trigger**: Operator pins the previous known-good SemVer tag and recreates the container (see [Rollback](#rollback)).

## Deployment Targets and Packaging

- **Deployment model**: Single OCI container image (multi-stage build — Node stage compiles the Vite SPA, final `python:3.13-slim` stage serves it via FastAPI `StaticFiles`).
- **Build artifact**: One Docker image, multi-arch `linux/amd64` + `linux/arm64` (covers x86 homelab hosts and ARM SBCs such as Raspberry Pi).
- **Container registry**: GitHub Container Registry (GHCR), public — `ghcr.io/<owner>/binocular`.
- **Image tagging**: Driven by SemVer git tags via `docker/metadata-action` — `{{version}}`, `{{major}}.{{minor}}`, and `latest`. The `{{major}}` tag is enabled only for `>= v1.0.0`. Base image pinned by digest for reproducibility.
- **Vulnerability scanning**: Trivy (`aquasecurity/trivy-action`) in CI against the built image; fail on HIGH/CRITICAL with available fixes. Weekly scheduled re-scan of the published image since it is long-lived.
- **SBOM / provenance**: Emitted by buildx (`sbom: true`, `provenance: true` on `build-push-action`) and attached as OCI attestations.

## CI/CD Pipeline Design

### Pipeline Stages

```mermaid
flowchart LR
    Lint["Lint &<br>Type-check"] --> Test["Test<br>(pytest, vitest)"]
    Test --> Build["Buildx<br>amd64+arm64"]
    Build --> Scan["Trivy<br>scan + SBOM"]
    Scan --> Push["Push to GHCR<br>(tags only)"]
```

- **Pipeline tooling**: GitHub Actions.
- **Quality gates (PRs and pushes)**: Ruff + mypy `--strict` (backend), Biome/ESLint + `tsc` (frontend); `pytest` + `pytest-asyncio`, Vitest + React Testing Library, one Playwright smoke test, and golden/fixture module-correctness tests.
- **Build stack**: `docker/setup-qemu-action` → `docker/setup-buildx-action` → `docker/login-action` (GHCR via `GITHUB_TOKEN`, `permissions: packages: write`) → `docker/metadata-action` → `docker/build-push-action` with `platforms: linux/amd64,linux/arm64`.
- **Publish condition**: Images are pushed only on SemVer tag refs; PR builds build-but-do-not-push. Layer caching via `type=gha` (`mode=max`).
- **Secrets in pipeline**: Only the built-in `GITHUB_TOKEN` for GHCR; no application secrets are baked into the image or passed as build args.

## Infrastructure and Hosting

- **Hosting**: Self-hosted by the operator (homelab host, NAS, mini-PC, or SBC). No cloud provider.
- **Compute model**: A single Docker container managed by Docker / Docker Compose. No orchestrator assumed or required.
- **Networking**: One exposed port (`8000`) on the trusted LAN. TLS, if desired, is provided by the operator's own reverse proxy — out of scope for the image.
- **Storage infrastructure**: Two persistent volumes — `/app/data` (SQLite `binocular.db`) and `/app/modules` (user extension `.py` files). Operator-managed; backed up by file/volume copy.
- **Container hardening**: Non-root user configurable via `PUID`/`PGID` environment variables (default `PUID=1000 PGID=1000`), applied at entrypoint via user/group creation and `su-exec`; `no-new-privileges:true`, `cap_drop: [ALL]`; optional `read_only` rootfs with a `tmpfs` for `/tmp`. See {SAD:ADR-0008}, {SAD:ADR-0001}.

### Infrastructure Diagram

```mermaid
flowchart TB
    subgraph Host["Self-hosted Host (Docker)"]
        subgraph Container["binocular (python:3.13-slim, non-root)"]
            App["Uvicorn :8000<br>FastAPI + SPA + APScheduler"]
        end
        Vol1["Volume /app/data<br>binocular.db"]
        Vol2["Volume /app/modules<br>.py extensions"]
    end
    Operator["Operator browser<br>(LAN)"] --> App
    App --> Vol1
    App --> Vol2
    App --> Vendor["Manufacturer pages"]
    App --> Notify["Email / Gotify"]
    Backup["Nightly backup<br>to NAS / 2nd disk"] -.copies.-> Vol1
```

## Observability and Monitoring

No external telemetry, metrics backend, or APM — by design.

### Logging
- **Approach**: Structured (JSON / key=value) logs via `structlog` with contextual fields (`device_id`, `module_name`), written to **stdout/stderr only**.
- **Aggregation**: `docker logs` / `docker compose logs -f`. The operator's Docker logging driver handles rotation.
- **In-app activity log**: A bounded, size-limited recent-events log persisted in SQLite and viewable in the UI.

### Metrics
- **Application signals**: Surfaced in the UI, not exported — failed-scrape count, last-success timestamps per device/module, notification dispatch failures.
- **Infrastructure signals**: Container health and data-volume disk usage observed via the operator's own Docker tooling.

### Health Checking
- **Container HEALTHCHECK**: `--interval=30s --timeout=5s --start-period=20s --retries=3` against a cheap `/healthz` endpoint. Drives `docker ps` health status and `restart` policy.

### Alerting
- **Self-notification**: Binocular can dispatch operational failures through its own Apprise channels.
- **Official module health**: In-app notification when a shipped official module consistently fails scraping (CAP-014).
- **What the operator watches**: container health = healthy; failed-scrape trend; notification dispatch failures; `/app/data` disk-usage growth; container restart loops.

## Reliability Engineering

- **Availability target**: Best-effort homelab availability; `restart: unless-stopped` plus the HEALTHCHECK recover from crashes.
- **RPO** (Recovery Point Objective): **≤ 24h** — a nightly backup of `/app/data` to a second host/disk/NAS.
- **RTO** (Recovery Time Objective): **≤ 1h** — pull the image tag, restore the data file, `docker compose up -d`.

### Backup and Restore
- **Backup (live-safe)**: Use SQLite `VACUUM INTO 'backup.db'` or the Online Backup API (`Connection.backup()`) for a consistent single-file snapshot. A scheduled (APScheduler) nightly job produces the snapshot; the operator copies it offsite.
- **Raw-copy caveat**: If copying the volume directly, copy `binocular.db` together with its `-wal`/`-shm` files, or run `PRAGMA wal_checkpoint(TRUNCATE)` first.
- **Restore**: Stop the container → replace `/app/data/binocular.db` (and remove stale `-wal`/`-shm`) → start. Boot path runs `PRAGMA integrity_check;`.
- **Disaster recovery**: One offsite copy is sufficient at homelab scale.

### Migration Safety
- Schema migrations run at startup inside a transaction, gated by `schema_version` / `PRAGMA user_version`, forward-only and idempotent. An automatic **pre-migration backup** is taken so a failed migration or a rollback to a previous image tag is recoverable. See {SAD:ADR-0004}.

### Production Readiness
- Non-root image builds and HEALTHCHECK pass.
- A restore from backup has been verified at least once.
- SMTP and/or Gotify notification channels validated end-to-end.
- Operator has pinned a specific SemVer tag.

## Security and Compliance in Operations

### Supply Chain Security
- **SBOM**: buildx-generated, attached as an OCI attestation.
- **Dependency scanning**: Trivy in CI; backend deps hash-pinned (`uv.lock`), frontend via `package-lock.json` + `npm ci`.
- **Artifact provenance**: buildx provenance attestation on published images.

### Runtime Security
- **Trust boundary**: Extension modules in `/app/modules` execute **unsandboxed, in-process, with full app privileges**. Accepted under the trusted-LAN single-user threat model. Operators must **not** expose port 8000 to untrusted networks. See {SAD:ADR-0005}, {SAD:ADR-0008}.
- **Container**: non-root user (PUID/PGID configurable), `no-new-privileges`, `cap_drop: [ALL]`, optional read-only rootfs.

### Secrets Management
- **Secrets store**: Environment variables, with the `_FILE` convention for Docker/Compose secrets.
- **Rotation**: Operator-managed; update the secret/env and recreate the container.
- **Access pattern**: Injected at runtime; never baked into the image.

### Compliance
- **Frameworks**: None applicable (single-user, self-hosted, no personal-data processing beyond the operator's own inventory).

## Operational Ownership and Processes

- **Ownership model**: The self-hosting operator is the sole owner and operator. Project maintainers own the image, CI, and release tags.
- **Change management**: PR-based with CI quality gates; releases cut by tagging a SemVer version.
- **Documentation expectations**: A `compose.yaml` example, `.env.example`, README run/upgrade instructions, and a module dev/test kit.

### Update Workflow

```mermaid
flowchart LR
    Pin["Pin version tag<br>in compose.yaml"] --> Pull["docker compose pull"]
    Pull --> Up["docker compose up -d<br>(recreate, volumes persist)"]
    Up --> Verify["Verify health<br>+ activity log"]
```

### Rollback

- Pin the previous known-good SemVer tag in `compose.yaml`, then `docker compose pull && docker compose up -d`.
- Because migrations are forward-only, pair any rollback that crosses a schema change with the **pre-migration backup** taken at upgrade time.

## Cost Considerations

- **Estimated cost**: Effectively $0 beyond the operator's existing hardware and electricity. GHCR is free for public images; GitHub Actions covers public-repo CI.

## Deployment Decisions

### DDR-001: GitHub Actions → public multi-arch GHCR image driven by SemVer tags

- **Status**: Accepted
- **Context**: An OSS self-hosted app needs a free, trusted distribution channel covering both x86 and ARM homelab hosts, with reproducible, pinnable releases.
- **Decision**: Build with `docker buildx` (QEMU) in GitHub Actions for `linux/amd64` + `linux/arm64`, publish to public GHCR, and tag from SemVer git tags.
- **Rationale**: Zero cost for public repos, native fit with GitHub, arm64 reach for SBC users, version pinning for operators.

### DDR-002: Minimal homelab-grade operations posture

- **Status**: Accepted
- **Context**: The system is a single-user, trusted-LAN, no-telemetry app. Enterprise ops machinery would be disproportionate.
- **Decision**: Operate at homelab scale — Docker/Compose only, stdout logs + in-app activity log, a shallow HEALTHCHECK, Apprise self-notification, and file-copy backups.

### DDR-003: SQLite backup via Online Backup API / `VACUUM INTO`, not raw copy

- **Status**: Accepted
- **Context**: The data store is a WAL-mode SQLite file; naive copying under load risks an inconsistent snapshot.
- **Decision**: Take backups with `VACUUM INTO` or the Online Backup API on a nightly schedule, plus an automatic pre-migration snapshot.

### DDR-004: Linuxserver-style PUID/PGID entrypoint for configurable container user

- **Status**: Accepted
- **Context**: Operators mount persistent volumes owned by arbitrary host UIDs. A fixed non-root UID creates friction.
- **Decision**: Adopt the linuxserver.io pattern: an entrypoint script reads `PUID` and `PGID` environment variables (defaulting to `1000:1000`), creates a matching user/group, `chown`s the volumes, then drops privileges via `su-exec`.
- **Rationale**: Single established convention familiar to homelab operators; eliminates the most common permission support issue; backward compatible.

## Risks, Assumptions, Constraints, and Open Questions

### Risks

- Operator exposes port 8000 beyond the trusted LAN — mitigated only by documentation and optional basic auth.
- Operator never configures or tests backups — mitigated by shipping a built-in scheduled backup job and verified-restore documentation.
- Multi-arch QEMU build flakiness — mitigated by caching and optional native arm64 runners.

### Assumptions

- The host runs Docker (or a compatible runtime) with persistent volumes.
- The operator can reach a second disk/host/NAS for offsite backup copies.
- The operator controls their own TLS/reverse proxy if exposing beyond LAN.

### Constraints

- Single container, single port, single data volume, non-root, zero-config startup.
- No external database, broker, telemetry, or cloud dependency.

### Open Questions

- None. All prototype-era operational open questions have been resolved.
