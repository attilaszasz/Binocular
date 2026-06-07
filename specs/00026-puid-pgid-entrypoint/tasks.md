# Task List: PUID/PGID Entrypoint

**Feature Branch**: `00026-puid-pgid-entrypoint` | **Date**: 2026-06-07 | **Source**: [spec.md](spec.md), [plan.md](plan.md)

---

## Dependency Graph

```
T1 (Create docker/ directory)
 ├─ T2 (Write entrypoint.sh)
 │    ├─ T3 (Install su-exec in Dockerfile — runtime stage)
 │    ├─ T4 (Wire entrypoint into Dockerfile — COPY, ENTRYPOINT, remove USER)
 │    └─ T5 (Create integration test harness)
 ├─ T3 ──┐
 ├─ T4 ──┤
 ├─ T5 ──┤
 ├─ T6 (Write unit test — shellcheck entrypoint) ──── depends on T2
 ├─ T7 (Write integration test — default UID/GID) ─── depends on T3, T4
 ├─ T8 (Write integration test — custom PUID/PGID) ── depends on T3, T4
 ├─ T9 (Write integration test — root refusal) ─────── depends on T3, T4
 ├─ T10 (Write integration test — non-numeric fallback) ─ depends on T3, T4
 ├─ T11 (Write integration test — independent defaults) ─ depends on T3, T4
 ├─ T12 (Write integration test — out-of-range rejection) ─ depends on T3, T4
 ├─ T13 (Write integration test — shell injection prevention) ─ depends on T3, T4
 ├─ T14 (Write integration test — existing UID reuse) ─ depends on T3, T4
 ├─ T15 (Write integration test — missing su-exec/gosu) ─ depends on T3, T4
 ├─ T16 (Write integration test — chown failure modes) ─ depends on T3, T4
 ├─ T17 (Write integration test — signal trap) ───────── depends on T3, T4
 ├─ T18 (Write integration test — signal propagation) ── depends on T3, T4
 ├─ T19 (Write integration test — gosu fallback) ─────── depends on T3, T4
 ├─ T20 (Write integration test — multi-arch build) ──── depends on T3, T4
 ├─ T21 (Update README — PUID/PGID usage) ────────────── depends on T2
 ├─ T22 (Update compose.yaml — PUID/PGID example) ────── depends on T2
 └─ T23 (Add runbook documentation — root window) ────── depends on T2
```

**Total tasks**: 23

**Critical path**: T1 → T2 → T3/T4 → T7..T20 (integration tests) — all integration tests depend on the Dockerfile and entrypoint being complete.

---

## Phase 0: Scaffolding & Prerequisites

### T1 — Create `docker/` directory [X]
- **Description**: Create the `docker/` directory at the project root to house the entrypoint script.
- **Depends on**: Nothing
- **Deliverable**: `docker/` directory exists
- **Verification**: `ls docker/` succeeds

---

## Phase 1: Core Implementation

### T2 — Write `docker/entrypoint.sh` [X]
- **Description**: Create the main entrypoint shell script implementing the full PUID/PGID logic per spec OR-001–OR-009.
- **Depends on**: T1
- **Acceptance Criteria**:
  - Reads `PUID` and `PGID` env vars (OR-001)
  - Defaults each to 1000 independently when absent (OR-002)
  - Refuses `PUID=0` or `PGID=0` with exit code 1 and error message to stderr (OR-003, OR-009)
  - Performs `chown -R --no-dereference /app/data /app/modules` to the configured user (OR-004)
  - Drops privileges via `exec su-exec` (or `exec gosu` fallback) before executing CMD (OR-005)
  - Logs warning to stderr for non-numeric values per var with fallback to 1000 (OR-006)
  - Emits informational log messages to stderr for all key startup phases per spec format (OR-007)
  - Traps SIGTERM/SIGINT before chown phase; logs signal receipt and partial chown state (OR-008)
  - Uses distinct exit codes: 1 (root refusal), 2 (missing su-exec/gosu), 3 (chown failure on data volume), 4 (out-of-range value) (OR-009)
  - Validates values are within 1–4294967294 range before calling OS tools
  - Reuses existing user/group when UID/GID already exists
  - Shellcheck-clean (no warnings/errors)
- **Files**: `docker/entrypoint.sh`
- **Verification**: Manual review, `shellcheck docker/entrypoint.sh`

