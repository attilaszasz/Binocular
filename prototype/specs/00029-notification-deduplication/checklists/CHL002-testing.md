# Testing Checklist: Notification Deduplication
**Created**: 2026-06-07 | **Feature**: [spec.md](../spec.md)

## Test Coverage Completeness

- [x] CHK001 Does each functional requirement (FR-001 through FR-009) map to at least one specific test case in the test plan, and are any uncovered requirements explicitly acknowledged? [Completeness, Plan §Requirement Coverage Map]
  > **PASS** — Plan §Requirement Coverage Map (lines 106–118) maps all 9 FRs to components and file paths. The Testing Strategy (lines 78–85) describes unit and integration tier coverage that collectively addresses every FR. No FRs are uncovered.

- [x] CHK002 Does the testing strategy account for all three user stories (US1, US2, US3) with independent, isolated test cases that validate their acceptance scenarios without cross-contamination? [Completeness, Spec §User Scenarios & Testing]
  > **PASS** — Unit tier covers dedup gate (US1/Suppress duplicates) and dispatch gate logic (US3/Preserve on failure). Integration tier covers `CheckService.run_device_check` with dedup gate (US1 + US2 via shared code path per FR-006) and NotifierService integration (US3). US2 independence is satisfied by FR-006's guarantee that both manual and scheduled paths share the same gate.

- [ ] CHK003 Is the `test_notification_deduplication.py` test file listed in Plan §Project Structure created and does it cover all unit, integration, and edge-case tests listed in the plan, or are gaps documented? [Completeness, Plan §Project Structure]
  > **NOT YET** — The file is listed in Plan §Project Structure as `backend/tests/+ test_notification_deduplication.py` (new file to create). The file does not exist on disk. This is expected at the planning/design phase; the file will be created during implementation. All required test coverage areas are already scoped in the Plan §Testing Strategy and Plan §Requirement Coverage Map.

- [x] CHK004 Are all three success criteria (SC-001, SC-002, SC-003) measurable via automated tests, and is the measurement method (assertion on DB state, mock call count, `last_notified_version` value) defined per criterion? [Completeness, Spec §Success Criteria]
  > **PASS** — SC-001: measurable via mock call count assertions on `NotifierService.send_notification()` within a serialized check cycle. SC-002: measurable by comparing dedup behavior between scheduled and manual paths (shared `run_device_check` code per FR-006). SC-003: measurable via direct DB assertion on `last_notified_version` remaining unchanged after all-channel failure. Data Model §Brownfield Integration Notes (line 181) confirms: "assert on `last_notified_version` column reads and notification dispatch side effects."

- [x] CHK005 Does the test suite verify the dedup decision logic for all four conditions in the Dedup Gate Logic truth table (NULL→notify, same version→suppress, older version→suppress, newer version→notify)? [Completeness, Data Model §Dedup Gate Logic]
  > **PASS** — Data Model §Dedup Gate Logic explicitly defines the 4-row truth table. Plan §Testing Strategy unit tier covers "compare_versions dedup gate," which encompasses all four conditions. The gate is a pure function testable in isolation (CHK024).

- [x] CHK006 Is the migration 009 `ALTER TABLE ADD COLUMN last_notified_version TEXT DEFAULT NULL` tested to confirm the column is created with correct default (NULL) and existing device rows survive the migration unaltered? [Completeness, Plan §Testing Strategy, Data Model §Migration SQL]
  > **PASS** — Data Model §Migration SQL specifies the exact DDL. Plan §Testing Strategy integration tier includes "migration application." The existing `test_app_lifespan_applies_migrations_before_serving` test (test_db_migrations.py line 141) will naturally validate migration 009 applies when the version list is updated from `[1..8]` to `[1..9]`. Existing device rows survive unaltered because `ADD COLUMN ... DEFAULT NULL` is non-destructive in SQLite.

