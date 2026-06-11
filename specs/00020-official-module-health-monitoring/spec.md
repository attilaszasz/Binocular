---
feature_branch: "00020-official-module-health-monitoring"
created: "2026-06-11"
input: "E020"
spec_type: "product"
spec_maturity: "draft"
epic_id: "E020"
epic_sources: "{PRD:CAP-014}"
---

# Feature Specification: Official Module Health Monitoring

**Feature Branch**: `00020-official-module-health-monitoring`  
**Created**: 2026-06-11  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: draft  
**Epic ID**: E020  
**Epic Sources**: {PRD:CAP-014}  
**Product Document**: specs/prd.md

## Problem Statement

When shipped official modules fail to scrape firmware updates due to target website structural changes, operators are unaware of the degradation unless they check individual device logs. This leads to silent failures where offline devices miss critical updates. Implementing automated health tracking and alerting ensures prompt visibility for operators, enabling them to update the system or modules immediately.

## Scope

### Included

- Automatic tracking of consecutive scraping failure counts and last successful check time for all official modules (where `is_official` is true).
- Configuration option for consecutive failure threshold (defaulting to 5).
- UI health indicator (banner or badge) on the official module details/cards when the threshold is exceeded.
- Automated notification dispatch via Apprise when the failure threshold is first crossed for an official module.
- Resetting the failure counter to 0 upon any successful check of the official module.

### Excluded

- Monitoring health of custom user-uploaded modules (non-official modules) — restricted to official modules to focus on maintenance and release pipelines.
- Auto-fixing or auto-updating broken scraper modules.

### Edge Cases & Boundaries

- **No devices use the module**: If an official module is registered but no active device is using it, check execution does not trigger. Health tracking is based on check runs, so it remains in a neutral state.
- **Multiple devices use the same module**: The consecutive failure count is incremented if *any* device check using that module fails, and reset if *any* device check using it succeeds.
- **Temporary network drops**: Transient network drops can trigger failures; a high enough threshold (default 5) prevents false positive alerts.

## User Scenarios & Testing

### User Story 1 - Track Failures and Display UI Alerts (Priority: P1)

As an operator, I want the system to track when official modules fail to scrape and display an in-app banner or badge on the module card so that I can immediately identify failing modules.

**Why this priority**: Core value proposition — operator must have clear in-app visibility of system and scraper health to take action.

**Independent Test**: Trigger consecutive scraping failures for an official module above the threshold and verify that the module details page displays a high-visibility error badge.

**Acceptance Scenarios**:

1. **Given** an official module is active, **When** update checks for a device using this module fail 5 times consecutively, **Then** the module status is updated to show health issues and a banner/badge appears on its card.
2. **Given** an official module has 5 consecutive failures, **When** a subsequent update check for a device using this module succeeds, **Then** the consecutive failures count resets to 0 and the health banner/badge is removed.

### User Story 2 - Dispatch Notification Alert (Priority: P2)

As an operator, I want to receive an external notification when an official module's consecutive failure count exceeds the threshold so that I am alerted without having to log into the UI.

**Why this priority**: Enhances usability and automation, but the core offline operations can function with in-app UI banners alone.

**Independent Test**: Verify that an Apprise notification is dispatched when consecutive failures reach the configured threshold.

**Acceptance Scenarios**:

1. **Given** notification channels are configured, **When** an official module's consecutive failures count reaches the threshold, **Then** a notification is dispatched via Apprise.
2. **Given** an official module already exceeds the failure threshold and has sent a notification, **When** a subsequent check fails again, **Then** no duplicate notification is dispatched (alerting is rate-limited/one-shot until reset).

## Requirements

### Functional Requirements

- **FR-001**: System MUST track the consecutive check failure count for each official module (`is_official` is true).
- **FR-002**: System MUST store the timestamp of the last successful check for each official module.
- **FR-003**: System MUST support a configurable setting `BINOCULAR_MODULE_HEALTH_THRESHOLD` (integer, default 5) for the consecutive failures limit.
- **FR-004**: System MUST reset the consecutive failure counter to 0 for an official module immediately when any check succeeds.
- **FR-005**: System MUST display a warning badge/banner in the frontend UI on the module's detail view/card when the failure threshold is exceeded.
- **FR-006**: System MUST dispatch an Apprise notification when an official module's consecutive failure count transitions from below the threshold to equal to or above the threshold.

### Key Entities

- **Module**: Extend existing module model with:
  - `consecutive_failures` (integer, defaults to 0): Tracks consecutive check failures.
  - `last_success` (ISO timestamp, nullable): Tracks when a check last succeeded.

## Assumptions & Risks

### Assumptions

- The operator has configured notification channels if they expect external notifications.
- Active devices are scheduled to run checks periodically, generating health data.

### Risks

- **[Notification Fatigue]** *(likelihood: medium, impact: medium)*: Frequent transient failures might trigger too many alerts. Mitigation: Default threshold to 5 and only notify on state transition (first time threshold is exceeded).

## Implementation Signals

- `MIGRATION` — Add `consecutive_failures` and `last_success` fields to the `modules` table in a new migration.
- `NEW-CONFIG` — Add `BINOCULAR_MODULE_HEALTH_THRESHOLD` setting to `Settings`.
- `NEW-UI` — Display health status badges on the frontend modules management interface.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: An official module with 5 consecutive check failures displays an "Alert" badge in the UI, and clearing it resets the badge immediately on the next success.
- **SC-002** [US2]: Exactly one notification dispatch event is logged or triggered when an official module transitions to failing state.

## Glossary

| Term | Definition |
|------|------------|
| Official Module | Shipped/bundled scraper module provided by default (e.g. Sony, Panasonic, Godox). |
| Consecutive Failures | The number of consecutive check runs for a module that returned a failure result since the last success. |
