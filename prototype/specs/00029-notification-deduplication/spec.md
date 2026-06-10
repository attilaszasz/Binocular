---
feature_branch: "00029-notification-deduplication"
created: "2026-06-07"
input: "E028 Notification Deduplication — track last-notified version per device, gate repeat alerts"
spec_type: "product"
spec_maturity: "clarified"
epic_id: "E028"
epic_sources: "{PRD:CAP-007}{SAD:ADR-0007}"
---

# Feature Specification: Notification Deduplication

**Feature Branch**: `00029-notification-deduplication`  
**Created**: 2026-06-07  
**Status**: Clarified  
**Spec Type**: product  
**Spec Maturity**: clarified  
**Epic ID**: E028  
**Epic Sources**: {PRD:CAP-007}{SAD:ADR-0007}  
**Product Document**: specs/prd.md

## Problem Statement

Currently, every scheduled check that finds a firmware version newer than the user's recorded version dispatches a notification — even if that exact same version already triggered a notification on a previous check. If the operator hasn't updated their device yet, repeated checks fire duplicate alerts for the same version, causing alert fatigue and eroding trust in the set-and-forget promise. The system needs to remember which version was last notified per device and suppress repeat alerts for already-reported versions.

## Scope

### Included

- Track the last firmware version for which a notification was dispatched per device (`last_notified_version`)
- Apply deduplication gate per FR-002: suppress notification when detected version is not strictly newer than `last_notified_version`
- Both scheduled and manual on-demand checks must respect the deduplication gate (FR-006)
- Devices with no recorded `last_notified_version` (e.g., existing devices before this feature) notify on the first newer-than-current detection (FR-003)
- Update `last_notified_version` only after at least one notification channel confirms successful dispatch (FR-004, FR-005)

### Excluded

- Per-channel deduplication state — single `last_notified_version` per device regardless of which channels succeed or fail
- Time-window suppression (e.g., "only notify once per 24 hours") — deduplication is version-based, not time-based
- Notification history or inbox — tracking is limited to the single `last_notified_version` field
- Changing existing Gotify or Email/SMTP format behavior — deduplication gates dispatch but does not alter message content

### Edge Cases & Boundaries

- **Dispatch failure**: FR-005 — if all notification channels fail, `last_notified_version` must not be updated; the next check retries notification for the same version
- **Partial dispatch success**: FR-004 — if at least one channel succeeds, `last_notified_version` is updated normally
- **User downgrades firmware**: If `current_version` is set lower than a previously-notified version, the dedup gate naturally prevents re-notification for the previously-seen version
- **Existing devices at deployment**: FR-003 — devices without a recorded `last_notified_version` treat the first detected newer-than-current version as notification-worthy (NULL = never notified)
- **Version format changes**: FR-002 — must use the same `compare_versions()` function used for the initial update-available check to avoid inconsistencies. When `compare_versions()` cannot parse either `latest_version` or `last_notified_version`, the system MUST treat the comparison as indeterminate: log a WARNING, suppress the notification (fail-safe), and record the check as `check_failed`.
- **Zero configured notification channels**: When no notification channels are enabled, the system treats the device as having no delivery capability — the check persists the result as `up_to_date` (if latest equals last_notified) or `update_available` (if newer), skips dispatch entirely, and `last_notified_version` remains unchanged
- **Invalid `last_notified_version` string**: If `last_notified_version` is non-NULL but `compare_versions()` cannot parse it, the system MUST log an error and treat the value as NULL (never notified) — see plan.md §Error Handling for details

## User Scenarios & Testing

### User Story 1 - Suppress Duplicate Notifications for Same Version (Priority: P1)

When a scheduled check detects a firmware version for a device that has already triggered a notification in a prior check run, the system suppresses the duplicate alert. The operator only sees a new notification when a genuinely newer firmware version appears.

**Why this priority**: Core value — alert fatigue is the entire problem this feature exists to solve. Without this, the feature has no utility.

**Independent Test**: Create a device, trigger a check that detects v2.0 (newer than recorded v1.0), verify notification fires and `last_notified_version` becomes v2.0. Trigger the same check again — verify no second notification is sent.

**Acceptance Scenarios**:

1. **Given** a device with `current_version = "1.0"` and no `last_notified_version`, **When** a check detects `latest_version = "2.0"`, **Then** a notification is dispatched and `last_notified_version` is set to `"2.0"`.

2. **Given** the same device now has `last_notified_version = "2.0"`, **When** a subsequent check again detects `latest_version = "2.0"`, **Then** no notification is dispatched.

3. **Given** the same device has `last_notified_version = "2.0"`, **When** a subsequent check detects `latest_version = "2.1"`, **Then** a notification is dispatched and `last_notified_version` is updated to `"2.1"`.

4. **Given** a device with `last_notified_version = "2.0"` and a check detects `latest_version = "2.0"`, **When** the check completes, **Then** the check result is persisted as `up_to_date` and the operator sees the device as current (no indication of suppressed notification).