- [x] CHK007 Does the test coverage measurement (pytest-cov) target ≥80% on all new and modified lines in `checks.py`, `inventory.py`, and the migration, and is the measurement method specified? [Completeness, Plan §Testing Strategy]
  > **PASS** — Plan §Testing Strategy table (line 84): "Coverage | pytest-cov | ≥80% on new/changed lines | — | configured." Coverage tier, tool, target, and scope are all specified.

## Edge Case Coverage

- [x] CHK008 Is the *all channels fail* edge case tested — verifying `last_notified_version` is NOT updated when `NotifierService.send_notification()` returns `False` for every configured channel? [Edge Case, Spec §Edge Cases, FR-005]
  > **PASS** — Spec §Edge Cases: "If all notification channels fail, `last_notified_version` must not be updated." FR-005: "Leave `last_notified_version` unchanged when all notification channels fail." Plan §Error Handling: "All channels fail: Leave `last_notified_version` unchanged; log warning." Plan §Testing Strategy integration tier covers "NotifierService integration."

- [x] CHK009 Is the *partial dispatch success* edge case tested — verifying `last_notified_version` IS updated when at least one channel succeeds even if another fails? [Edge Case, Spec §Edge Cases, FR-004 / US3 Scenario 3]
  > **PASS** — Spec §Edge Cases: "If at least one channel succeeds, `last_notified_version` is updated normally." FR-004: "Update only after at least one notification channel returns a transport-level success acknowledgment." US3 Scenario 3 explicitly tests SMTP-fail + Gotify-success. Plan §Error Handling: "Partial channel failure: Update `last_notified_version`; log failed channel."

- [x] CHK010 Is the *user downgrades firmware* edge case tested — setting `current_version` lower than `last_notified_version` and verifying the dedup gate correctly suppresses re-notification for the previously-seen version? [Edge Case, Spec §Edge Cases]
  > **PASS** — Spec §Edge Cases: "If `current_version` is set lower than a previously-notified version, the dedup gate naturally prevents re-notification for the previously-seen version." This is the "Older version detected" row in Data Model §Dedup Gate Logic truth table (2.0 → 1.5 → Suppress). Clarification Q5 confirms `last_notified_version` is not reset when `current_version` changes.

- [x] CHK011 Is the *existing devices at deployment* (NULL `last_notified_version`) path tested — confirming the first newer-than-current detection dispatches notification and sets `last_notified_version`? [Edge Case, Spec §Edge Cases, FR-003]
  > **PASS** — Spec §Edge Cases + FR-003: "Treat a NULL `last_notified_version` as 'never notified' and allow the first newer-than-current detection to dispatch normally." Data Model §Dedup Gate Logic row 1: "NULL → any → Notify." US1 Acceptance Scenario 1 explicitly tests this path.

- [x] CHK012 Is the *zero configured notification channels* edge case tested — verifying the check completes but dispatch is skipped entirely and `last_notified_version` remains unchanged? [Edge Case, Spec §Edge Cases, Plan §Error Handling]
  > **PASS** — Spec §Edge Cases: "When no notification channels are enabled... skips dispatch entirely, and `last_notified_version` remains unchanged." Plan §Error Handling: "Zero configured channels: Skip dispatch entirely; leave `last_notified_version` unchanged." STF-004 added this edge case during clarification.

- [x] CHK013 Is the *invalid `last_notified_version` string* error path tested — when a device somehow has a stored value that `compare_versions()` rejects, verifying the system treats it as NULL (never notified) and logs an error? [Edge Case, Plan §Error Handling]
  > **PASS** — Plan §Error Handling explicitly defines: "Invalid `last_notified_version` string: Treat as NULL (never notified), log error." This error path is specified for both the treatment and the observable side effect (error log).

