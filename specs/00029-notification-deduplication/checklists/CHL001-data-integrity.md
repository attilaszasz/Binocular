# Data Integrity Checklist: Notification Deduplication
**Created**: 2026-06-07 | **Feature**: [spec.md](../spec.md) | **Evaluated**: 2026-06-07

## Database Migration Safety

- [x] CHK001 Is the migration number 009 confirmed to be the next available number, with no existing migration file at `backend/src/binocular/db/migrations/009_*.sql` that would be overwritten or cause a numbering collision? [Migration Safety, Data Model §Schema Change]
  > **RESOLVED**: Existing migrations are 001–008 (verified via `ls backend/src/binocular/db/migrations/`). 009 is the next available. Data-model.md and plan.md both designate 009.

- [x] CHK002 Does the migration use `ALTER TABLE devices ADD COLUMN last_notified_version TEXT DEFAULT NULL` — a non-blocking operation in SQLite that does not require table rebuild or downtime, and is the column appended at the end of the table as SQLite requires? [Migration Safety, Data Model §Migration SQL]
  > **RESOLVED**: Data-model.md §Migration SQL shows exactly this statement. Spec clarifies "non-blocking, no downtime needed."

- [x] CHK003 Is the column type `TEXT` consistent with existing version columns (`current_version`, `latest_version`) so that the same `compare_versions()` function operates on identically-typed inputs without implicit type coercion? [Consistency, Data Model §Post-Migration Column Constraints]
  > **RESOLVED**: Data-model.md §Post-Migration: "Free-text firmware version string (same domain as current_version / latest_version)". All three columns are TEXT.

- [x] CHK004 Does the migration set `DEFAULT NULL` so that all existing devices automatically receive NULL `last_notified_version`, satisying FR-001 ("initially NULL for existing devices") without requiring a separate backfill step? [Completeness, Spec §FR-001]
  > **RESOLVED**: Migration SQL: `DEFAULT NULL`. All existing rows inherit NULL automatically. No separate backfill needed. ✓ FR-001.

- [x] CHK005 Is the migration file committed alongside (or before) any code that reads `last_notified_version`, so that no code path executes a SELECT referencing the column against a database that has not yet had the migration applied? [Migration Safety, Plan §Project Structure]
  > **RESOLVED**: Plan.md §Project Structure places migration `009_add_last_notified_version.sql` in the same feature branch as the code changes. Commit ordering enforced at implementation time; the numbered migration runs before application startup via `MigrationRunner.apply_pending()`.

- [x] CHK006 Are all existing SELECT queries that produce `DeviceRecord` instances (`get_device`, `require_device`, `list_active_devices`) updated to include `d.last_notified_version` in their explicit column lists, preventing a column-exists-but-not-fetched scenario that could silently produce NULL on existing devices with a non-NULL value? [Completeness, Data Model §Brownfield Integration Notes]
  > **RESOLVED**: Data-model.md §Brownfield Integration Notes: "get_device, require_device, list_active_devices all use explicit column lists — no SELECT *. Each must add d.last_notified_version."

- [x] CHK007 Is `_record_from_row()` updated to read the new column via `_optional_text(row["last_notified_version"])`, matching the pattern used for other nullable text fields, and does the row key `"last_notified_version"` match the column alias in the SQL SELECT? [Consistency, Data Model §Dataclass Change]
  > **RESOLVED**: Data-model.md §Brownfield Integration Notes: "_record_from_row() must include last_notified_version=_optional_text(row['last_notified_version'])". Column alias matches field name.

- [x] CHK008 Does the migration runner guarantee that migration 009 is applied exactly once on startup, with idempotency protection against re-execution (e.g., migration tracking table check), so that `ALTER TABLE ADD COLUMN` is never attempted on a database that already has the column? [Migration Safety, Research §None — implementation concern]
  > **RESOLVED**: Verified in `backend/src/binocular/db/migrations.py`. `MigrationRunner.apply_pending()` reads `schema_version` table, computes `pending = [m for m in migrations if m.version not in applied_versions]`. Already-applied migrations are skipped. Each migration runs in `BEGIN IMMEDIATE` with `INSERT INTO schema_version` committed atomically.

## State Consistency

- [x] CHK009 Is `last_notified_version` updated to `latest_version` in the same `BEGIN IMMEDIATE` / `COMMIT` transaction as the check result persistence, so that a mid-transaction crash rolls back both the check result and the `last_notified_version` update atomically? [Atomicity, Data Model §Locking Strategy]
  > **RESOLVED**: Data-model.md §Locking Strategy shows `BEGIN IMMEDIATE` → persist check result → UPDATE last_notified_version → `COMMIT` as a single transaction. §Write Semantics: "The UPDATE to last_notified_version occurs in the same BEGIN IMMEDIATE transaction as the check result persistence."

