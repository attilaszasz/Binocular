---
feature_branch: "00014-manual-on-demand-checks"
created: "2026-05-31"
input: "E010 Manual On-Demand Checks"
spec_type: "product"
spec_maturity: "draft"
epic_id: "E010"
epic_sources: "{PRD:CAP-005}"
---

# Feature Specification: Manual On-Demand Checks

**Feature Branch**: `00014-manual-on-demand-checks`  
**Created**: 2026-05-31  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: draft  
**Epic ID**: E010  
**Epic Sources**: {PRD:CAP-005}  
**Product Document**: specs/prd.md

## Problem Statement

Operators sometimes need to verify firmware status immediately instead of waiting for a scheduled run. Binocular already has inventory, modules, and the shared detection result contract, but without a manual trigger the operator cannot investigate a specific device or refresh all devices on demand. The system needs single-device and bulk manual checks that show stored and detected versions side by side while keeping the UI responsive.

## Scope

### Included

- Trigger an immediate check for one active device from the UI and API.
- Trigger an immediate check for all active devices from the UI and API.
- Display stored current version, detected latest version, status, timestamps, and diagnostics together per device.
- Run bulk checks concurrently without blocking the UI or crashing when one device fails.
- Reuse the E009 check-result contract and existing device/module execution paths.

### Excluded

- Scheduled recurring check orchestration — covered by E011.
- Notification dispatch when updates are found — covered by E012.
- Long-term activity log browsing — covered by E014.
- Changing module authoring or validation rules — covered by E006 and E017.
- Automatically applying firmware updates to hardware — out of product scope.

### Edge Cases & Boundaries

- A device has no usable module association; the manual result is failed with diagnostics.
- One device fails during a bulk check; other checks still complete and return their own statuses.
- A bulk check is requested when no active devices exist; the operator sees an empty result state, not an error.
- A module timeout, scrape failure, or unsafe version comparison remains visible and preserves prior last-success context.
- Archived or deleted devices are not included in all-device checks.

## User Scenarios & Testing

### User Story 1 - Check One Device Now (Priority: P1)

As an operator, I need to run a check for a specific device immediately so I can verify its stored version against the latest detected firmware before deciding whether to update it.

**Why this priority**: Core value proposition — manual checking is unusable without a single-device trigger and result.

**Independent Test**: Trigger a check for one active device and verify the result shows stored version, latest version, status, timestamp, and diagnostics.

**Acceptance Scenarios**:

1. **Given** an active device with a configured module, **When** the operator triggers a manual check for that device, **Then** Binocular runs detection and returns a result for that device only.
2. **Given** the latest detected version is newer than the stored version, **When** the result is displayed, **Then** the operator sees both versions side by side with an update-available status.
3. **Given** the module fails, **When** the result is displayed, **Then** the operator sees a failed status and diagnostic detail without losing prior last-success context.

### User Story 2 - Check All Devices Now (Priority: P1)

As an operator, I need to run checks for all active devices at once so I can refresh my entire inventory without clicking each device individually.

**Why this priority**: Core value proposition — bulk refresh is required for portfolios of many offline devices.

**Independent Test**: Trigger an all-device check for multiple active devices and verify each device returns an independent result.

**Acceptance Scenarios**:

1. **Given** multiple active devices with modules, **When** the operator triggers an all-device check, **Then** Binocular starts checks for all eligible devices.
2. **Given** one device fails and another succeeds, **When** the bulk result is shown, **Then** both outcomes are visible independently.
3. **Given** no active devices are eligible, **When** the operator triggers an all-device check, **Then** Binocular shows an empty result state instead of a crash or misleading success.

### User Story 3 - Keep Manual Checks Responsive (Priority: P2)

As an operator, I need long-running bulk checks to avoid blocking the UI so I can keep using the application while checks complete.

**Why this priority**: Significant usability value — P1 can work synchronously for small inventories, but responsive concurrent execution is needed for the intended 5-50+ device range.

**Independent Test**: Start a bulk check with delayed module responses and verify the UI remains interactive while results resolve.

**Acceptance Scenarios**:

