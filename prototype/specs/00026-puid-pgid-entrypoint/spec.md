---
feature_branch: "00026-puid-pgid-entrypoint"
created: "2026-06-07"
input: "E025 PUID/PGID Entrypoint"
spec_type: "operational"
spec_maturity: "clarified"
epic_id: "E025"
epic_sources: "{SAD:ADR-0008}, {DOD:DDR-004}"
---

# Feature Specification: PUID/PGID Entrypoint

**Feature Branch**: `00026-puid-pgid-entrypoint`
**Created**: 2026-06-07
**Status**: Draft
**Spec Type**: operational
**Spec Maturity**: clarified
**Epic ID**: E025
**Epic Sources**: {SAD:ADR-0008}, {DOD:DDR-004}
**Product Document**: [specs/prd.md](../prd.md)

## Problem Statement

The Docker container currently creates a fixed system user (`binocular`) with an arbitrary UID assigned by the image build process. Operators who mount host volumes into `/app/data` or `/app/modules` commonly encounter permission errors because the container's internal UID does not match their host UID. There is no way to configure the container user identity without manually `chown`ing the volume before first run, which creates friction and a recurring support burden. Without a configurable user mechanism, operators must either run diagnostics to discover the container UID or modify their host volume permissions, both of which violate the set-and-forget operability promise.

## Scope

### Included

- Add a Docker entrypoint script that reads `PUID` and `PGID` environment variables
- User/group creation based on `PUID`/`PGID` values inside the entrypoint; username defaults to `app`, groupname defaults to `app`
- Recursive `chown -R` of `/app/data` and `/app/modules` to the configured user on every start
- Privilege drop via `exec su-exec` (ensuring correct signal propagation for `docker stop`)
- Default `PUID=1000 PGID=1000` when env vars are not set; each defaults independently
- Installation of `su-exec` binary in the runtime Dockerfile stage (build-time choice; `gosu` as documented fallback if `su-exec` is unavailable for a target architecture)
- Update Dockerfile to set `ENTRYPOINT` to the new script

### Excluded

- Support for supplementary groups or complex GID mapping — single PGID only, matching linuxserver.io convention
- Migration of existing volume ownership — entrypoint sets ownership on every start; operators do not need to pre-chown

### Edge Cases & Boundaries

- `PUID=0` or `PGID=0` — entrypoint MUST refuse to run as root (preserve non-root constraint from {SAD:ADR-0008})
- `PUID` or `PGID` env var absent — silently use default (1000), no warning; separate from invalid-value case
- `PUID` or `PGID` present but not a valid unsigned integer in range 1–4294967294 (e.g. `abc`, `-1`, `3.14`, `0xFF`, ` 1001 ` with whitespace, or empty string `""`) — fall back to default (1000) for that var only, log a warning naming the invalid var and its value, and its fallback value. This validation also serves as injection prevention by rejecting shell metacharacters before values reach `useradd`/`groupadd` or shell expansion
- One var set, the other absent — each defaults independently (e.g. `PUID=1500` with absent `PGID` → UID 1500, GID 1000)
- Entrypoint re-chown fails due to read-only rootfs — container should still start, log a warning; ownership may be incorrect
- Neither `su-exec` nor `gosu` available in `PATH` — entrypoint MUST fail with a clear error message
- Existing user with the same UID already exists — skip creation, reuse existing user entry for that UID; confirm the matched user has a valid shell and home directory
- Group with the same GID already exists — reuse existing group, do not create a duplicate
- `PUID`/`PGID` values outside valid range (`< 1` or `> 4294967294`) — script-level validation error with clear message before calling OS tools

## Operational Objectives

### Objective 1 — PUID/PGID Entrypoint Script (Priority: P1)

Create the entrypoint shell script that implements linuxserver.io-style PUID/PGID support: read env vars, create user/group, chown volumes, drop privileges.

**Why this priority**: Core operability issue — permission errors on mounted volumes are the most common support friction for self-hosted containers; blocking for operators.

**Rationale**: The linuxserver.io PUID/PGID convention is the de facto standard for homelab containers. Adopting it eliminates the most common "permission denied" issue while maintaining backward compatibility.

**Deliverables**:
- `docker/entrypoint.sh` — the entrypoint script
- Updated `Dockerfile` (repository root) — add `su-exec` install, set `ENTRYPOINT`, remove hardcoded `USER binocular` directive in favor of runtime user switching