- [x] CHK010 When all configured notification channels fail (all return `False`), does the code path leave `last_notified_version` unchanged and avoid calling `record_notification_dispatched()`, ensuring FR-005 ("leave `last_notified_version` unchanged when all channels fail") is satisfied? [Correctness, Spec §FR-005]
  > **RESOLVED**: Data-model.md §Write Semantics: "all channels fail or zero channels configured → Leave last_notified_version unchanged (FR-005)". Plan.md §Error Handling: "All channels fail → Leave last_notified_version unchanged; log warning."

- [x] CHK011 When at least one channel succeeds but others fail (partial success), does the code path update `last_notified_version` via `record_notification_dispatched()` — satisfying FR-004 ("at least one channel returns a transport-level success") — without requiring all channels to succeed? [Correctness, Spec §FR-004, Clarifications Q6]
  > **RESOLVED**: Data-model.md §Write Semantics: "at least one channel returns transport success → UPDATE last_notified_version = latest_version (FR-004)". Plan.md §Error Handling: "Partial channel failure → Update last_notified_version."

- [x] CHK012 When the dedup gate suppresses a notification (`should_notify = False`), does the code path skip both notification dispatch AND the `last_notified_version` update, leaving the column at its existing value (which correctly reflects the last-notified version, not the suppressed one)? [Correctness, Data Model §Write Semantics for last_notified_version]
  > **RESOLVED**: Data-model.md §Write Semantics: "Dedup gate returns should_notify = False → Leave last_notified_version unchanged". The dedup gate only permits dispatch when `is_newer` is True.

- [x] CHK013 When zero notification channels are configured, does the code path skip dispatch entirely, leave `last_notified_version` unchanged, and still persist the check result — consistent with the spec edge case "no delivery capability"? [Completeness, Spec §Edge Cases & Boundaries]
  > **RESOLVED**: Spec.md Edge Cases: "check records the detection result but skips dispatch entirely, and last_notified_version remains unchanged". Plan.md §Error Handling matches.

- [x] CHK014 After `last_notified_version` is first set to a concrete version string, does every code path prevent it from being reset to NULL, ensuring the invariant "never reset to NULL after first set" holds? [Invariant Protection, Data Model §Validation Rules]
  > **RESOLVED**: Data-model.md §Validation Rules: "last_notified_version is never reset to NULL by the application after first set". The only write paths are via `record_notification_dispatched()` which writes a concrete version string, never NULL.

- [x] CHK015 When a device is archived (`is_archived = 1`), is `last_notified_version` preserved in the row (not cleared) so that if the device is ever unarchived its dedup state is intact? [Data Preservation, Data Model §Entity Table]
  > **RESOLVED**: Data-model.md §Repository Changes: `record_notification_dispatched` includes `AND is_archived = 0` — prevents writes to archived devices but does not clear the column. Archival is a separate mutation on `is_archived` only; the column value is preserved.

- [x] CHK016 Is `updated_at` on the `devices` row updated to `CURRENT_TIMESTAMP` whenever `last_notified_version` is written via `record_notification_dispatched()`, maintaining consistency with the timestamp pattern used for other device mutations? [Consistency, Data Model §Repository Changes]
  > **RESOLVED**: Data-model.md §Repository Changes: `UPDATE devices SET last_notified_version = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND is_archived = 0`. Matches existing timestamp pattern.

- [x] CHK017 When `compare_versions()` raises an exception due to an invalid or unparseable version string in `last_notified_version`, does the code path treat the value as NULL (never notified) and log the error, rather than crashing the check or silently suppressing a valid notification? [Error Handling, Plan §Error Handling Strategy]
  > **RESOLVED**: Plan.md §Error Handling: "Invalid last_notified_version string → compare_versions raises VersionComparisonError → Treat as NULL (never notified), log error."

- [x] CHK018 When `latest_version` is NULL (no version detected by the module), does the dedup gate short-circuit before calling `compare_versions()`, avoiding a comparison between NULL and a concrete `last_notified_version`? [Robustness, Plan §Error Handling Strategy]
  > **RESOLVED**: The dedup gate is only reached when a version IS detected (the existing check flow handles failed/null detections before reaching the gate). Plan.md §Error Handling covers unparseable versions via "Record as check_failed; do not update last_notified_version". If latest_version is NULL, the check would be recorded as check_failed upstream of the dedup gate per existing logic.

