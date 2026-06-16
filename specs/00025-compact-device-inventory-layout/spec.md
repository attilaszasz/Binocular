---
feature_branch: "00025-compact-device-inventory-layout"
created: "2026-06-16"
input: "E024"
spec_type: "product"
spec_maturity: "draft"
epic_id: "E024"
epic_sources: "{PRD:CAP-001}"
---

# Feature Specification: Compact Device Inventory Layout

**Feature Branch**: `00025-compact-device-inventory-layout`  
**Created**: 2026-06-16  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: draft  
**Epic ID**: E024  
**Epic Sources**: {PRD:CAP-001}  
**Product Document**: specs/prd.md

## Problem Statement *(mandatory)*

The Inventory page displays a module-derived `device_type` badge on each device card. Because some modules support multiple device types (such as both cameras and lenses), displaying a single static type from the module on every linked device is incorrect and confusing for operators. In addition, the current device cards have excessive padding and spacing, which reduces the number of items that can be viewed on screen simultaneously. This feature removes the misleading badge and establishes a compact, highly dense layout for the device cards.

## Scope *(mandatory)*

### Included

- Removal of the `<Badge variant="secondary">{device.device_type}</Badge>` element from the device card layout on the Inventory page.
- Adjusting CSS classes (margins, paddings, gap spacing, and text sizes) in `device-card.tsx` to achieve a more compact layout.
- Restructuring element alignment within the card layout to maximize information density.
- Verification that all frontend test suites compile and pass.

### Excluded

- Database schema changes (no `device_type` column is added to the `devices` table).
- Modifying `SUPPORTED_DEVICE_TYPE` on modules (the backend contract is preserved).
- Removing the `device_type` select list from the "Add/Edit Device" form (the module dropdown itself is not removed, but we remove the type display on the cards).

### Edge Cases & Boundaries

- **Long Device Names**: Very long names should wrap or truncate gracefully in the compacted layout without overlapping other card elements.
- **Mobile Responsiveness**: The compact card design must adapt cleanly to small viewports.

## User Scenarios & Testing *(mandatory for product specs only)*

### User Story 1 - Remove Misleading Type Badge (Priority: P1)

As an operator, I want the device cards to not show a misleading module-level device type badge, so that I don't see "camera" labeled on my lenses or other incorrect categories.

**Why this priority**: Core correctness requirement to resolve the user's issue.

**Independent Test**: Verify that the device cards rendered on the Inventory page no longer display a `device_type` badge.

**Acceptance Scenarios**:

1. **Given** a device of model "FE 24-70mm" linked to a module with `SUPPORTED_DEVICE_TYPE = "camera"`, **When** the operator views the Inventory page, **Then** the device card does not display a "camera" badge.

### User Story 2 - Compact Device Cards Layout (Priority: P2)

As an operator, I want the device cards to be more compact, so that I can see more devices on my screen without extensive scrolling.

**Why this priority**: Enhances usability for large inventories of devices.

**Independent Test**: Verify that the device cards use tighter paddings (e.g. `p-4` or `p-3`) and smaller text for version display.

**Acceptance Scenarios**:

1. **Given** the Inventory page is rendered, **When** the cards are viewed on desktop or mobile, **Then** the spacing between text blocks and button controls is compact, and the cards fit neatly in the layout grid.

## Requirements *(mandatory)*

### Functional Requirements *(product specs only)*

- **FR-001**: System MUST exclude the `device_type` badge from the device card layout on the Inventory page.
- **FR-002**: System MUST render device cards with optimized compact styling (reduced padding, tighter margins, and aligned elements) to increase information density.

## Assumptions & Risks *(mandatory)*

### Assumptions

- Users have diverse display sizes, but a compact grid layout fits both desktop and mobile viewports.
- The `device_type` property remains returned by the API but is simply ignored/not displayed on the card component.
- The user is satisfied with identifying the type of device from the device model and name.

### Risks

- **Long Device Names** *(likelihood: medium, impact: low)*: Long names could overflow or wrap awkwardly. Mitigation: ensure text truncation or wrapping is handled gracefully in CSS.

## Implementation Signals *(mandatory)*

- `NEW-UI` — modify `device-card.tsx` to remove the badge and compact the card layout classes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** [US1]: The device card component does not render any `device_type` badge.
- **SC-002** [US2]: Device cards use smaller paddings and spacing (e.g., `p-4` or `p-3` container padding instead of `p-6`).

## Compliance Check

### Instructions Check Report
**Target**: specs/00025-compact-device-inventory-layout/spec.md
**Status**: PASS

| Principle | Verdict | Notes |
|-----------|---------|-------|
| I. Honest Failure | N/A | UI layout change only. |
| II. Polite by Default | N/A | UI layout change only. |
| III. Data Ownership & Self-Containment | PASS | No new storage, external dependencies, or telemetry. |
| IV. Least-Privilege & Explicit Trust Boundary | PASS | No changes to runtime privilege boundaries. |
| V. Type Safety & Correctness-First | PASS | Requires all frontend test suites to pass cleanly. |
| VI. Set-and-Forget Reliability | PASS | No impact on persistence or process stability. |
| VII. Agent Output Style | PASS | Template structure strictly followed. |

**Violations**:
None.