**Verification Criteria**:

1. **Given** a container started with `PUID=1001 PGID=1001` env vars, **When** the entrypoint runs, **Then** a user with UID 1001 and GID 1001 exists (verified via `id -nu 1001` yielding `app` and `id -ng 1001` yielding `app`), owns `/app/data` and `/app/modules` (verified via `stat -c '%u:%g'` on both paths and at least one subdirectory each, confirming UID 1001:GID 1001), and uvicorn runs as UID 1001:GID 1001 with username `app`.
2. **Given** a container started with no `PUID`/`PGID` env vars, **When** the entrypoint runs, **Then** the process runs as UID 1000 GID 1000.
3. **Given** a container started with `PUID=0`, **When** the entrypoint runs, **Then** the container exits with exit code 1 and an error message to stderr naming the offending variable (`PUID=0`).
4. **Given** a container started with `PUID=1001 PGID=0`, **When** the entrypoint runs, **Then** the container exits with exit code 1 and an error message to stderr naming the offending variable (`PGID=0`).
5. **Given** a container started with `PUID=abc PGID=def` (non-numeric), **When** the entrypoint runs, **Then** the container starts with UID 1000 GID 1000 and a warning is logged to stderr for each invalid var in the format `[entrypoint] WARNING: PUID=abc is non-numeric, falling back to 1000`.
6. **Given** a container started with `PUID=1500` and no `PGID` env var, **When** the entrypoint runs, **Then** the process runs as UID 1500 GID 1000, with an info log indicating PGID defaulted to 1000.
7. **Given** a container started with `PUID=1001 PGID=abc` (asymmetric non-numeric), **When** the entrypoint runs, **Then** the process runs as UID 1001 GID 1000, with a warning logged to stderr for `PGID` only.
8. **Given** a container started with `PUID=4294967295` (out of range), **When** the entrypoint runs, **Then** the container exits with exit code 4 and an error message to stderr indicating the value exceeds the maximum allowed range.
9. **Given** a container started with `PUID='; rm -rf /'` (shell metacharacters), **When** the entrypoint runs, **Then** the container starts with default UID 1000 and a warning is logged, without executing the injected command.
10. **Given** a container started where UID 1000 already exists in the container image (e.g., assigned to a system user), **When** the entrypoint runs, **Then** the existing user is reused, and an info log indicates the matched username, shell, and home directory.
11. **Given** a container image where neither `su-exec` nor `gosu` is in `PATH`, **When** the container starts, **Then** the container exits with exit code 2 and an error message to stderr indicating neither tool is available.

### Objective 2 — Dockerfile Integration (Priority: P1)

Install `su-exec` and wire the entrypoint into the Docker build.

**Why this priority**: The entrypoint cannot function without `su-exec` installed and the Dockerfile must invoke the entrypoint script before the CMD.

**Rationale**: `su-exec` is a minimal (~25 KB) drop-in privilege-dropping tool preferred over `gosu` for its smaller footprint and lack of Python dependency.

**Deliverables**:
- Dockerfile changes: `apt-get install su-exec` in runtime stage, `COPY docker/entrypoint.sh /entrypoint.sh`, `ENTRYPOINT ["/entrypoint.sh"]`, remove `USER binocular`

**Verification Criteria**:

1. **Given** the Docker image is built, **When** inspecting the image, **Then** `su-exec` is available in `PATH` and `/entrypoint.sh` exists and is executable.
2. **Given** the image is built, **When** checking `docker inspect`, **Then** the `Entrypoint` is `["/entrypoint.sh"]` and the `Cmd` is `["uvicorn", "binocular.main:app", "--host", "0.0.0.0", "--port", "8000"]`.

### Operational Constraints