- [x] CHK019 If a device's module is removed or deactivated after `last_notified_version` has been set, does the stored value remain valid for future checks if the module is reactivated, or does it become a stale reference that must be invalidated? [Data Lifecycle, Data Model §Entity Table]
  > **RESOLVED**: `last_notified_version` is a plain TEXT column (no FK to modules). If the module is removed/deactivated, checks for that device will fail upstream (module not found) before reaching the dedup gate. If a different module is later assigned and produces an incompatible version format, CHK017's error handling covers the fallback: `compare_versions()` exception → treat as NULL → notify permitted. No explicit invalidation needed.

## SQLite Locking & Concurrency

- [x] CHK020 Does the dedup gate implementation wrap the read of `last_notified_version`, the `compare_versions()` evaluation, and the potential write in a `BEGIN IMMEDIATE` transaction, ensuring that no concurrent check for the same device reads a stale `last_notified_version` while another check is mid-update? [Concurrency Control, Data Model §Locking Strategy]
  > **RESOLVED**: Data-model.md §Locking Strategy shows full pseudocode with `BEGIN IMMEDIATE` wrapping SELECT, dedup evaluation, check result persistence, and `last_notified_version` UPDATE. Plan.md HINT-002 reinforces.

- [x] CHK021 Does `BEGIN IMMEDIATE` acquire a reserved lock immediately (rather than `BEGIN DEFERRED` which only acquires on first write), preventing the scenario where two concurrent readers both see the old `last_notified_version`, both pass the dedup gate, and both dispatch duplicate notifications? [Concurrency Control, Data Model §Locking Strategy, Plan AD-001]
  > **RESOLVED**: Data-model.md §Locking Strategy: "BEGIN IMMEDIATE acquires a reserved lock immediately, serializing concurrent writers." Plan.md AD-001 rationale documents the choice over deferred locking.

- [x] CHK022 Is the transaction scope bounded to exactly the per-device check operation (not held open across multiple device checks), so that a long-running module scrape for device A does not block the dedup gate for device B? [Lock Scope, Plan AD-001]
  > **RESOLVED**: The `BEGIN IMMEDIATE` → `COMMIT` window wraps `run_device_check()` which operates on a single device. Plan.md HINT-002: "wrap the dedup read+gate". Each device check opens and closes its own transaction. Spec and plan confirm single-user bounded concurrency.

- [ ] CHK023 If `BEGIN IMMEDIATE` fails due to a database lock held by another connection (busy), does the implementation handle `sqlite3.OperationalError` with a retry or timeout rather than silently proceeding without the lock? [Error Handling, Plan §Error Handling Strategy]
  > **UNRESOLVED**: Neither plan.md §Error Handling Strategy nor data-model.md address `BEGIN IMMEDIATE` failure due to database busy/lock contention. The migration runner is protected (it has its own `BEGIN IMMEDIATE` with rollback), but the CheckService dedup gate's transaction error handling is not specified. The existing `ConnectionManager` sets `busy_timeout_ms` (from settings), which gives some protection via SQLite's built-in busy timeout, but explicit retry logic is not documented. Recommend adding to plan.md error handling table: "BEGIN IMMEDIATE busy → retry with exponential backoff or fail the check with `check_failed`."

- [x] CHK024 Does the transaction use `COMMIT` on success and `ROLLBACK` on any exception (including notification dispatch failure), preserving atomicity so that a partially-written check result is never left in the database? [Atomicity, Data Model §Locking Strategy]
  > **RESOLVED**: Plan.md HINT-002 explicitly references `ROLLBACK`/`COMMIT` block. Data-model.md §Locking Strategy shows COMMIT. The migration runner (`migrations.py`) demonstrates the established pattern: `BEGIN IMMEDIATE`, execute, `COMMIT` on success, `ROLLBACK` on exception.

- [x] CHK025 Given that SQLite uses database-level locking (not row-level), does the implementation acknowledge that `BEGIN IMMEDIATE` serializes all concurrent writers — not just per-device — and is this acceptable given the single-user, single-instance deployment model with bounded check concurrency? [Design Awareness, Plan AD-001, Plan §Technical Context]
  > **RESOLVED**: Data-model.md §Locking Strategy explicitly: "SQLite uses database-level locking; BEGIN IMMEDIATE acquires a reserved lock immediately, serializing concurrent writers." Plan.md §Technical Context: "Single-user, single-instance; concurrent checks bounded by existing semaphore." The trade-off is acknowledged and deemed acceptable.