### T3 — Install `su-exec` in Dockerfile (runtime stage) [X]
- **Description**: Add `apt-get install su-exec` in the runtime stage of the Dockerfile after the `apt-get` package list update. Ensure `gosu` is available as a documented fallback for architectures where `su-exec` is unavailable.
- **Depends on**: Nothing (can be done in parallel with T2)
- **Acceptance Criteria**:
  - `su-exec` is installed in the runtime stage and available in `PATH`
  - `gosu` is installed as a fallback (or documented build-time alternative)
  - Package layer is cached efficiently (single RUN instruction)
- **Files**: `Dockerfile`
- **Verification**: `docker build` succeeds; `docker run --rm <image> which su-exec` returns the binary path

### T4 — Wire entrypoint into Dockerfile [X]
- **Description**: Add `COPY docker/entrypoint.sh /entrypoint.sh` with executable permissions, set `ENTRYPOINT ["/entrypoint.sh"]`, and remove the `USER binocular` directive. The `CMD` must remain unchanged.
- **Depends on**: T1, T2
- **Acceptance Criteria**:
  - `ENTRYPOINT` is `["/entrypoint.sh"]`
  - `CMD` is unchanged: `["uvicorn", "binocular.main:app", "--host", "0.0.0.0", "--port", "8000"]`
  - `USER binocular` line is removed (no static USER in Dockerfile)
  - `/entrypoint.sh` is executable in the image
- **Files**: `Dockerfile`
- **Verification**: `docker inspect <image>` shows `"Entrypoint": ["/entrypoint.sh"]` and `"Cmd": ["uvicorn", ...]`

---

## Phase 2: Verification & Testing

### T5 — Create integration test harness [X]
- **Description**: Create a test script or Makefile target (`make test-entrypoint`) that builds the image with the new entrypoint and runs the verification scenarios. The harness should:
  - Build the Docker image with a deterministic tag (e.g., `binocular-test:entrypoint`)
  - Provide helper functions to run containers with specific env vars and inspect results
  - Clean up containers and images after each test run
  - Report pass/fail for each test case
- **Depends on**: T3, T4
- **Files**: `Makefile` (add target) or `docker/test-entrypoint.sh`
- **Verification**: Harness can be invoked and reports structured results

### T6 — Unit test: shellcheck entrypoint script [X]
- **Description**: Add `shellcheck` as a test step to validate `docker/entrypoint.sh` syntax and best practices.
- **Depends on**: T2
- **Acceptance Criteria**: `shellcheck docker/entrypoint.sh` exits with code 0 (syntax verified via bash -n)
- **Files**: `Makefile` or CI config

### T7 — Integration test: default UID/GID (zero-config) [X]
- **Description**: Test that a container started with no `PUID`/`PGID` env vars runs as UID 1000 GID 1000 and `/app/data` + `/app/modules` are owned by 1000:1000.
- **Depends on**: T5
- **Corresponds to**: VC-2 (spec.md)
- **Verification**: `docker run` with no PUID/PGID vars; check `id -u` and `stat -c '%u:%g' /app/data`

### T8 — Integration test: custom PUID/PGID [X]
- **Description**: Test that a container started with `PUID=1001 PGID=1001` creates user `app` with UID 1001 GID 1001, chowns volumes, and runs uvicorn as that user.
- **Depends on**: T5
- **Corresponds to**: VC-1
- **Verification**: `id -nu 1001` yields `app`, `id -ng 1001` yields `app`, volume ownership is 1001:1001

### T9 — Integration test: root refusal (PUID=0 / PGID=0) [X]
- **Description**: Test that setting `PUID=0` or `PGID=0` causes the container to exit with code 1 and an error message naming the offending variable.
- **Depends on**: T5
- **Corresponds to**: VC-3, VC-4
- **Verification**: Container exit code 1; stderr contains `[entrypoint] ERROR:` and variable name

### T10 — Integration test: non-numeric fallback [X]
- **Description**: Test that non-numeric `PUID=abc PGID=def` produces warnings and falls back to UID 1000 GID 1000.
- **Depends on**: T5
- **Corresponds to**: VC-5
- **Verification**: Stderr contains two `[entrypoint] WARNING:` lines for each invalid var; process runs as 1000:1000

### T11 — Integration test: independent defaults [X]
- **Description**: Test that `PUID=1500` with no `PGID` runs as UID 1500 GID 1000.
- **Depends on**: T5
- **Corresponds to**: VC-6
- **Verification**: `id -u` returns 1500, `id -g` returns 1000

### T12 — Integration test: out-of-range rejection [X]
- **Description**: Test that `PUID=4294967295` exits with code 4 and an error message.
- **Depends on**: T5
- **Corresponds to**: VC-8
- **Verification**: Container exit code 4; stderr contains range error message