- Must preserve zero-config startup — no environment variables required for the container to start and function
- Must preserve non-root execution per {SAD:ADR-0008}
- `PUID`/`PGID` must default to `1000:1000` for backward compatibility; each defaults independently
- Entrypoint re-chown on every start is acceptable (few milliseconds); correctness guarantee outweighs startup cost
- Must not introduce new dependencies beyond `su-exec` (gosu as documented fallback if unavailable for a target arch at build time)
- Must use `exec su-exec ...` (or `exec gosu ...`) pattern for correct signal propagation (SIGTERM from `docker stop` must reach uvicorn directly)
- Entrypoint shell script MUST trap SIGTERM/SIGINT before the chown phase to ensure prompt shutdown during long chown operations; partial chown on SIGTERM is accepted
- `chown -R` startup time scales linearly with the number of files in mounted volumes; for volumes exceeding 100k files, operators should pre-set ownership. A `SKIP_CHOWN=true` opt-out is deferred — not implemented in this epic; startup time target is < 2s for typical volumes (<10k files)
- `chown -R` follows symlinks by default; the entrypoint MUST use `--no-dereference` (or equivalent) to prevent ownership changes on symlink targets that may point outside the intended paths
- Capability hardening (e.g., dropping all capabilities, setting `--no-new-privileges`) is a Docker runtime concern outside the entrypoint's scope; the entrypoint only manages UID/GID and signal propagation via su-exec/gosu — it does not clear Linux capabilities
- su-exec and gosu have different codebases (~25 KB C-based vs Ruby-based) and their security properties (capability handling, group handling, signal forwarding) MUST be verified as equivalent for the target architecture during implementation
- Concurrent containers on the same volume race on `chown` (STF-009); no lock mechanism is provided in v1 — operators running multiple replicas should pre-set ownership or use a volume driver that serializes writes

## Integration Points

- **IP-001**: E001 (Application Skeleton & Container) provides the Dockerfile that this epic extends with entrypoint and `su-exec` installation
- **IP-002**: {DOD:DDR-004} documents the deployment decision that this epic implements

## Requirements

### Operational Requirements

- **OR-001**: System MUST read `PUID` and `PGID` environment variables on container start (case-sensitive, uppercase only)
- **OR-002**: System MUST default each variable independently to `1000` when the env var is absent (e.g. `PUID=1500` with no `PGID` → UID 1500, GID 1000)
- **OR-003**: System MUST refuse to run as root (`PUID=0` or `PGID=0`) by checking before any user/group creation, chown, or filesystem writes, and exit with a non-zero code (exit code 1) and clear error message to stderr naming the offending variable and its value
- **OR-004**: System MUST `chown -R` `/app/data` and `/app/modules` to the configured user on every container start; failure on data volumes MUST be a hard error (exit code 3, log the failed path and error to stderr), while failure on read-only rootfs MUST log a warning to stderr and continue startup; entrypoint MUST log chown start and completion (with duration) to stderr at info level
- **OR-005**: System MUST drop privileges via `exec` to `su-exec` (or `gosu` if `su-exec` is absent) before executing the CMD, ensuring signals propagate correctly to uvicorn; entrypoint MUST log which privilege-drop tool (su-exec or gosu) is being used to stderr
- **OR-006**: System MUST log a warning to stderr when a `PUID`/`PGID` value is non-numeric, naming which var was invalid and what fallback value was used, using the format `[entrypoint] WARNING: <var>=<value> is non-numeric, falling back to <default>`; absent env vars produce no warning

- **OR-007**: System MUST emit informational log messages to stderr for key startup phases: env var resolution (each var and its source: explicit value, absent default, or non-numeric fallback), user/group creation outcome (created or reused with matched user info), resolved UID:GID and username, chown target paths, chown start and completion with duration, and a startup completion marker before exec (`[entrypoint] INFO: entrypoint complete, starting application via <tool>`). All informational messages MUST use the format `[entrypoint] INFO: <message>`.
- **OR-008**: System MUST log signal receipt (SIGTERM/SIGINT) and any resulting partial chown state to stderr using the format `[entrypoint] WARNING: Received SIGTERM — chown may be incomplete for <path>`; the log MUST appear before the trap handler exits.
- **OR-009**: System MUST use distinct non-zero exit codes per failure mode: exit code 1 for root refusal (PUID=0 or PGID=0), exit code 2 for missing su-exec/gosu in PATH, exit code 3 for chown failure on data volume, exit code 4 for out-of-range PUID/PGID. All error messages MUST write to stderr using the format `[entrypoint] ERROR: <message>`.

### Runbook Requirements

- **RR-001**: The README and `compose.yaml` MUST document how to set `PUID`/`PGID` in `docker-compose.yml` to match the host UID, noting that environment variable names are case-sensitive and must be uppercase
- **RR-002**: The runbook MUST document the temporary root execution window during entrypoint startup (user/group creation and chown phase) and explain that this is an accepted security tradeoff per the linuxserver.io pattern

