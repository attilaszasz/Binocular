---
feature_branch: "00014-notification-alerting"
created: "2026-06-11"
input: "E014"
spec_type: "product"
spec_maturity: "draft"
epic_id: "E014"
epic_sources: "{PRD:CAP-007}{SAD:ADR-0007}"
product_document: "specs/prd.md"
---

# Feature Specification: Notification & Alerting

**Feature Branch**: `00014-notification-alerting`  
**Created**: 2026-06-11  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: draft  
**Epic ID**: E014  
**Epic Sources**: {PRD:CAP-007}{SAD:ADR-0007}  
**Product Document**: specs/prd.md

## Problem Statement

When Binocular detects a new firmware version, the self-hosting operator has no automated way to receive this information, requiring them to constantly check the UI. Without automated email or chat notifications, the operator may miss critical security patches or features, undermining the "set-and-forget" promise of the product. Additionally, repeated notifications for the same version would cause alert fatigue, so smart version tracking and deduplication are required.

## Scope

### Included

- Migration to add `last_notified_version` (nullable TEXT) to `devices` table.
- Migration to create `notification_channels` table storing type (e.g., `email`, `gotify`), config (JSON), and enabled status.
- Integration of Apprise for dispatching notifications via Email/SMTP and Gotify.
- Responsive HTML email rendering using Jinja2 templates (light-themed, matching the app's clean light-gray design).
- Deduplication: track `last_notified_version` on each device, only dispatching alerts if the new version is strictly newer than `last_notified_version` (or if it hasn't been notified yet).
- API routes to get, save, and test notification channel configurations.
- Settings UI page in the React application to manage channels (Email/SMTP and Gotify settings) and run test dispatches.
- Logging of notification delivery failures directly to the system's activity log.

### Excluded

- In-app marketplace or directory of notification providers (only Email/SMTP and Gotify are officially built-in).
- Custom templating engines or user-editable email templates via UI (Jinja2 templates are static backend files).
- Gotify instance hosting (the user must host/provide their own Gotify server).

### Edge Cases & Boundaries

- **Invalid SMTP / Gotify Credentials**: The system must not crash; it must log the failure in the activity log and report it on test execution.
- **Malformed Version Strings**: If version strings do not follow strict semver, a lexicographical comparison fallback or raw equality fallback must be used, preventing a block in the check execution.
- **Multiple Channels Enabled**: If both Email and Gotify are enabled, failure in one channel must not prevent delivery to the other.

## User Scenarios & Testing

### User Story 1 - Configure Notification Channels (Priority: P1)

As an operator, I want to configure SMTP email settings and Gotify tokens in the application UI so that the app knows where to send alerts.

**Why this priority**: Core value proposition — without channel configuration, the system cannot notify the operator.

**Independent Test**: Save a Gotify configuration via the Settings UI and verify that it persists in the backend SQLite database.

**Acceptance Scenarios**:

1. **Given** the operator is on the Settings page, **When** they fill in valid SMTP details (host, port, username, password, from/to emails) and click Save, **Then** the settings are saved, a success toast appears, and the values persist across page refreshes.
2. **Given** the operator has saved a Gotify token, **When** they return to the Settings page, **Then** the Gotify settings are displayed (with password/tokens masked or hidden where appropriate).

### User Story 2 - Deduplicated Alerting on Update (Priority: P1)

As an operator, I want to receive a single notification when a new version is detected, and not receive duplicate notifications for that same version on subsequent checks.

**Why this priority**: Prevents alert fatigue and ensures the system operates as a reliable "set-and-forget" utility.

**Independent Test**: Trigger a scheduled check that detects a new version, verify a notification is dispatched, and verify that subsequent checks for that same version do not dispatch further notifications.

**Acceptance Scenarios**:

1. **Given** a device with current version `1.0.0` and no `last_notified_version`, **When** a check detects version `2.0.0`, **Then** a notification is dispatched via all enabled channels and `last_notified_version` is updated to `2.0.0`.
2. **Given** a device with `last_notified_version` set to `2.0.0`, **When** another check runs and detects version `2.0.0`, **Then** no notification is dispatched.
3. **Given** a device with `last_notified_version` set to `2.0.0`, **When** a check detects version `2.1.0`, **Then** a notification is dispatched and `last_notified_version` is updated to `2.1.0`.

### User Story 3 - Test Channel Configuration (Priority: P1)

As an operator, I want to send a test alert for a channel before enabling it so that I can verify my SMTP or Gotify credentials are correct.

**Why this priority**: Avoids silent configuration errors where notifications are misconfigured and never received.

**Independent Test**: Click the "Test" button on Gotify settings with valid credentials and verify a test message is received on the Gotify client.

**Acceptance Scenarios**:

1. **Given** the operator has entered valid Gotify server details, **When** they click "Test", **Then** the backend attempts to send a test alert, and the UI displays a success status.
2. **Given** the operator has entered an invalid SMTP server host, **When** they click "Test", **Then** the backend attempts connection, fails, logs the error, and the UI displays the error message.

### User Story 4 - View Notification Failures in Activity Log (Priority: P2)

As an operator, I want to see notification dispatch errors in the activity log so that I can troubleshoot why alerts are failing.

**Why this priority**: Essential troubleshooting visibility when SMTP servers go down or API keys expire.

**Independent Test**: Trigger an update alert with invalid SMTP settings and verify that an error log entry is written to the activity log.

**Acceptance Scenarios**:

1. **Given** a scheduled check detects a new version but the SMTP server returns a authentication error, **When** the dispatch fails, **Then** a failure message containing the error details is logged to the database activity log.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST allow operators to save, update, and read notification channel configs for Email/SMTP and Gotify.
- **FR-002**: The system MUST store channel configurations securely in a database table called `notification_channels`.
- **FR-003**: The system MUST dispatch notifications via Apprise using enabled channels when a new firmware version is detected.
- **FR-004**: The system MUST render emails in responsive HTML format using a Jinja2 template styled with light-themed colors.
- **FR-005**: The system MUST compare versions and only dispatch alerts when the detected version is newer than `last_notified_version` (or if `last_notified_version` is null).
- **FR-006**: The system MUST update `last_notified_version` to the detected version immediately after a successful notification dispatch.
- **FR-007**: The system MUST expose a POST `/api/v1/notifications/test` endpoint to trigger a dry-run/test alert for verification.
- **FR-008**: The system MUST log all delivery failures to the activity log.

### Key Entities

- **NotificationChannel**: Represents a configured alerting channel.
  - `id`: INTEGER (Primary Key)
  - `type`: TEXT (e.g., `'email'`, `'gotify'`)
  - `enabled`: BOOLEAN
  - `config`: TEXT (JSON serialized configuration dictionary)
- **Device**: Extended entity from E006.
  - `last_notified_version`: TEXT (Nullable, stores the last version that was successfully notified to the user)

## Assumptions & Risks

### Assumptions

- The operator's host environment has outgoing network access to SMTP servers and the Gotify API endpoint.
- Apprise is capable of resolving and routing requests to standard SMTP and Gotify endpoints.
- Version strings are parseable as standard semantic versions or compare lexicographically.

### Risks

- **[SMTP Blockages]** *(likelihood: medium, impact: high)*: Local SMTP servers or firewalls might block port 25/465/587, leading to timed-out SMTP connections. Mitigation: The test button and logs help identify blockages immediately.
- **[Gotify Rate Limiting]** *(likelihood: low, impact: medium)*: High volume of test alerts may hit rate limits. Mitigation: Add in-UI warning on rate limits.

## Implementation Signals

- `MIGRATION` — Add `last_notified_version` to `devices` table; create `notification_channels` table.
- `NEW-ENTITY` — Create `NotificationChannel` model/repository.
- `NEW-API` — Endpoints under `/api/v1/notifications` for GET (list config), PUT (save config), and POST (test config).
- `NEW-UI` — Notification settings form in Settings SPA tab.
- `NEW-WORKER` — Integrate notifier dispatch inside the check runner after a version update is found.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: The Settings UI successfully saves and retrieves SMTP and Gotify credentials to/from SQLite.
- **SC-002** [US2]: A check finding a new version triggers an email and Gotify dispatch, and updates `last_notified_version` in the database.
- **SC-003** [US2]: Subsequent checks for the same firmware version trigger zero notification dispatches.
- **SC-004** [US3]: A test dispatch returns success/failure within 5 seconds in the UI.

## Glossary

| Term | Definition |
|------|------------|
| Apprise | A Python library simplifying notification delivery across many different platforms. |
| Gotify | A self-hosted notification server for sending and receiving push messages. |
| last_notified_version | Database field on devices tracking the last firmware version that triggered an alert. |

## Compliance Check

### Instructions Check Report
**Target**: spec.md
**Status**: PASS

| Principle | Verdict | Notes |
|-----------|---------|-------|
| I. Honest Failure | PASS | Delivery failures logged to activity log. |
| II. Polite by Default | PASS | Outbound SMTP/Gotify handled via Apprise integration, honoring configurations. |
| III. Data Ownership & Self-Containment | PASS | Config and notification state persisted in SQLite, no external servers. |
| IV. Least-Privilege & Explicit Trust Boundary | PASS | Non-root container compatibility; no claims of sandboxing. |
| V. Type Safety & Correctness-First | PASS | High-level requirements mapped; strict static typing guidelines respected. |
| VI. Set-and-Forget Reliability | PASS | Fault-isolation for notification failures; tracking last_notified_version prevents duplicate alerts. |

**Violations**:
None.