### User Story 2 - Manual Checks Respect Deduplication (Priority: P1)

When the operator triggers a manual on-demand check for a device that already had a notification for the detected version, the system suppresses the duplicate just like scheduled checks. Manual checks only produce a notification if a genuinely newer version appears.

**Why this priority**: Manual checks must be consistent with scheduled checks — if they bypass deduplication, every manual check would fire duplicate alerts, defeating the feature.

**Independent Test**: After notifying for v2.0 via a scheduled check, trigger a manual check for the same device — verify no notification is sent. Then change the module fixture to return v2.1 — trigger manual check, verify notification fires.

**Acceptance Scenarios**:

1. **Given** a device with `last_notified_version = "2.0"`, **When** the operator triggers a manual check that detects `latest_version = "2.0"`, **Then** no notification is dispatched.

2. **Given** a device with `last_notified_version = "2.0"`, **When** the operator triggers a manual check that detects `latest_version = "2.1"`, **Then** a notification is dispatched and `last_notified_version` is updated to `"2.1"`.

### User Story 3 - Preserve Notification on Dispatch Failure (Priority: P1)

When a check detects a newer version but all notification channels fail to deliver, the system must not record the version as "notified" — the next check must retry notification for that version so the operator doesn't permanently miss the alert.

**Why this priority**: If `last_notified_version` is updated before dispatch and dispatch fails, the operator silently loses the alert forever. This is a correctness-critical failure mode.

**Independent Test**: Configure a broken SMTP channel, trigger a check that detects a newer version, verify `last_notified_version` remains unchanged. Fix the SMTP config, trigger another check — verify notification now fires.

**Acceptance Scenarios**:

1. **Given** a device with no `last_notified_version` and a misconfigured (failing) notification channel, **When** a check detects `latest_version = "2.0"`, **Then** dispatch fails, `last_notified_version` is not updated, and the check result is still persisted as `update_available`.

2. **Given** the same device still has no `last_notified_version` after the failed dispatch, **When** a subsequent check detects `latest_version = "2.0"` and the channel is now working, **Then** a notification is dispatched and `last_notified_version` is set to `"2.0"`.

3. **Given** a device with two notification channels (SMTP and Gotify), **When** a check detects `latest_version = "2.0"` and SMTP fails but Gotify succeeds, **Then** `last_notified_version` is updated to `"2.0"` (at least one channel succeeded).

## Requirements

### Functional Requirements

- **FR-001**: System MUST store a `last_notified_version` field per device, initially NULL for existing devices.
- **FR-002**: System MUST suppress notification dispatch when the detected `latest_version` is not strictly newer than `last_notified_version`, using the same `compare_versions(latest_version, last_notified_version).is_newer` function from `backend/src/binocular/services/version_compare.py` as the initial update-available check. When `compare_versions()` raises a `VersionComparisonError` for either operand, the system MUST treat the comparison as indeterminate, log a WARNING, suppress the notification (fail-safe), and record the check as `check_failed`.
- **FR-003**: System MUST treat a NULL `last_notified_version` as "never notified" and allow the first newer-than-current detection to dispatch normally.
- **FR-004**: System MUST update `last_notified_version` only after at least one notification channel adapter returns `True` (transport-level success: SMTP 250, Gotify HTTP 2xx, or equivalent transport acknowledgment from the channel adapter).
- **FR-005**: System MUST leave `last_notified_version` unchanged when all notification channels fail (no channel returns a success acknowledgment).
- **FR-006**: System MUST apply the deduplication gate identically to both scheduled checks and manual on-demand checks.
- **FR-007**: System MUST NOT alter the format, content, or routing of notifications — deduplication only gates whether a notification is dispatched.
- **FR-008**: System MUST serialize per-device check access using a database-level write transaction (`BEGIN IMMEDIATE` + `COMMIT` in SQLite, per data-model.md §Locking Strategy) before reading `last_notified_version` and evaluating the deduplication gate, to prevent concurrent checks from both dispatching duplicate notifications.
- **FR-009**: System MUST log deduplication decisions at INFO level as structured key-value pairs (using structlog) with `device_id`, `latest_version`, `last_notified_version`, `decision` (suppressed|dispatched), and `trigger` (scheduled|manual) for auditability and debugging. Canonical field names are defined in data-model.md §Validation Rules.
- **FR-010**: System MUST log check initiation at INFO level as structured key-value pairs with `device_id` and `trigger` (scheduled|manual) before evaluating the deduplication gate, providing a timestamped confirmation that the check was received even when the notification is suppressed.
- **FR-011**: System MUST log `last_notified_version` state transitions at INFO level as structured key-value pairs with `device_id`, `previous_value`, `new_value`, and `trigger` when the column is updated after a successful dispatch, creating an audit trail of notification state changes. See data-model.md §Validation Rules for schema.

### Key Entities