## Assumptions & Risks

### Assumptions

- The operator uses Docker or a compatible OCI runtime that supports `ENTRYPOINT` and environment variable injection
- `su-exec` is available for `linux/amd64` and `linux/arm64` in the `python:3.13-slim` apt repositories
- Operators who do not set `PUID`/`PGID` are content with the default `1000:1000` mapping
- The current hardcoded `binocular` system user's UID is not documented or relied upon externally

### Risks

- **`su-exec` not available for arm64** *(likelihood: low, impact: medium)*: Fall back to `gosu` at build time. Both provide the same `exec`-compatible interface.
- **Operator expects `PGID` to create a new group** *(likelihood: low, impact: low)*: If the GID already exists on the system, the entrypoint reuses it — this matches standard linuxserver.io behavior and is well-documented.
- **PUID/PGID out of range** *(likelihood: low, impact: low)*: `useradd`/`groupadd` will reject values outside system limits; error output visible in container logs — acceptable failure mode.
- **Misconfiguration masking from independent defaults** *(likelihood: low, impact: low)*: If `PUID` is set to an invalid value (fallback to 1000 with warning) and `PGID` is absent (silent default to 1000), the container runs as 1000:1000 with only one warning, which may mask the misconfiguration. Operators should verify both PUID and PGID in their compose file.

## Implementation Signals

- `NEW-CONFIG`: `PUID`/`PGID` environment variables added as container configuration knobs
- `BREAKING-CHANGE`: Dockerfile `USER binocular` directive is replaced by entrypoint privilege drop; the fixed `binocular` system user is no longer created at build time

## Success Criteria

### Measurable Outcomes

- **SC-001** [OBJ1]: An operator can set `PUID=1001 PGID=1001` in `docker-compose.yml` and the container runs as UID 1001:GID 1001, confirmed via `id -nu` and `stat -c '%u:%g'` on `/app/data` and `/app/modules` per VC-1
- **SC-002** [OBJ1]: With no `PUID`/`PGID` set, the container starts and functions identically to the baseline: the API responds on port 8000, log output shows the expected default-identity pattern (`UID 1000, GID 1000`), and files in `/app/data` are owned by UID 1000:GID 1000 (zero-config preserved)
- **SC-003** [OBJ2]: The Docker image builds and `docker inspect <image>` shows `"Entrypoint": ["/entrypoint.sh"]` and `"Cmd": ["uvicorn", "binocular.main:app", "--host", "0.0.0.0", "--port", "8000"]`
- **SC-004** [OBJ1]: The project documentation or README contains instructions for setting `PUID`/`PGID` in `docker-compose.yml`, including how to determine the host user's UID:GID
- **SC-005** [RR-002]: The project documentation or README documents the temporary root execution window during entrypoint startup and explains the accepted security tradeoff per the linuxserver.io pattern

## Compliance Check

**Audit Date**: 2026-06-07
**Auditor**: SDD Agent (project-instructions.md compliance check)
**Result**: PASS

| Principle / Policy | Status | Notes |
|---|---|---|
| I. Honest Failure | ✅ | Chown failure → warning, missing su-exec → hard error, root → hard error, invalid input → warning+fallback |
| II. Polite by Default | ✅ N/A | No outbound HTTP scraping involved |
| III. Data Ownership & Self-Containment | ✅ | No external deps added; volumes `/app/data`, `/app/modules` align with SQLite self-containment |
| IV. Least-Privilege | ✅ | PUID=0/PGID=0 refused (OR-003); defaults 1000:1000 preserve non-root; su-exec/gosu drop mandated (OR-005). Note: entrypoint runs as root briefly during user/group creation and chown — accepted per linuxserver.io pattern; runbook documents this window |
| V. Type Safety & Correctness-First | ✅ N/A | Shell entrypoint — no Python/TS source changes |
| VI. Set-and-Forget | ✅ | Zero-config startup mandated; defaults ensure backward compat; re-chown on every start guarantees correctness |
| VII. Agent Output Style | ✅ N/A | Applies to agent communication, not spec artifacts |
| Technology Stack | ✅ | `python:3.13-slim`, uvicorn, volumes, non-root container — all match |
| Source Code Layout | ✅ | Infra files (Dockerfile, entrypoint) exempt from `/src` rule |
| Development Workflow | ✅ N/A | Spec phase |
| Governance | ✅ | Cross-references {SAD:ADR-0008}, {DOD:DDR-004} correct |