- [x] CHK026 Are WAL mode implications considered — in WAL mode (SQLite default in many deployments), can a writer (`BEGIN IMMEDIATE`) proceed concurrently with readers, and does a reader see the most recent committed `last_notified_version` or a stale snapshot from before the write transaction began? [Transaction Isolation, Data Model §Locking Strategy]
  > **RESOLVED**: Verified `backend/src/binocular/db/connection.py` sets `PRAGMA journal_mode = WAL`. In WAL mode: (1) `BEGIN IMMEDIATE` (write tx) sees the latest committed state, so the dedup gate reads the freshest `last_notified_version`. (2) Concurrent readers see a consistent snapshot from their read start — they may briefly see a stale value, but the write transaction that updated `last_notified_version` has already committed, serializing correctly. (3) Writers are still serialized via the reserved lock. WAL mode is compatible with and favorable for this locking strategy.

## NULL Handling

- [x] CHK027 Does the dedup gate treat NULL `last_notified_version` as "never notified," passing the gate (`should_notify = True`) for the first newer-than-current detection without calling `compare_versions(NULL, latest_version)` — satisfying FR-003? [Correctness, Spec §FR-003, Data Model §Dedup Gate Logic]
  > **RESOLVED**: Data-model.md §Dedup Gate Logic: `if last_notified_version is None: should_notify = True` — no compare_versions() call.

- [x] CHK028 Is the NULL check implemented before any `compare_versions()` call so that NULL never reaches the comparison function, which may not have defined NULL-handling behavior and could raise an unhandled exception? [Robustness, Plan §Error Handling Strategy]
  > **RESOLVED**: Data-model.md §Dedup Gate Logic pseudocode shows the `is None` guard before the `compare_versions()` call. Plan.md §Error Handling documents fallback: if compare_versions raises → treat as NULL.

- [x] CHK029 In the API response for a device with NULL `last_notified_version`, is the field serialized as JSON `null` (not the string `"null"`, not omitted, not an empty string), providing unambiguous signal to the UI that no notification has ever been sent? [API Fidelity, Spec §Clarifications Q4]
  > **RESOLVED**: `DeviceRecord.last_notified_version` is `str | None`. FastAPI serializes Python `None` → JSON `null` by default. Data-model.md §Brownfield Integration Notes: "DeviceRecord.last_notified_version flows through existing API response serialization."

- [ ] CHK030 In the UI device detail view, is NULL `last_notified_version` rendered as a meaningful indicator (e.g., "Never notified" or "—") rather than a blank space or the literal word "null"? [UX Fidelity, Spec §Clarifications Q4]
  > **UNRESOLVED**: Spec.md Clarifications Q4 states `last_notified_version` should be "visible in the UI on the device detail view" but does not prescribe a specific rendering string for NULL. The UI layer (outside this backend feature scope) must decide whether to render "Never notified", "—", or an equivalent. Recommend adding a UI acceptance criterion or deferring to a separate UI task.

- [x] CHK031 Does the migration produce NULL (not the string `'NULL'`, not an empty string `''`, not a zero-length blob) for all pre-existing device rows, ensuring correct dedup gate behavior on first post-deployment checks? [Migration Correctness, Data Model §Migration SQL]
  > **RESOLVED**: Migration SQL uses SQLite `DEFAULT NULL` keyword — stores SQL NULL, not the string `'NULL'`. aiosqlite returns SQL NULL as Python `None`. Dedup gate checks `is None` correctly.

- [x] CHK032 Does `_optional_text()` in the repository layer correctly distinguish between a database NULL (returns Python `None`) and an empty string (returns `""`), since both are valid SQLite TEXT values but have different dedup-gate semantics? [Type Safety, Data Model §Dataclass Change]
  > **RESOLVED**: Verified in `backend/src/binocular/repositories/inventory.py` line 237: `return value if isinstance(value, str) else None`. Database NULL → aiosqlite returns Python `None` → `_optional_text(None)` returns `None`. Empty string `""` → `_optional_text("")` returns `""`. The two cases are correctly distinguished.

- [ ] CHK033 If a future code path writes an empty string `""` to `last_notified_version` (instead of NULL), does the dedup gate handle it correctly — should `""` be treated as a concrete (invalid) version that suppresses all notifications, or should it be treated as equivalent to NULL? [Edge Case Completeness, Spec §FR-003]
  > **UNRESOLVED**: The dedup gate's NULL check (`if last_notified_version is None`) does not catch empty strings. `""` would be passed to `compare_versions("", latest_version)`, likely raising `VersionComparisonError`. CHK017's error handling would then treat it as NULL and log the error — so the system self-corrects, but with avoidable log noise. No code path in the current design writes empty strings, but a guard (`if not last_notified_version`) or a validation constraint on `record_notification_dispatched()` would make the invariant explicit. Recommend documenting or rejecting empty strings at the repository boundary.