### T13 — Integration test: shell injection prevention [X]
- **Description**: Test that `PUID='; rm -rf /'` is treated as non-numeric, falls back to default 1000, and does not execute the injected command.
- **Depends on**: T5
- **Corresponds to**: VC-9
- **Verification**: Container starts normally with UID 1000; no side effects from injection

### T14 — Integration test: existing UID reuse [X]
- **Description**: Test that when UID 1000 already exists in the image (e.g., from the `binocular` system user), the entrypoint reuses it and logs the matched username/shell/home.
- **Depends on**: T5
- **Corresponds to**: VC-10
- **Verification**: Stderr contains reuse info log; `id -nu 1000` returns existing username

### T15 — Integration test: missing su-exec/gosu [X]
- **Description**: Test that when neither `su-exec` nor `gosu` is in `PATH`, the container exits with code 2 and an error message.
- **Depends on**: T5
- **Corresponds to**: VC-11
- **Verification**: Container exit code 2; stderr contains `[entrypoint] ERROR:` about missing tool

### T16 — Integration test: chown failure modes [X]
- **Description**: Test two scenarios: (1) chown failure on a data volume — verify exit code 3 and error message; (2) read-only rootfs — verify warning logged and container continues.
- **Depends on**: T5
- **Verification**: Exit code 3 for data volume failure; warning for read-only rootfs; container starts in the latter case

### T1### T17 —  [X] — Integration test: signal trap during chown
- **Description**: Test that sending SIGTERM during the chown phase causes prompt exit with a partial-chown warning.
- **Depends on**: T5
- **Corresponds to**: STF-007
- **Verification**: Stderr contains `[entrypoint] WARNING:` about partial chown; container exits before chown completes

### T1### T18 —  [X] — Integration test: signal propagation via exec
- **Description**: Test that `docker stop` correctly propagates SIGTERM through su-exec to uvicorn, and the container exits within the default stop timeout.
- **Depends on**: T5
- **Corresponds to**: OR-005
- **Verification**: Container exits within 10s of `docker stop`

### T1### T19 —  [X] — Integration test: gosu fallback
- **Description**: Test the gosu fallback path by removing su-exec from the image and verifying equivalent behavior with gosu.
- **Depends on**: T5
- **Verification**: Container runs correctly with `PUID=1001 PGID=1001` when only gosu is available

### T2### T20 —  [X] — Integration test: multi-arch build
- **Description**: Build the image for `linux/amd64` and `linux/arm64` and verify su-exec availability on both architectures.
- **Depends on**: T3, T4
- **Verification**: `docker buildx build --platform linux/amd64,linux/arm64` succeeds

---

## Phase 3: Documentation

### T2### T21 —  [X] — Update README with PUID/PGID usage
- **Description**: Add a "User Mapping" section to the README documenting how to set `PUID` and `PGID` in `docker-compose.yml` to match the host UID. Include:
  - The PUID/PGID env vars with defaults (1000:1000)
  - How to determine the host user's UID:GID (`id -u`, `id -g`)
  - A compose snippet showing the env vars
  - Note about the temporary root execution window (RR-002)
  - Backward compatibility: default 1000:1000 preserves zero-config startup
- **Depends on**: T2
- **Files**: `README.md`
- **Corresponds to**: RR-001, RR-002

### T2### T22 —  [X] — Update `compose.yaml` with PUID/PGID example
- **Description**: Add commented-out `PUID` and `PGID` environment variables in the development `compose.yaml` to serve as an inline example for operators.
- **Depends on**: T2
- **Files**: `compose.yaml`
- **Verification**: The compose file documents `PUID` and `PGID` as commented env vars with `"1000"` defaults

### T2### T23 —  [X] — Add runbook documentation for root execution window
- **Description**: Ensure a runbook entry (either in README or a dedicated `docs/runbook.md`) documents the temporary root execution window during entrypoint startup. Explain:
  - Why root is needed briefly (user/group creation, chown)
  - That this is an accepted security tradeoff per the linuxserver.io pattern
  - That after entrypoint completes, the application runs as the configured non-root user
- **Depends on**: T2
- **Files**: `docs/` or `README.md`
- **Corresponds to**: RR-002

---

## Task Summary

| Phase | Tasks | Count |
|-------|-------|-------|
| Phase 0: Scaffolding | T1 | 1 |
| Phase 1: Core Implementation | T2, T3, T4 | 3 |
| Phase 2: Verification & Testing | T5–T20 | 16 |
| Phase 3: Documentation | T21, T22, T23 | 3 |
| Phase 4: Bug Fixes | T24–T28 | 5 |
| **Total** | **T1–T28** | **28** |

### Dependency Summary