**Structural Compliance**:
- Required sections (operational spec_type): Problem Statement, Scope, Operational Objectives, Integration Points, Requirements, Assumptions & Risks, Implementation Signals, Success Criteria — **all present**
- Requirement IDs: OR-001–OR-009, RR-001–RR-002 — correct format
- Success criteria IDs: SC-001–SC-005 — correct format with [OBJ#] tags
- No unauthorized top-level sections
- Frontmatter: feature_branch, created, input, spec_type, spec_maturity, epic_id, epic_sources — all present

**Conclusion**: Spec is compliant. No remediation required.

## Clarifications

### Session 2026-06-07

- Q: Recursive or non-recursive chown? -> A: `chown -R` (linuxserver.io convention)
- Q: Partial env-var behavior (one set, other absent)? -> A: Each defaults independently
- Q: Partial non-numeric fallback granularity? -> A: Individual per-var fallback + warning naming the invalid var
- Q: Group creation when GID exists? -> A: Reuse existing group, do not create duplicate
- Q: `--non-unique` vs skip creation for duplicate UID? -> A: Skip creation, reuse existing user entry
- Q: Signal propagation through su-exec? -> A: `exec su-exec ...` pattern for correct signal handling
- Q: Username/groupname for created user? -> A: `app` (both user and group)
- Q: PUID/PGID bounds validation? -> A: OS-level rejection acceptable; error output visible in logs
- Q: Logging format/sink? -> A: Warnings to stderr with descriptive message including var name and value
- Q: "Missing" vs "non-numeric" conflation? -> A: Separated — absent is silent default, non-numeric is warning+fallback
- Q: su-exec vs gosu at build or runtime? -> A: Build-time decision in Dockerfile

## Stress-Test Findings

### Session 2026-06-07

| ID | Category | Severity | Summary | Resolution |
|----|----------|----------|---------|------------|
| STF-001 | Internal Contradiction | Critical | Edge case says su-exec not in PATH must fail, but gosu fallback is defined | Resolved: edge case accepts either su-exec or gosu; OR-005 updated |
| STF-002 | Internal Contradiction | High | Non-numeric and non-integer handling overlap with contradictory behaviors | Resolved: merged into single rule; non-numeric and non-integer both use fallback |
| STF-003 | Internal Contradiction | Low | VC-1 omits GID verification | Resolved: VC-1 now asserts UID:GID and username |
| STF-004 | Constraint Impossibility | Medium | Entrypoint must run as root to enforce non-root — temporary root window | Resolved: acknowledged in Compliance Check; runbook documents window |
| STF-005 | Constraint Impossibility | Medium | Chown failure on read-only volume defeats feature purpose | Resolved: chown failure on data volumes is hard error; read-only rootfs is warning |
| STF-006 | Constraint Impossibility | Low | Default 1000:1000 may collide with existing system user | Resolved: edge case mandates verifying matched user has valid shell/home |
| STF-007 | Concurrent-Trigger | High | SIGTERM during chown phase is lost before exec | Resolved: entrypoint must trap SIGTERM/SIGINT before chown phase |
| STF-008 | Concurrent-Trigger | Medium | Env var case sensitivity unspecified | Resolved: documented as case-sensitive, uppercase only |
| STF-009 | Concurrent-Trigger | Medium | Concurrent containers on same volume race on chown | Documented limitation; no lock mechanism in v1 |
| STF-010 | Concurrent-Trigger | Low | PGID=0 refusal rationale not justified separately | Resolved: GID 0 grants root-group access on host |
| STF-011 | Boundary/Scale | High | chown -R on large volumes exceeds "few milliseconds" claim | Resolved: removed millisecond claim; documented linear scaling; SKIP_CHOWN opt-out noted |
| STF-012 | Boundary/Scale | Medium | Undocumented 60000 range limit | Resolved: raised to OS max 4294967294 with script-level validation |
| STF-013 | Boundary/Scale | Low | No cross-arch su-exec verification for extreme UIDs | Documented: cross-arch integration test recommended for CI |
| STF-014 | Boundary/Scale | Low | Username `app` not validated in acceptance criteria | Resolved: VC-1 now asserts username `app` via `id -nu` |
