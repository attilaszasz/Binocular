# Write Ownership Audit

## Production SQL Entry Points

Paths are relative to `backend/src/binocular/`. Audited every `execute`, `executemany`, `executescript`, `commit`, `rollback` and SQLite connection-opening call.

| Path | Ownership mode / transaction boundary |
|------|---------------------------------------|
| `app.py`, `deps.py` | Bootstrap connection runs migrations and closes before runtime. Shared lifespan connection uses `query_only=ON` and autocommit reads; never owns domain mutations. |
| `db/connection.py` | Connection initialization only: WAL, foreign keys, 5000ms busy timeout; runtime query-only guard. File-path discovery is a read. |
| `db/migrations.py` | Exclusive bootstrap owner: transaction-free pre-upgrade backup, then one submitted script containing BEGIN, all pending SQL, user_version and COMMIT. Drains actual submission outcome; rolls back failure. Never receives the shared runtime connection. |
| `db/unit_of_work.py` | Sole runtime domain commit/rollback authority. Dedicated connection, task-owned BEGIN IMMEDIATE, one commit, rollback before submission/failure, cancellation drainage and close. Participating adapter rejects independent transaction control. |
| `db/repository.py` | Standalone mutation owns a dedicated WriteUnit; bound mutation joins caller without commit. Multi-statement methods use `write_scope`/bound repositories. Read helpers only query the supplied connection. |
| `devices/repository.py`, `extensions/repository.py` | Parameterized standalone or caller-bound mutations; no commit. Module insertion's schedule trigger shares its owner transaction. Dynamic columns use fixed allowlists. |
| `db/activity_repository.py` | Activity insert and pruning share one unit; bound calls never commit. |
| `db/notifications_repository.py` | Channel read/compare/update or insert shares one unit. UPDATE preserves channel IDs/history; effective changes increment config revision; no-op saves retain exact stored JSON. |
| `devices/service.py` | CRUD validation/read-modify-return groups bind repositories to one scope; single-statement deletion uses the standalone adapter. |
| `routes/modules.py` | Upload persistence, status changes and referenced-device deletion checks use dedicated scopes. Validation/loading precede admission; scheduler effects follow commit. Remaining raw SQL calls are SELECTs. |
| `routes/notifications.py` | Masked-secret merge and channel save share one scope; test dispatch performs reads only before network. |
| `services/checks.py`, `services/notifier.py` | Raw runtime SQL is SELECT-only. Check/status/watermark/activity writes use standalone repository units; health read/increment uses one bound unit. Scraping and Apprise dispatch execute outside units. V1 behavior remains; no catalog work/intents activated. |
| `services/scheduler.py` | Raw shared-connection calls are SELECTs. Schedule mutations use dedicated units; interval/config-generation changes are atomic. Firmware checks and job registration occur outside units. |
| `official_modules/canon_endpoint_cache.py` | Mapping/validation/invalidation/heartbeat writes use standalone or bound units. Lease read/acquire/join/takeover is one scope; terminal detach/close is one scope. Network runs between units; bound live coordination is rejected. Existing normalized family/model single-flight key and shielded waiter semantics retained. |
| `services/seeder.py` | Validate/load/hash before admission; one owned unit per module rechecks provenance and inserts/updates its existing identity. Controls, schedules, devices and history are not replaced. Failed persistence restores copied bytes only when the unit did not commit. |
| `services/settings_seeder.py` | Prepare environment settings outside a unit; all configured channels seed in one owned unit through bound repositories. Absent settings leave existing channels untouched. |
| `services/backup.py` | Separate transaction-free maintenance connection performs VACUUM INTO; no runtime commit/rollback and no WriteUnit. Drain VACUUM/close before cancellation propagation or output cleanup; publish completed output by same-filesystem rename. |

## Deterministic Evidence

- As-built dormant repositories (`catalog_repository.py`, `observation_repository.py`, `work_repository.py`, `delivery_repository.py`) participate in caller-owned units or open dedicated standalone scopes; no production V1 queues or dispatch workers are activated. Atomic observation/enqueue and mutation/enqueue APIs require one bound unit. Claim authorization persists exact dispatch execution registration before network; uncertain retry requires matching immutable registration and host-observed stoppage, not merely owner labels. See `data-model.md` as-built contracts and `backend/tests/db/test_catalog_delivery.py`.
- TR-015 sanitization is applied before immutable persistence: origin-only URLs, allowlisted error/status/operation context, typed safe event detail and vetted numeric receipts; opaque values redact or fail closed. Authority validation retains access to the original captured URL before origin-only projection. Security fixtures inspect storage/logs for credential leakage; see `backend/tests/db/test_catalog_security.py`.
- T028 browser regression exposed lost V1 missing-product diagnostics after error sanitization. `extensions/runner.py` now retains only the exact allowlisted labels `product_not_found`, `firmware_not_available`, `firmware_index_not_found` from a plain ValueError's plain-string first argument; no exception stringification or provider message survives. Stateless search propagates only those labels. Unknown labels retain the generic failure; runner regressions include credential-bearing suffixes and prefix lookalikes. Browser assertions are unchanged.

- `backend/tests/db/test_auxiliary_write_ownership.py`: real-file cache/module-seed/settings-seed/config partial failures; SQL-traced contender BEGIN barrier; independent activity commit; reopen proves failed-owner state absent. Terminal cache cleanup rolls back together. Seed success preserves identities, controls, devices and history. Backup success/failure cannot commit another owner's pending writes; cancellation pauses the real SQLite worker and verifies drainage, closure and temporary-output cleanup.
- `backend/tests/test_canon_endpoint_cache.py`: strict cache freshness/invalidation/fencing plus normalized same-variant coalescing and independent writer admission during live work.
- `backend/tests/test_seeder.py`: provenance/upgrade preservation also runs against a query-only input.
- `backend/tests/test_migrations.py`: reproduced the initial full-suite result, **607 passed / 1 failed**. `setup_logging(cache_logger_on_first_use=True)` binds processors on the module logger; later `capture_logs()` only changes global processors and therefore misses already-bound events. The cancellation test now observes actual structured events with an explicitly bound capture processor, independent of suite configuration. Both success/cancellation and failure event assertions remain, alongside original durable-outcome/reopen assertions.

## Validation

- T028 aggregate implementation gates and post-fix evidence: [validation-results.md](validation-results.md). The figures below preserve the earlier T008 ownership audit execution, not final feature totals.

- Working directory: `backend/`.
- `uv run ruff check .`: exit 0, all checks passed.
- `uv run mypy --strict .`: exit 0, no issues in 132 source files.
- `uv run pytest -q` twice on the final code: exit 0 each; **619 passed in 33.62s**, then **619 passed in 33.44s**. Includes existing V1 and official-module fixture regressions.
- `git diff --check` at repository root: exit 0.
- No task states, completion/QC markers, workers or production catalog queues changed by T008.