- **Device** (extended): Adds `last_notified_version` (nullable text) — the firmware version string for which the last successful notification was dispatched. NULL means no notification has ever been sent. Stored in the `devices` table. Exposed in the Device API response and visible in the UI on the device detail view.

## Assumptions & Risks

### Assumptions

- The existing `compare_versions()` function in `version_compare.py` correctly handles all firmware version formats used by official and user-authored modules.
- Notification channel configuration is stable — the dedup state doesn't need to track which specific channel succeeded, only that at least one did.
- The operator's notification channels are configured and functional; partial failures (some channels fail, some succeed) are handled by recording success when at least one channel delivers.
- A database migration adding `last_notified_version TEXT` to the `devices` table via `ALTER TABLE ADD COLUMN` with NULL default is non-blocking and requires no downtime.

### Risks

- **Version comparison inconsistency** *(likelihood: low, impact: high)*: If the dedup gate uses different comparison logic than the initial update-available check, the system could suppress valid notifications or re-fire for already-notified versions. Mitigation: use the exact same `compare_versions()` call.
- **Dispatch failure edge cases** *(likelihood: medium, impact: medium)*: Complex partial-failure scenarios (e.g., SMTP succeeds for one device but Gotify fails for another in the same batch) could create confusion. Mitigation: the simple "at least one channel = success" rule keeps behavior predictable.

## Implementation Signals

- `MIGRATION` — new numbered SQL migration adding `last_notified_version TEXT` column to the `devices` table
- `NEW-ENTITY` — `DeviceRecord` dataclass gains `last_notified_version` field
- `BREAKING-CHANGE` — `CheckService.run_device_check` signature changes to accept/read last-notified version, and notification dispatch logic adds dedup gate (though external API surface is unaffected)

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: After a notification is dispatched for version X, at most one notification per check cycle is sent when the same version X is detected — concurrent checks are serialized per device via database-level locking.
- **SC-002** [US2]: A manual on-demand check produces the same notification dispatch decision (notified or suppressed) as a scheduled check for the same device and detected version.
- **SC-003** [US3]: When all configured notification channels fail, `last_notified_version` remains unchanged and the next check attempt retries notification delivery.

## Glossary

| Term | Definition |
|------|------------|
| `last_notified_version` | The firmware version string for which the last notification was dispatched. NULL = never notified. |
| Deduplication gate | Logic comparing `latest_version` vs `last_notified_version` using `compare_versions()` before dispatch. |

## Compliance Check

Policy audit completed 2026-06-07. One violation found and remediated (zero-channels handling). All other principles pass. See analysis-report.md for details.

## Clarifications

### Session 2026-06-07

- Q: How should the system prevent duplicate notifications when two checks run concurrently for the same device? → A: Use database row-level lock (`SELECT ... FOR UPDATE`) before the dedup gate.
- Q: How does the system determine a notification channel succeeded vs. failed? → A: Channel adapter returns a boolean — transport-level acknowledgment (SMTP 250, HTTP 2xx) counts as success.
- Q: Should `last_notified_version` be exposed in the API/UI? → A: Expose in both API response and UI device detail view.
- Q: Should deduplication decisions be logged? → A: Log at INFO level with device ID, versions, and decision (suppressed/dispatched).
- Q: Should `last_notified_version` be reset when `current_version` changes? → A: Leave untouched; current logic correctly handles this (the dedup gate only suppresses when latest ≤ last_notified, not when current changes).
- Q: What are the migration constraints for adding `last_notified_version`? → A: `ALTER TABLE ADD COLUMN` with NULL default — non-blocking, no downtime needed.
- Q: What check-result status is displayed when dedup suppresses a notification? → A: Device shows as `up_to_date`; no distinct "suppressed" status — the device is current relative to the known latest version.

## Stress-Test Findings

### Session 2026-06-07

- **STF-001** [HIGH] Concurrent scheduled and manual checks on the same device can both dispatch duplicate notifications because no mutual-exclusion or serialization rule is defined. **Resolution**: Added FR-008 requiring per-device database-level lock (`SELECT ... FOR UPDATE`) before evaluating the dedup gate.
- **STF-002** [HIGH] FR-004's gate condition "confirms successful dispatch" was never defined, making SC-003 unverifiable. **Resolution**: Refined FR-004 to define success as transport-level acknowledgment (SMTP 250, Gotify HTTP 2xx).
- **STF-003** [HIGH] SC-001's absolute "zero additional notifications" guarantee was impossible without serialization. **Resolution**: Relaxed SC-001 to "at most one per check cycle" and linked to FR-008 concurrency control.
- **STF-004** [MEDIUM] Zero configured notification channels left `last_notified_version` behavior undefined. **Resolution**: Added edge case: skip dispatch, leave `last_notified_version` unchanged when zero channels are enabled.
- **STF-005** [MEDIUM] Check-result entity value during dedup suppression was unspecified. **Resolution**: Added acceptance scenario: device shows `up_to_date` when dedup suppresses notification — no distinct suppressed status.