## Data Integrity Rules

- [x] CHK034 Does the dedup gate use the exact same `compare_versions()` function imported from `version_compare.py` as the update-available check, with no separate comparison implementation or wrapper that could introduce semantic divergence — satisfying the high-impact risk mitigation? [Correctness, Spec §FR-002, Plan §Risk Mitigation]
  > **RESOLVED**: Data-model.md §Validation Rules: "Single import: from binocular.services.version_compare import compare_versions". Spec.md FR-002 and plan.md §Risk Mitigation both require the exact same function.

- [x] CHK035 Is the dedup decision logged at INFO level via structlog with all four required fields (`device_id`, `latest_version`, `last_notified_version`, and `decision` being "suppressed" or "dispatched"), satisfying FR-009's auditability requirement? [Observability, Spec §FR-009]
  > **RESOLVED**: Data-model.md §Validation Rules: `structlog.info("notification_dedup_decision", device_id=..., latest_version=..., last_notified_version=..., decision="suppressed"|"dispatched")`. All four fields present.

- [x] CHK036 When the dedup gate suppresses a notification, is the check result still persisted as `up_to_date` (not a new status like "suppressed"), consistent with the Clarifications Q7 ruling that the device is current relative to the known latest version? [Consistency, Spec §Clarifications Q7]
  > **RESOLVED**: Data-model.md §Validation Rules: "Current check result status shown as up_to_date when dedup suppresses (no distinct 'suppressed' status)". Spec.md Clarifications Q7 confirms.

- [x] CHK037 Is `last_notified_version` in the repository's `record_notification_dispatched()` parameterized with `?` placeholders (not f-strings or string concatenation), preventing SQL injection via version strings that may contain unexpected characters? [Security, Data Model §Repository Changes]
  > **RESOLVED**: Data-model.md §Repository Changes shows `?` placeholders in the UPDATE SQL. Plan.md §Technical Context: "raw parameterized SQL". The existing repository pattern uses parameterized queries exclusively.

- [x] CHK038 Does the `record_notification_dispatched()` method include `AND is_archived = 0` in its WHERE clause, preventing updates to archived devices that should not be receiving dispatch state mutations? [Correctness, Data Model §Repository Changes]
  > **RESOLVED**: Data-model.md §Repository Changes SQL: `WHERE id = ? AND is_archived = 0`. Explicit guard against archived device mutations.

- [x] CHK039 Is the `DeviceRecord` dataclass marked `frozen=True` — meaning a new instance must be created when `last_notified_version` changes, rather than mutating an existing record, preserving immutability guarantees across the codebase? [Type Safety, Data Model §Dataclass Change, Plan HINT-004]
  > **RESOLVED**: Data-model.md §Dataclass Change: `@dataclass(frozen=True)`. Plan.md HINT-004: "DeviceRecord is frozen — create a new DeviceRecord with last_notified_version populated; do not mutate existing instances."

- [x] CHK040 Does the dedup gate's `compare_versions(last_notified_version, latest_version)` use `is_newer` (strictly newer) rather than `is_newer_or_equal`, ensuring that re-detection of the already-notified version is correctly suppressed rather than incorrectly re-notified? [Correctness, Data Model §Dedup Gate Logic]
  > **RESOLVED**: Data-model.md §Dedup Gate Logic: `should_notify = comparison.is_newer  # strictly newer required`. The result table confirms equal versions → Suppress.

- [x] CHK041 Are the three state transitions for `last_notified_version` (NULL → version on first success, unchanged on suppression/failure, vX → vY on newer version detection) the only write paths, with no other code path (e.g., device update, module change, bulk operation) silently modifying the column? [Invariant Completeness, Data Model §State Transition Diagram]
  > **RESOLVED**: Data-model.md §State Transition Diagram documents exactly three transitions. The only write to the column is via `record_notification_dispatched()` in the repository. No other mutation (device update, archival, module change) touches this column per the current design.

- [x] CHK042 When `current_version` is changed by the user (e.g., manual update after a firmware upgrade), is `last_notified_version` left untouched per the Clarifications Q5 ruling, relying on the dedup gate logic to naturally handle the new state rather than resetting the value? [Correctness, Spec §Clarifications Q5]
  > **RESOLVED**: Spec.md Clarifications Q5: "Leave untouched; current logic correctly handles this". Data-model.md state transitions for `last_notified_version` are independent of `current_version` mutations.

(End of file - total 164 lines)
