---
feature_branch: "00017-notification-alerting-apprise"
created: "2026-06-01"
input: "E012 Notification & Alerting — Apprise dispatch to Email/SMTP + Gotify"
spec_type: "product"
spec_maturity: "clarified"
epic_id: "E012"
epic_sources: "{PRD:CAP-007}{SAD:ADR-0007}"
---

# Feature Specification: Notification & Alerting

**Feature Branch**: `00017-notification-alerting-apprise`  
**Created**: 2026-06-01  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: clarified  
**Epic ID**: E012  
**Epic Sources**: {PRD:CAP-007}{SAD:ADR-0007}  
**Product Document**: specs/prd.md

## Problem Statement

When Binocular discovers a newer firmware version during scheduled or manual checks, the operator remains unaware unless they actively visit the web UI. To fulfill the core set-and-forget value proposition, the system needs an automated way to push alerts directly to the operator. Unreliable notification dispatches or hard-to-configure channels can result in missed updates or a broken alerting loop without the user's knowledge.

## Scope

### Included

- **Multi-channel Configuration**: Let the operator configure independent channel settings for Email/SMTP and Gotify through the UI.
- **Stateless Verification (Test Dispatch)**: Provide a "Send Test Notification" trigger in the UI that attempts immediate dispatch to verify settings without waiting for a real detection event.
- **Automated Alert Dispatch**: Automatically dispatch alerts via Apprise to all enabled channels when a newer-than-recorded firmware version is detected.
- **Fail-Safe Integrity**: Ensure notification failures do NOT affect the underlying database check-result update. A failed dispatch must be caught, logged, and surfaced without rollback or crash.
- **Credential Security**: Support environment variables and `_FILE` secret convention loading for credentials, masking passwords/tokens when reading configuration in the UI.

### Excluded

- **In-App Notification Inbox**: Binocular does not maintain a notification inbox inside the UI; it dispatches alerts directly to external services.
- **Other Notification Channels**: Non-SMTP and non-Gotify dispatch systems (e.g., Discord, Slack, Telegram) are out of scope for the initial release, though the core uses Apprise to maintain extensibility.

### Edge Cases & Boundaries

- **Invalid Configuration**: Saving blank hostnames, invalid ports, or malformed Gotify tokens is blocked by robust form validation in the UI/API.
- **Outage of External Service**: If SMTP or Gotify is down during dispatch, Binocular logs a detailed diagnostic error to `structlog` and the activity logs, but keeps the device's latest version persisted.
- **Parallel Dispatch**: If multiple updates are detected simultaneously, notifications are dispatched concurrently without blocking the core execution loop.

## User Scenarios & Testing

### User Story 1 - Configure Notification Channels (Priority: P1)

As an operator, I want to configure and persist Email/SMTP and Gotify settings so that I can choose my preferred alerting channel.

**Why this priority**: Core utility — alerting cannot work without a way to set up target destinations.

**Independent Test**: Configure SMTP and Gotify settings, save them, reload the application, and verify that the saved values are preserved and masked appropriately.

**Acceptance Scenarios**:

1. **Given** no configured channels, **When** the operator inputs valid SMTP credentials and saves, **Then** Binocular persists the settings in SQLite and lists SMTP as enabled.
2. **Given** saved Gotify settings, **When** the operator views the configuration, **Then** the Gotify application token is masked with `********` for security.
3. **Given** invalid values (e.g., negative port or empty hostname), **When** the operator saves, **Then** the API rejects the request with a `422 Unprocessable Entity` response.

### User Story 2 - Test Channels from the UI (Priority: P1)

As an operator, I want to trigger a test notification from the UI so that I can verify that my credentials and endpoints are correct.

**Why this priority**: Crucial verification — users need to confirm that email or push notifications work before relying on them for unattended operations.

**Independent Test**: Input valid settings, click "Send Test", and verify receipt of a test notification.

**Acceptance Scenarios**:

1. **Given** valid unsaved channel settings in the UI, **When** the operator clicks "Send Test", **Then** Binocular attempts instant dispatch via Apprise and shows a success banner.
2. **Given** a down/unreachable Gotify server, **When** the operator triggers a test, **Then** the UI shows a clear error message containing the Apprise failure details.

### User Story 3 - Automatic Alerting on Detection (Priority: P1)

As the system, I want to automatically dispatch notifications when a newer firmware version is detected so that the operator is informed without manual checks.

**Why this priority**: Core value loop — completes the detect → compare → notify flow.

**Independent Test**: Trigger a check that detects a newer version than recorded and confirm that a notification is received.

**Acceptance Scenarios**:

