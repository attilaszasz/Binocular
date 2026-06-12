---
feature_branch: "00022-compact-inventory-subtitle"
created: "2026-06-12"
input: "On the inventory page, the 'Devices', 'Updates Available', 'Checked' count panels take up too much space. They should be one single, small subtitle under the 'Inventory' title."
spec_type: "product"
spec_maturity: "draft"
---

# Feature Specification: Compact Inventory Subtitle

**Feature Branch**: `00022-compact-inventory-subtitle`  
**Created**: 2026-06-12  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: draft  

## Problem Statement

Currently, the Inventory Page includes large, separate count panels for "Devices", "Updates Available", and "Checked" states, taking up significant screen real estate. This reduces visibility of the actual device list on smaller resolutions. Moving these metrics into a compact subtitle under the page title saves vertical space and improves readability.

## Scope

### Included

- Displaying total devices, updates available count, and checked devices count in a single, compact line under the "Inventory" header.
- Conditionally showing the subtitle only when devices exist (`totalDevices > 0`) and the inventory page is not loading.
- Formatting the subtitle with clear separators (e.g., bullets or vertical bars) and clean styling (muted text color, small font size).
- Preserving all count logic (using existing variables/hooks in `inventory.tsx`).
- Removing the three separate `StatCard` panels from the inventory page.

### Excluded

- Modifying backend models or API responses for these statistics.
- Changing metadata or checks logic.

### Edge Cases & Boundaries

- Proper pluralization of counts (e.g., "1 device" vs "2 devices", "1 update available" vs "2 updates available").
- Visibility during loading, error, and empty states.

## User Scenarios & Testing

### User Story 1 - Compact Inventory Subtitle (Priority: P1)

As an operator viewing the inventory page, I want to see the key stats (total devices, update availability, and checking coverage) as a single clean subtitle, so that I have more screen space to view my devices.

**Why this priority**: Core requirement of the user request to save space.

**Independent Test**: Verify that the separate panels are gone and a subtitle text like "5 devices • 1 update available • 4 of 5 checked" is shown directly under the Inventory title.

**Acceptance Scenarios**:

1. **Given** a user navigates to the Inventory page with 5 devices (1 update available, 4 checked), **When** the page loads, **Then** they see a subtitle below "Inventory" containing "5 devices • 1 update available • 4 of 5 checked", and no separate stat cards.
2. **Given** a user has no devices, **When** they view the Inventory page, **Then** they do not see any subtitle, only the empty state.

## Requirements

### Functional Requirements

- **FR-001**: System MUST render a single, small subtitle text below the "Inventory" header on the inventory page.
- **FR-002**: Subtitle MUST display: total devices, number of updates available, and number of checked devices.
- **FR-003**: Subtitle MUST be hidden when the device inventory is empty or loading.
- **FR-004**: StatCard component panels for "Devices", "Updates Available", and "Checked" MUST be removed from the inventory page.

### Key Entities

- **Device**: Represents a physical or software device tracked by the system (ID, name, has_update, last_checked).

## Assumptions & Risks

### Assumptions

- No other pages or components rely on the layout of these specific stat panels on the inventory page.

### Risks

- **[None]** *(likelihood: low, impact: low)*: Simple frontend UI reorganization.

## Implementation Signals

- `NEW-UI` — Adjust the page header layout and remove the `StatCard` grid container in [inventory.tsx](file:///Users/attila/git/Binocular/frontend/src/pages/inventory.tsx).

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: The inventory stats are presented as a single-line subtitle below the header, saving approximately 100-150px of vertical height compared to the card-based layout.