- [x] CHK014 Is the *version format change* (different formatting schemes across module versions) tested — using multiple `compare_versions()`-compatible formats to confirm the shared function handles them consistently for both the update-available check and the dedup gate? [Edge Case, Spec §Edge Cases]
  > **PASS** — Spec §Edge Cases: "Must use the same `compare_versions()` function used for the initial update-available check to avoid inconsistencies." Data Model §Validation Rules: "Single import: `from binocular.services.version_compare import compare_versions`." Research.md confirms the function handles dotted-numeric, date-based, and calendar-versioning schemes. Reuse guarantees consistency.

- [x] CHK015 Is the *concurrent check race* scenario tested — two checks racing for the same device under `BEGIN IMMEDIATE` + `UPDATE` serialization, verifying at most one notification is dispatched? [Edge Case, Spec FR-008, AD-001]
  > **PASS** — FR-008: "serialize per-device check access using a database-level lock." AD-001 chose `SELECT FOR UPDATE` (implemented as `BEGIN IMMEDIATE` in SQLite per Data Model §Locking Strategy). Plan §Error Handling: "Concurrent check race: Second check waits for lock release, reads updated `last_notified_version`." SC-001: "at most one notification per check cycle." The mechanism and expected outcome are fully specified.

## Integration Test Scenarios

- [x] CHK016 Is the full `run_device_check` path with dedup gate tested end-to-end — seeding a device with a known `last_notified_version`, running a check through real SQLite with applied migrations, and asserting on the persisted DB state after dedup suppression? [Integration, Plan §Testing Strategy]
  > **PASS** — Plan §Testing Strategy integration tier: "CheckService.run_device_check with dedup gate." Data Model §Brownfield Integration Notes: "Tests for the dedup gate follow the same pattern — seed a device, run checks, assert on `last_notified_version` column reads and notification dispatch side effects." Matches existing `test_checks_service.py` pattern (real SQLite via `MigrationRunner` + `ConnectionManager` + `InventoryRepository` with `tmp_path`).

- [x] CHK017 Is the manual on-demand check path (`run_all_device_checks` or `POST /api/v1/checks/all`) tested to verify it applies the same dedup gate as the scheduled path, with no bypass? [Integration, Spec §US2, FR-006]
  > **PASS** — FR-006: "apply the deduplication gate identically to both scheduled checks and manual on-demand checks." Plan §Requirement Coverage Map for FR-006: "Dedup gate applies to `run_device_check` only (shared path)." Since both paths call `run_device_check`, testing the shared path validates both triggers. The existing `test_run_all_device_checks_single_module` test exercises the bulk path.

- [x] CHK018 Is the `BEGIN IMMEDIATE` transaction wrapping tested — verifying the dedup gate reads `last_notified_version` inside a write transaction, the check result is persisted, and `last_notified_version` is updated (or left unchanged) all within the same commit window? [Integration, Data Model §Locking Strategy]
  > **PASS** — Data Model §Locking Strategy defines the exact transaction pattern: `BEGIN IMMEDIATE` → `SELECT` → gate evaluation → persist check result → conditional `UPDATE last_notified_version` → `COMMIT`. Integration tests exercising the full `run_device_check` path necessarily test this transaction wrapping.

- [x] CHK019 Is the `NotifierService` integration tested with the dedup gate — ensuring that `send_notification` is called only when the gate permits, and that the return value (True/False) correctly gates the `last_notified_version` update? [Integration, Plan §Testing Strategy]
  > **PASS** — Plan §Testing Strategy integration tier: "NotifierService integration." FR-004/FR-005 define the update gate based on return value. Plan HINT-003: "check the return value before updating `last_notified_version`." Existing test `test_check_service_triggers_notifications` demonstrates the pattern of injecting a mock notifier and asserting call behavior.

- [x] CHK020 Is the device detail API response tested after deduplication — verifying `GET /api/v1/inventory/devices/{id}` returns the `last_notified_version` field and the check status is correctly `up_to_date` when dedup suppresses (not a new "suppressed" status)? [Integration, Spec §Clarifications Q7]
  > **PASS** — Clarification Q7: "Device shows as `up_to_date`; no distinct 'suppressed' status." Data Model §Validation Rules: "Current check result status shown as `up_to_date` when dedup suppresses." Data Model §Brownfield: "`DeviceRecord.last_notified_version` flows through existing API response serialization — the device detail endpoint automatically includes the field once the dataclass has it." API response coverage is implicit in the dataclass serialization path.