1. **Given** an enabled SMTP channel and a recorded device at version `1.0.0`, **When** a check detects version `2.0.0`, **Then** Binocular updates the database and dispatches an email alert with the device details.
2. **Given** multiple active channels (both SMTP and Gotify enabled), **When** a newer version is detected, **Then** both channels receive the notification.
3. **Given** SMTP dispatch fails due to an authentication error, **When** a newer version is detected, **Then** the version is still updated in the inventory, and a failure is recorded in the activity log.

## Requirements

### Functional Requirements

- **FR-001**: System MUST support configuring a single Email/SMTP notification channel.
- **FR-002**: System MUST support configuring a single Gotify notification channel.
- **FR-003**: System MUST persist all notification channel configurations in the application SQLite database.
- **FR-004**: System MUST allow enabling/disabling channels individually.
- **FR-005**: System MUST expose an endpoint to trigger a test notification to a given channel setup.
- **FR-006**: System MUST automatically dispatch alerts to all enabled channels when a check result transitions to `newer_found`.
- **FR-007**: System MUST use Apprise (`apprise` package) as the underlying notification library.
- **FR-008**: System MUST mask sensitive parameters (e.g., SMTP passwords, Gotify tokens) in UI read responses.
- **FR-009**: System MUST support loading credentials using standard environment variables and `_FILE` suffix conventions.
- **FR-010**: System MUST handle notification dispatch failures gracefully, logging them contextually while ensuring the check-result persistence completes successfully.

### Key Entities

- **NotificationChannel**: Represents a configured alerting destination. Attributes include: `id` (int/uuid), `type` (SMTP, Gotify), `enabled` (boolean), `config` (JSON block containing credentials/endpoints), `created_at`, `updated_at`.
- **DetectionEvent**: Represents the event payload passed to the notifier, containing the device name, device type, old version, new version, and source URL.

## Assumptions & Risks

### Assumptions

- The operator has a working SMTP server or a reachable Gotify server.
- The `apprise` package works correctly within the Python 3.13 runtime environment.
- SQLite remains the sole repository of all configurations and activity logs.

### Risks

- **Network Blocking or Firewalls** *(likelihood: low, impact: high)*: Homelab network topology might block outbound SMTP port 587 or 465; mitigated by UI test-notification triggers to diagnose issues immediately.
- **Slow Notification I/O Blocking the Main App** *(likelihood: medium, impact: medium)*: Blocking SMTP calls can slow down the FastAPI thread pool; mitigated by executing Apprise dispatches in an async thread pool executor.
- **Silent Failures** *(likelihood: medium, impact: high)*: An expired token makes alerts disappear silently; mitigated by logging failures clearly to stdout via `structlog` and writing them to the activity log.

## Implementation Signals

- `NEW-ENTITY` — Add `NotificationChannel` schema and model to backend data layer.
- `MIGRATION` — Add SQL migration file `005_notification_channels.sql` to create `notification_channels` table in SQLite.
- `NEW-API` — Add `/api/v1/notifications` router for configuring channels and triggering test notifications.
- `NEW-UI` — Add "Notifications" configuration tab/view with form controls and "Send Test" buttons.
- `NEW-WORKER` — Add background async thread runner for non-blocking Apprise dispatch.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: An operator can save and read Email/SMTP and Gotify configurations via the UI.
- **SC-002** [US2]: Clicking "Send Test" sends a test notification through the configured channel and returns success/failure status in the UI.
- **SC-003** [US3]: Detection of a newer firmware version triggers non-blocking Apprise alerts to all enabled channels.
- **SC-004** [US3]: Outage of an alerting channel does not crash the check loop or block database version updates.

## Glossary

| Term | Definition |
|------|------------|
| Apprise | The underlying Python notification abstraction library. |
| Gotify | A self-hosted real-time push notification server. |
| Notification Channel | A saved configuration describing where and how alerts are sent. |
| Masking | Replacing sensitive credentials with asterisks in API/UI read views. |

## Compliance Check

### Instructions Check Report
**Target**: specs/00017-notification-alerting-apprise/spec.md  
**Status**: PASS

| Principle | Verdict | Notes |
|-----------|---------|-------|
| Honest Failure | PASS | Dispatch failures do not break the check loop, and are logged contextually to activity logs. |
| Polite by Default | PASS | Integrates politely with homelab alerts, avoiding heavy loops or continuous retries on down channels. |
| Data Ownership & Self-Containment | PASS | Credentials and channel config reside entirely in the self-contained SQLite file. |
| Least-Privilege & Explicit Trust Boundary | PASS | Credentials loaded via env/`_FILE` secrets, masked in UI, and parameterized in SQLite. |
| Type Safety & Correctness-First | PASS | Full test coverage is required for Apprise integrations and masking. |
| Set-and-Forget Reliability | PASS | Standard alerts ensure operators remain updated without checking the dashboard. |

**Violations**:  
None