1. **Given** several module checks are slow, **When** a bulk check is running, **Then** the page remains usable and shows in-progress or completed results as available.
2. **Given** a bulk check finishes, **When** the operator reviews results, **Then** stored and latest versions remain aligned with the correct device rows.

## Requirements

### Functional Requirements

- **FR-001**: System MUST allow the operator to trigger a manual check for one active device.
- **FR-002**: System MUST allow the operator to trigger a manual check for all active devices.
- **FR-003**: System MUST return one structured check result per checked device using the E009 contract.
- **FR-004**: System MUST display stored current version and detected latest version side by side for each manual result.
- **FR-005**: System MUST display check status, timestamp, and diagnostic detail for failed or unsafe checks.
- **FR-006**: System MUST run bulk manual checks concurrently enough that one slow or failed device does not block all other results.
- **FR-007**: System MUST exclude archived or deleted devices from all-device manual checks.
- **FR-008**: System MUST preserve visible failure semantics and last-success behavior from the shared detection service.
- **FR-009**: System MUST keep the manual-check UI responsive while checks are running or completing.

### Key Entities

- **CheckResult**: The structured result for one checked device, reused from E009 and shown in manual-check responses.
- **Manual Check Request**: An operator-initiated request targeting either one device or all active devices.
- **Manual Check Batch**: The collection of per-device results produced by an all-device manual check.

## Assumptions & Risks

### Assumptions

- E009 provides a stable service/API result shape for one device check.
- Active devices can be queried from the existing inventory repository.
- The intended inventory size remains modest enough for bounded async concurrency in a single process.
- The UI already has inventory navigation where manual check controls can be added.

### Risks

- **Long-running vendor pages** *(likelihood: medium, impact: medium)*: Bulk checks may take noticeable time; mitigation is concurrent execution and visible in-progress state.
- **Partial failures in bulk mode** *(likelihood: medium, impact: high)*: One failing module could obscure other outcomes; mitigation is independent per-device result reporting.
- **Contract drift from E009** *(likelihood: low, impact: high)*: Manual UI could reinterpret status incorrectly; mitigation is typed client coverage against the shared result shape.

## Implementation Signals

- `NEW-API` — Add manual single-device and all-device check triggers under `/api/v1/checks`.
- `NEW-UI` — Add controls and result views for manual checks in the inventory experience.
- `NEW-ENTITY` — Represent an all-device manual batch as a collection of existing `CheckResult` objects.
- `EXTERNAL-SERVICE` — Continue using modules only through the host-provided scraping client and runner.
- `NEW-WORKER` — Use async concurrent execution for bulk requests without introducing an external worker or broker.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: An operator can trigger a check for one active device and see a result for only that device.
- **SC-002** [US1]: A single-device result presents stored and detected versions side by side with status and diagnostics.
- **SC-003** [US2]: An all-device check returns one independent result per eligible active device.
- **SC-004** [US2]: A failed device in a bulk check does not prevent successful results for other devices from being shown.
- **SC-005** [US3]: During a delayed bulk check, the UI remains interactive and communicates running or completed state.

## Glossary

| Term | Definition |
|------|------------|
| Manual Check | An operator-triggered immediate firmware detection run. |
| Bulk Check | A manual check request that targets all active eligible devices. |
| Eligible Device | An active, non-archived device with enough module configuration to attempt detection. |

## Compliance Check

### Instructions Check Report
**Target**: specs/00014-manual-on-demand-checks/spec.md
**Status**: PASS

| Principle | Verdict | Notes |
|-----------|---------|-------|
| Honest Failure | PASS | Failed manual checks are visible and preserve last-success semantics. |
| Polite by Default | PASS | Manual checks reuse the host-owned module runner and scraping client. |
| Data Ownership & Self-Containment | PASS | No external storage or service dependency is introduced. |
| Least-Privilege & Explicit Trust Boundary | PASS | Existing unsandboxed module boundary remains unchanged and implicit execution is not hidden. |
| Type Safety & Correctness-First | PASS | Requires typed shared CheckResult usage and tests against manual results. |
| Set-and-Forget Reliability | PASS | Partial failures are isolated to each device and do not crash the check flow. |

**Violations**:
None