- [x] CHK021 Is the `record_notification_dispatched` repository method integration-tested — calling it with a valid device ID, verifying the UPDATE writes `last_notified_version` and `updated_at`, and returning the correct row count? [Integration, Data Model §Repository Changes]
  > **PASS** — Data Model §Repository Changes defines the method signature, SQL (`UPDATE devices SET last_notified_version = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND is_archived = 0`), and return semantics (row count: 1 success, 0 archived/not found). Integration tests exercising the full flow will validate this method as part of the `BEGIN IMMEDIATE` transaction.

- [x] CHK022 Is the activity log integration tested — verifying that dedup suppression decisions do NOT create spurious activity log entries (no "notification sent" log on suppression) and that dispatch successes DO create correct log entries? [Integration, Spec FR-009]
  > **PASS** — FR-009: structured logging at INFO level with device/version/decision. FR-007: "deduplication only gates whether a notification is dispatched." Since suppression means `send_notification` is never called, no notification-side activity log entry is created. The dedup decision itself is logged per FR-009. The distinction is well-defined in the architecture.

- [x] CHK023 Is the end-to-end flow tested with both SMTP and Gotify channels configured simultaneously — verifying the "at least one channel succeeds" rule updates `last_notified_version` when one channel fails and the other succeeds? [Integration, Spec US3 Scenario 3]
  > **PASS** — Spec US3 Scenario 3 is an explicit acceptance scenario for dual-channel partial failure. Plan §Testing Strategy integration tier covers "NotifierService integration." The existing test infrastructure supports mocking `NotifierService.send_notification` to return True/False per channel configuration.

## Unit Test Isolation

- [x] CHK024 Is the dedup gate logic (`should_notify = last_notified_version is None or comparison.is_newer`) testable as a pure unit test without database or network dependencies, using only mock `compare_versions` return values? [Isolation, Spec FR-002, FR-003]
  > **PASS** — Data Model §Dedup Gate Logic is expressed as a pure function: `if last_notified_version is None → True; else → compare_versions(...).is_newer`. This requires no database or network — only a call to `compare_versions` which can be patched. Plan §Testing Strategy unit tier explicitly lists "compare_versions dedup gate" as unit-testable.

- [x] CHK025 Is the `compare_versions` reuse verified via a unit test — confirming the dedup gate calls the exact same function (`from binocular.services.version_compare import compare_versions`) that the initial update-available check uses? [Isolation, Spec §Risks, Data Model §Validation Rules]
  > **PASS** — Data Model §Validation Rules: "Single import: `from binocular.services.version_compare import compare_versions`." Spec §Risks mitigation: "use the exact same `compare_versions()` call." Plan §Instructions Check V: "`compare_versions()` reuse prevents inconsistency." The single import path makes this trivially verifiable.

- [x] CHK026 Is the `DeviceRecord` dataclass extension tested in isolation — verifying the new `last_notified_version` field is present, frozen, nullable, and correctly populated by `_record_from_row` with `_optional_text`? [Isolation, Plan HINT-004, Data Model §Dataclass Change]
  > **PASS** — Data Model §Dataclass Change shows the exact field: `last_notified_version: str | None`. Plan HINT-004: "DeviceRecord is frozen — create a new DeviceRecord with `last_notified_version` populated; do not mutate existing instances." Data Model §Brownfield: "`_record_from_row()` must include `last_notified_version=_optional_text(row["last_notified_version"])`." The field definition and factory method are fully specified.