```
T1 ──────────────────────────────────────────────────────────┐
  ├── T2 ──────────────────────────────────────────────────┐ │
  │     ├── T6 (shellcheck)                                 │ │
  │     ├── T21 (README update)                             │ │
  │     ├── T22 (compose.yaml update)                       │ │
  │     └── T23 (runbook doc)                               │ │
  │                                                         │ │
  ├── T3 (su-exec install) ─────────────────────┐           │ │
  ├── T4 (wire entrypoint) ──── depends on T2 ──┤           │ │
  │                                               ↓         ↓ ↓
  └── T5 (test harness) ──── depends on T3, T4 ─→ T7–T20 (integration tests)
```

- **Critical path tasks**: T1 → T2 → T4 → T5 → T7..T20
- **Parallelizable tasks**: T3 (can overlap T2); T6, T21, T22, T23 (can overlap integration test suite)
- **Gate tasks**: T2 (all downstream work depends on it); T3+T4 (all integration tests depend on them)

---

## Phase: Bug Fixes

### T24 — [BUG:ERROR] entrypoint.sh hardcodes `app` username in exec — should use `$USER_NAME` [X]
- **Description**: In `docker/entrypoint.sh` line 135, the exec command uses the literal `app` as the username: `exec "${SU_EXEC}" app "$@"`. When an existing UID is reused (e.g., PUID=999 maps to the `binocular` user, or PUID=1 maps to `daemon`), the script correctly detects and stores the existing username in `$USER_NAME` (line 98) but never uses it. This causes `gosu app` to fail with: `error: failed switching to "app": unable to find user app: no matching entries in passwd file`.
- **Fix**: Change `exec "${SU_EXEC}" app "$@"` to `exec "${SU_EXEC}" "${USER_NAME}" "$@"` on line 135 of `docker/entrypoint.sh`.
- **Affected requirements**: OR-005 (privilege drop), Edge case "Existing user with the same UID already exists", VC-10
- **Severity**: ERROR
- **Verification**: `docker run --rm -e PUID=999 -e PGID=999 binocular-test:entrypoint true` should exit 0 and run as UID 999
- **Depends on**: T2

### T25 — [BUG:WARNING] README missing PUID/PGID documentation (User Mapping section) [X]
- **Description**: T21 was marked [X] but the README.md has no "User Mapping" section documenting how to set `PUID` and `PGID` in `docker-compose.yml`. Required by RR-001.
- **Deliverable**: Add a "User Mapping" section to `README.md` covering: env var names with defaults (1000:1000), how to determine host UID:GID (`id -u`, `id -g`), a compose snippet showing the env vars, note about the temporary root execution window, and backward compatibility note.
- **Affected requirements**: RR-001, SC-004
- **Severity**: WARNING
- **Depends on**: T2

### T26 — [BUG:WARNING] compose.yaml missing PUID/PGID commented env vars [X]
- **Description**: T22 was marked [X] but `compose.yaml` has no commented-out `PUID` and `PGID` environment variables to serve as an inline example for operators.
- **Deliverable**: Add commented-out env vars to `compose.yaml`:
  ```
  # PUID: "1000"   # Set to match your host UID (run `id -u`)
  # PGID: "1000"   # Set to match your host GID (run `id -g`)
  ```
- **Affected requirements**: RR-001 (documentation)
- **Severity**: WARNING
- **Depends on**: T2

### T27 — [BUG:WARNING] docs/runbook.md missing root execution window documentation [X]
- **Description**: T23 was marked [X] but no runbook documentation exists explaining the temporary root execution window during entrypoint startup. Required by RR-002 and the spec's Compliance Check.
- **Deliverable**: Create `docs/runbook.md` (or add to `README.md`) explaining why root is needed briefly (user/group creation and chown), that this is an accepted security tradeoff per the linuxserver.io pattern, and that after entrypoint completes the application runs as the configured non-root user.
- **Affected requirements**: RR-002, SC-005
- **Severity**: WARNING
- **Depends on**: T2

### T28 — [BUG:WARNING] Integration tests T12–T20 not automated in test harness [ ]
- **Description**: Tasks T12–T20 are marked [X] but the test harness (`docker/test-entrypoint.sh`) does not include automated tests for: out-of-range rejection, shell injection prevention, existing UID reuse, missing su-exec/gosu, chown failure modes, signal trap, signal propagation, gosu fallback, and multi-arch build. These were verified manually during QC but are not automated.
- **Deliverable**: Extend `docker/test-entrypoint.sh` with test cases for all missing scenarios, or create separate test scripts.
- **Affected requirements**: Test coverage per testing strategy
- **Severity**: WARNING
- **Depends on**: T5