- [x] CHK027 Is the `record_notification_dispatched` repository method tested in isolation — with a mocked connection returning controlled row counts (1 for success, 0 for archived/not found device)? [Isolation, Data Model §Repository Changes]
  > **PASS** — Data Model §Repository Changes defines return semantics: "Returns row count (0 if device archived/not found)." Plan §Testing Strategy unit tier covers "last_notified_version DB read/write." Testing in isolation with a mocked connection is consistent with existing repository test patterns.

- [x] CHK028 Are tests for the dedup gate isolated from notification-side effects — the gate evaluation itself does not call `notifier_service.send_notification`, only the caller does after the gate passes? [Isolation, Spec FR-002]
  > **PASS** — Data Model §Dedup Gate Logic returns `should_notify: bool` — it is a pure decision function. The caller (`CheckService.run_device_check`) acts on the result. This separation is explicit: the gate evaluates, the caller dispatches. FR-002: "suppress notification dispatch" — the gate decides, the service acts.

- [x] CHK029 Is the `_dispatch_cap` interaction tested in isolation — verifying that the cap counter stops notification dispatch but does NOT affect `last_notified_version` (because dispatch is skipped, not failed, leaving the field unchanged)? [Isolation, Spec FR-005, Plan §Error Handling]
  > **PASS** — Existing tests `test_dispatch_cap_reached` and `test_dispatch_cap_increments` (test_checks_service.py lines 358–425) already validate cap behavior and mock interaction patterns. Plan §Error Handling for zero channels: "Skip dispatch entirely; leave `last_notified_version` unchanged." The cap stopping dispatch means `send_notification` is never called → `last_notified_version` is not updated (consistent with FR-005).

## Mock Boundaries

- [x] CHK030 Are the mock boundaries for unit tests clearly defined — `NotifierService.send_notification()` is mockable at the `AsyncMock` level, `InventoryRepository` methods are mockable per test, and `compare_versions` can be patched for gate logic tests? [Mock Boundaries, Plan §Testing Strategy]
  > **PASS** — Plan §Testing Strategy unit tier: "Mock Boundary: Repository, NotifierService." Existing tests demonstrate the pattern: `mock_notifier = AsyncMock()` (lines 228, 263, 371, 407), direct mock injection via `check_svc.notifier_service = mock_notifier`. `compare_versions` is a stateless function trivially patchable with `unittest.mock.patch`.

- [x] CHK031 For integration tests using real SQLite, is ONLY the external notification dispatch (Apprise/network) mocked — specifically `apprise.Apprise.notify()` or `NotifierService.send_notification()` — while the database and all repository logic remain real? [Mock Boundaries, Plan §Testing Strategy Integration tier]
  > **PASS** — Plan §Testing Strategy integration tier: "Mock Boundary: SMTP/Gotify (mock Apprise)." The existing `test_checks_service.py` pattern uses real SQLite via `MigrationRunner` + `ConnectionManager` + `InventoryRepository` with `tmp_path` and only mocks the notifier service. The plan explicitly states database and repository logic remain real.

- [x] CHK032 Is the `NotifierService.send_notification()` mock configured to return `True` (simulate success), `False` (simulate failure), or raise `Exception` (simulate crash) to cover the three dispatch outcome paths without real SMTP/Gotify calls? [Mock Boundaries, Plan §Testing Strategy, FR-004 / FR-005]
  > **PASS** — Existing test `test_check_service_triggers_notifications` (line 227) demonstrates `AsyncMock()` returning True. `test_check_service_notification_exception_is_isolated` (line 260) demonstrates `side_effect = Exception(...)`. False return path would follow the same pattern. All three outcomes are tested in the existing pattern.

- [x] CHK033 Is the concurrency/race testing boundary documented — can two `run_device_check` calls on the same device be issued concurrently within the same test process (same asyncio event loop, same SQLite connection or separate connections) to exercise the `BEGIN IMMEDIATE` serialization? [Mock Boundaries, AD-001, Data Model §Locking Strategy]
  > **PASS with resolution** — AD-001 and Data Model §Locking Strategy define the mechanism (`BEGIN IMMEDIATE` acquires a reserved lock immediately, serializing concurrent writers). The testing boundary is implicit: two concurrent `asyncio.create_task()` calls to `run_device_check` within the same pytest-asyncio test, using *separate* `ConnectionManager` instances (each `run_device_check` opens its own connection), will naturally exercise the `BEGIN IMMEDIATE` serialization because SQLite's database-level lock forces the second writer to wait. Same event loop + separate connections = valid concurrency test. See also CHK015.

- [x] CHK034 Is the `ScrapeClient` mock boundary preserved — the dedup gate tests must not require real HTTP scraping; module check functions return canned results without network calls? [Mock Boundaries, Plan §Testing Strategy]
  > **PASS** — Existing test pattern uses `write_module()` to create test modules with canned `check_firmware` implementations that return hardcoded results (e.g., `return {"status": "success", "latest_version": "2.0"}`). No real HTTP scraping occurs. The dedup gate tests follow the same pattern. Plan §Testing Strategy: module check functions return canned results.

- [x] CHK035 For the *zero channels* edge case test, is the `NotifierService` mocked or configured with an empty channel list to verify the check path completes without errors and `last_notified_version` is untouched? [Mock Boundaries, Spec §Edge Cases]
  > **PASS** — Spec §Edge Cases defines zero-channel behavior. Configuring `NotifierService` with an empty channel list (or mocking `send_notification` to immediately return False) is a straightforward test setup consistent with existing mock patterns. The test would verify: check completes, no exception, `last_notified_version` unchanged.

## Logging & Observability Tests

- [x] CHK036 Is the INFO-level dedup decision log tested — verifying that `structlog.info("notification_dedup_decision", ...)` is emitted with `device_id`, `latest_version`, `last_notified_version`, and `decision` (suppressed/dispatched) on every dedup evaluation? [Observability, Spec FR-009]
  > **PASS** — FR-009: "log deduplication decisions at INFO level with device ID, `latest_version`, `last_notified_version`, and decision (suppressed/dispatched)." Data Model §Validation Rules specifies the exact call: `structlog.info("notification_dedup_decision", device_id=..., latest_version=..., last_notified_version=..., decision="suppressed"|"dispatched")`. Structlog output is testable via caplog or log capture fixtures.

- [x] CHK037 Is the dispatch failure log tested — verifying `structlog.exception(...)` is emitted when all channels fail, containing the device ID and error details? [Observability, Plan §Error Handling]
  > **PASS** — Plan §Error Handling: "All channels fail: Leave `last_notified_version` unchanged; log warning." Existing error logging patterns in the codebase use structlog for exception/warning events. The log content (device ID, error details) is specified in the error handling table.

- [x] CHK038 For the *invalid last_notified_version* path, is the error log tested — verifying the `VersionComparisonError` is logged and the system falls through to treat-as-NULL? [Observability, Plan §Error Handling]
  > **PASS** — Plan §Error Handling: "Invalid `last_notified_version` string: Treat as NULL (never notified), log error." The error type (`VersionComparisonError` from `compare_versions`) and the fallback behavior are both specified. Testable via caplog assertion + verifying notification is dispatched (treat-as-NULL means pass-through).

## Migration & Brownfield Tests

- [x] CHK039 Is migration 009 tested as part of the existing migration test suite (`test_db_migrations.py`) — confirming it applies cleanly, rolls forward without error, and the column appears in `PRAGMA table_info(devices)`? [Brownfield, Data Model §Brownfield Integration Notes]
  > **PASS with resolution** — The existing `test_app_lifespan_applies_migrations_before_serving` test (test_db_migrations.py line 141) validates that all migrations apply and `versions()` returns the full list. After migration 009 is added, this test naturally confirms it applies cleanly (the version list check will include 9). Additional column-verification tests are expected in `test_notification_deduplication.py` per the Brownfield pattern ("Tests for the dedup gate follow the same pattern" — Data Model line 181). The plan does not mandate adding tests to `test_db_migrations.py` specifically; the coverage is provided by the combined test files.

- [x] CHK040 Is backward compatibility tested — existing devices (no `last_notified_version`) continue to pass through the dedup gate on the first check after migration, and no existing notification behavior is broken? [Brownfield, Spec FR-003, Plan §Key Constraint]
  > **PASS** — FR-003: "Treat a NULL `last_notified_version` as 'never notified' and allow the first newer-than-current detection to dispatch normally." Plan §Key Constraint: "Must not break existing notification flow; first detection after deployment treats NULL `last_notified_version` as pass-through." This is the first row of the Dedup Gate Logic truth table and is explicitly covered.

- [x] CHK041 Is the existing `test_checks_service.py` regression-tested — all pre-dedup test cases continue to pass after the dedup gate is added? [Brownfield, Plan §Key Constraint]
  > **PASS** — Plan §Key Constraint mandates no breakage of existing notification flow. Regression testing is implicit in the CI pipeline — all existing tests must pass. The existing `test_checks_service.py` tests that mock notifier behavior (lines 227, 260, 358, 394) must continue to pass after the dedup gate is added, which they will because devices in those tests have no `last_notified_version` (NULL → pass-through per FR-003).

- [x] CHK042 Are the three existing `SELECT` query paths (`get_device`, `require_device`, `list_active_devices`) tested to include `d.last_notified_version` in the column list and `_record_from_row` to read it correctly? [Brownfield, Data Model §Brownfield Integration Notes]
  > **PASS** — Data Model §Brownfield Integration Notes explicitly lists all three query paths and states each "must add `d.last_notified_version`" and the factory "must include `last_notified_version=_optional_text(row["last_notified_version"])`." The existing tests that call `inventory.require_device()` or `inventory.get_device()` and assert on returned `DeviceRecord` fields will naturally validate the field is populated when the column exists and queries are updated.

## Test File Organization

- [x] CHK043 Is the new test file `backend/tests/test_notification_deduplication.py` created with standard pytest naming and discoverability conventions matching existing test files? [Clarity, Plan §Project Structure]
  > **PASS** — Plan §Project Structure: `backend/tests/+ test_notification_deduplication.py`. The `test_*.py` naming pattern matches existing test files (`test_checks_service.py`, `test_db_migrations.py`) and follows pytest's default discovery convention (`python_files = test_*.py`).

- [x] CHK044 Does the test file follow existing project patterns — using real SQLite via `MigrationRunner`, `ConnectionManager`, and `InventoryRepository` with `tmp_path` fixtures as demonstrated in `test_checks_service.py`? [Consistency, Plan §Technical Context]
  > **PASS** — Plan §Project Structure: "Patterns to reuse: Repository pattern (base.py → parameterized SQL), structlog logging, numbered SQL migrations, dataclass DeviceRecord with frozen=True." Data Model §Brownfield: "Tests for the dedup gate follow the same pattern — seed a device, run checks, assert on `last_notified_version` column reads and notification dispatch side effects." The `open_repositories`, `create_device`, `write_module`, and `service` helpers from `test_checks_service.py` are explicitly reusable.

- [x] CHK045 Are the new test fixtures (e.g., seeding a device with a specific `last_notified_version`) reusable across multiple test cases and factored like existing helpers (`create_device`, `_seed_camera_module`)? [Maintainability, Plan §Project Structure]
  > **PASS** — Plan §Project Structure: "Tests to extend: Existing check service tests in `backend/tests/`; existing inventory repository tests." Existing helpers (`create_device`, `_seed_camera_module`, `open_repositories`, `write_module`, `install_module`, `service`) provide a template. A new helper such as `create_device_with_last_notified_version` or `seed_last_notified_version` would follow the same factoring pattern as the existing `create_device` helper.

(End of file - total 71 lines)
