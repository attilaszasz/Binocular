# Feature Specification: Core Frontend (UI/UX)

**Feature Branch**: `00003-devices-ui`  
**Created**: 2026-03-01  
**Status**: Draft  
**Input**: User description: "Feature 1.3: Core Frontend (UI/UX) — React + Tailwind scaffold (Responsive layout, Dark mode). Main Dashboard: View grouped devices, showing local vs. web versions. Forms to add/edit devices and map them to device types."  
**Product Document**: docs/binocular-product-brief.md

## User Scenarios & Testing

### User Story 1 - View Device Inventory Dashboard (Priority: P1)

A user opens Binocular in their browser and immediately sees a summary of their tracked devices. The dashboard displays three summary statistics at the top — total devices, devices with updates available, and devices that are up to date. Below the stats, devices are grouped by device type (e.g., "Sony Alpha Bodies", "Sony E-Mount Lenses"). Each device card shows the device name, the locally recorded firmware version side-by-side with the latest detected web version, the last-checked timestamp, and a clear visual indicator when an update is available. Devices that have never been checked display a "Not checked" status rather than a misleading "up to date" state.

**Why this priority**: The dashboard is the primary surface of Binocular — the first thing users see and the place they return to daily. Without it, the system has no user interface. Every other frontend feature builds on this foundation. Viewing the inventory is the single most frequent user action.

**Independent Test**: Can be fully tested by loading the dashboard with a pre-populated backend containing several device types and devices in various states (up to date, update available, never checked) and verifying all data renders correctly, grouped by type, with accurate stats.

**Acceptance Scenarios**:

1. **Given** the backend contains 5 devices across 3 device types with 2 updates available, **When** the user loads the dashboard, **Then** the stats bar shows "Total Devices: 5", "Updates Available: 2", "Up to Date: 3" and devices appear grouped under their respective device type headings.
2. **Given** a device has current version "2.00" and latest seen version "3.00", **When** the user views its card, **Then** both versions are displayed side-by-side with "Local: v2.00" and "Latest: v3.00", and the card has a distinct visual treatment (color/icon) indicating an update is available.
3. **Given** a device has matching current and latest seen versions, **When** the user views its card, **Then** the latest version is displayed in a "healthy" visual style (e.g., green/emerald) and no update indicator is shown.
4. **Given** a device has never been checked (no latest seen version), **When** the user views its card, **Then** the latest version area displays "Not checked" or equivalent, clearly distinguishable from "up to date."
5. **Given** the user is on a smartphone, **When** they view the dashboard, **Then** the stats cards stack vertically, device cards take full width, and version comparisons remain readable without horizontal scrolling.
6. **Given** the dashboard is loading data, **When** the user first sees the page, **Then** skeleton placeholders matching the stats row and device card layout are visible until data arrives (FR-024).

---

### User Story 2 - Switch Between Dark and Light Mode (Priority: P1)

A user prefers to use Binocular in dark mode (the common preference for homelab dashboards). On their first visit, the application respects their operating system's color scheme preference. The user can toggle between dark and light modes using a button in the top header bar. Their choice persists across browser sessions so they don't need to toggle it again each time they open the application.

**Why this priority**: Dark mode is a near-mandatory requirement for self-hosted homelab tools (stated in the product brief and project checklists). It also co-depends on the application scaffold — the theme system must be in place before any UI component can be styled correctly. A broken or missing dark mode makes the application feel unfinished in the target audience's environment.

**Independent Test**: Can be fully tested by toggling the dark/light mode switch, verifying visual styles change across all visible components, refreshing the page, and confirming the chosen mode persists.

**Acceptance Scenarios**:

1. **Given** the user's operating system is set to dark mode and the user has not previously set a preference in Binocular, **When** the application loads for the first time, **Then** the interface renders in dark mode.
2. **Given** the user is in dark mode, **When** they click the theme toggle in the header, **Then** the entire interface transitions to light mode, and the toggle icon changes to reflect the current state.
3. **Given** the user has switched to light mode, **When** they close the browser tab and reopen Binocular, **Then** the interface loads in light mode (their last-chosen preference persists).
4. **Given** the application is in either mode, **When** the user inspects the interface, **Then** all text, icons, borders, and backgrounds maintain sufficient contrast for readability (no invisible text, no washed-out icons).
5. **Given** the user changes their OS color scheme preference, **When** they have NOT previously set a manual preference in Binocular, **Then** the application follows the new OS preference on next load.
6. **Given** the user has previously set light mode, **When** they reload the page, **Then** no dark-mode flash is visible before the interface renders in light mode (FR-005).

---

### User Story 3 - Navigate the Application Shell (Priority: P1)

The user accesses Binocular from either a desktop browser or a mobile device. On desktop, a fixed sidebar shows the application logo and navigation links: Inventory, Activity Logs, Modules, and Settings. On mobile, the sidebar is hidden behind a hamburger menu icon. The user taps the icon to open the sidebar as an overlay, and can close it by tapping a close button or tapping outside the sidebar. A sticky top header displays the current page title and the dark mode toggle. Navigation between sections is instant (client-side routing) with no full page reload.

**Why this priority**: The application shell (sidebar, header, routing) is the structural skeleton that all feature tabs live inside. Without it, there is no way to navigate between sections. Co-prioritized with P1 because the dashboard (US1) cannot exist without a shell to host it.

**Independent Test**: Can be fully tested by clicking each navigation link, verifying the correct content area loads, resizing the browser to mobile width, opening/closing the sidebar, and confirming navigation state persists correctly.

**Acceptance Scenarios**:

1. **Given** the user is on a desktop browser (width ≥ 768px), **When** the page loads, **Then** the sidebar is visible and fixed on the left, and the main content area occupies the remaining space to the right.
2. **Given** the user is on a mobile browser (width < 768px), **When** the page loads, **Then** the sidebar is hidden, a hamburger menu icon appears in the top header, and the main content takes the full width.
3. **Given** the sidebar is hidden on mobile, **When** the user taps the hamburger icon, **Then** the sidebar slides in as an overlay and a close mechanism is available (close button or tap-outside-to-dismiss).
4. **Given** the user is on the Inventory tab, **When** they click "Activity Logs" in the sidebar, **Then** the content area switches to show the Activity Logs view without a full page reload, and the sidebar highlights "Activity Logs" as the active item.
5. **Given** the user navigates to a tab, **When** the content loads, **Then** the sticky header displays the current section name (e.g., "Inventory", "Activity Logs").
6. **Given** the user is navigating the sidebar using only a keyboard, **When** they press Tab, **Then** focus moves sequentially through each navigation item with a visible focus indicator.
7. **Given** a device card action button is focused via keyboard, **When** the user presses Enter, **Then** the action fires identically to a mouse click.

---

### User Story 4 - Confirm a Firmware Update (Priority: P1)

A user has physically updated their Sony A7IV's firmware to version 3.00. On the dashboard, the device card shows "Local: v2.00 → Latest: v3.00" with an update-available indicator. The user clicks the "Confirm" (or "Sync Local") button directly on the device card. The system immediately updates the stored local version to match the latest detected version. The card's visual indicator changes to show the device is now up to date, and the dashboard stats update accordingly (one fewer "Updates Available", one more "Up to Date").

**Why this priority**: The one-click confirmation action is a core value proposition from the product brief. It closes the loop between "update found" and "update applied." The UI for this action must live on the dashboard alongside the device cards — it cannot be deferred without leaving the MVP incomplete. The backend endpoint already exists (Feature 00002 US3).

**Independent Test**: Can be fully tested by setting up a device with mismatched versions, clicking the confirm button on its card, and verifying the card updates to show matching versions, the update indicator disappears, and the stats bar reflects the change.

**Acceptance Scenarios**:

1. **Given** a device card shows "Local: v2.00" and "Latest: v3.00" with an update indicator, **When** the user clicks the confirm/sync button, **Then** the card updates to show both versions as "v3.00", the update indicator disappears, and the card's visual styling changes to the "up to date" treatment.
2. **Given** a device is confirmed, **When** the user views the stats bar, **Then** the "Updates Available" count decreases by 1 and the "Up to Date" count increases by 1.
3. **Given** a device's confirm action fails (e.g., network error), **When** the user clicks the confirm button, **Then** an inline error message appears on or near the device card and the card reverts to its previous state (the version is NOT updated).
4. **Given** the device has never been checked (no latest seen version), **When** the user views the card, **Then** no confirm button is shown — only devices with a detected version mismatch display the confirm action.
5. **Given** a device card shows an update-available confirm button, **When** the user clicks the confirm button and the request is in flight, **Then** the button is visually disabled and a second click has no effect (FR-018).

---

### User Story 5 - Add a New Device (Priority: P2)

A user has just purchased a new Sony 50mm f/1.2 GM lens and wants to add it to their Binocular inventory. From the dashboard, they click an "Add Device" button. A slide-over panel (right-edge drawer) appears, allowing them to enter the device name, select an existing device type from a dropdown, and enter the currently installed firmware version. They submit the form, and the new device immediately appears in the dashboard under the correct device type group. All CRUD forms (add/edit device, create/edit module) use this same slide-over panel pattern for consistency. On mobile, the slide-over panel expands to full screen.

**Why this priority**: Adding devices is how the inventory grows beyond its initial state. While the dashboard (P1) can display existing data, the system cannot be useful without the ability to register new devices. This is P2 rather than P1 because the API already supports device creation, and device data can be seeded through the API directly during initial setup. The frontend form is the natural user-facing layer for this operation.

**Independent Test**: Can be fully tested by clicking "Add Device", filling the form with valid data, submitting, and verifying the device appears in the correct group on the dashboard with accurate attributes.

**Acceptance Scenarios**:

1. **Given** the user is on the dashboard and device types exist, **When** they click "Add Device", **Then** a form opens presenting fields for device name (required), device type (required, dropdown populated from existing types), and current firmware version (required).
2. **Given** the form is open, **When** the user fills in "Sony 50mm f/1.2 GM" as the name, selects "Sony E-Mount Lenses" as the device type, enters "01" as the current version, and submits, **Then** the form closes, the device appears under the "Sony E-Mount Lenses" group, and the "Total Devices" stat increments.
3. **Given** the user submits the form with an empty name, **When** the submission is attempted, **Then** the form displays an inline validation error under the name field without closing (client-side validation).
4. **Given** the user submits a device name that already exists under the same device type, **When** the backend responds with a duplicate name error, **Then** the form displays an inline error message near the name field (e.g., "A device with this name already exists in this type") without losing the user's input.
5. **Given** no device types exist yet, **When** the user clicks "Add Device", **Then** the form still opens but the device type dropdown is empty with guidance text (e.g., "No device types yet — create one first") and the submit button is disabled or the form provides a way to create a device type inline.

---

### User Story 6 - Manage Extension Modules / Device Types (Priority: P2)

A user wants to add, edit, or remove extension modules — each of which defines a device type. From the Modules tab in the sidebar, the user sees a list of installed extension modules, each showing its name, associated firmware source URL, and device count. The user can create a new module (providing a name and firmware source URL), edit an existing module's name, URL, and check frequency, or delete a module. Deleting a module that has devices under its associated device type requires explicit confirmation showing how many devices will be removed. Modules and device types are the same concept in the UI — each extension module corresponds to exactly one device type.

**Why this priority**: Extension modules (device types) are the organizational backbone — you cannot add devices without at least one module. This is P2 because the API for module/device type management already exists and can be driven through API calls, but the Modules tab makes this accessible to all users. Paired with US5 since adding devices requires at least one module/device type to exist.

**Independent Test**: Can be fully tested by navigating to the Modules tab, creating a new module via the form, verifying it appears in the module list and as a group header on the dashboard, editing its name, and attempting to delete one with and without child devices.

**Acceptance Scenarios**:

1. **Given** the user navigates to the Modules tab, **When** the tab loads, **Then** a list of installed extension modules is displayed, each showing its name, firmware source URL, and device count.
2. **Given** the user wants to create a module, **When** they access the module creation form from the Modules tab and enter a name (e.g., "Sony Alpha Bodies") and a firmware source URL, **Then** the new module is persisted, appears in the Modules list, and a corresponding device type group heading appears on the dashboard (with 0 devices initially).
3. **Given** a module "Sony Alpha Bodies" exists, **When** the user opens its edit form and changes the name to "Sony Alpha Camera Bodies", **Then** the Modules list and the dashboard group heading both update to reflect the new name.
4. **Given** a module has 3 devices under its device type, **When** the user initiates deletion, **Then** a confirmation dialog appears warning that 3 devices will also be removed and requiring the user to explicitly confirm before proceeding.
5. **Given** a module has 0 devices, **When** the user initiates deletion, **Then** the module is removed immediately without a cascade confirmation dialog.
6. **Given** the user tries to create a module with a name that already exists, **When** the backend responds with a duplicate error, **Then** the form displays a user-friendly error message without clearing the form.

---

### User Story 7 - Edit and Delete a Device (Priority: P2)

A user wants to update a device's details (correct a name, change the recorded firmware version, add notes) or remove a device they've sold. They can access the edit form from the device card. Deleting a device asks for a simple confirmation before removal.

**Why this priority**: Device editing completes the CRUD lifecycle for the primary entity users interact with. Grouped with other P2 management stories since the dashboard read-only view (P1) is viable without inline editing. The API layer is already in place.

**Independent Test**: Can be fully tested by editing a device's name and notes, verifying the updated card reflects changes, then deleting a device and confirming it disappears from the dashboard and stats update.

**Acceptance Scenarios**:

1. **Given** a device "Sony A7IV" exists, **When** the user opens its edit form and changes the name to "Sony A7 IV (Main)", **Then** the dashboard card displays the updated name after submission.
2. **Given** a device has no notes, **When** the user opens the edit form and adds notes "Primary camera body", **Then** the notes are saved successfully.
3. **Given** the user clicks "Delete" on a device, **When** a confirmation prompt appears, **Then** the user must confirm before the device is removed. Upon confirmation, the device disappears from the dashboard, and the stats bar totals update.

---

### User Story 8 - View Placeholder Tabs (Priority: P3)

The user navigates to Activity Logs or Settings tabs. For this feature, these tabs render meaningful placeholder content that communicates their purpose and indicates they are upcoming features. The Activity Logs tab shows a description of what will appear there. The Settings tab displays a placeholder indicating where notification and scheduling configuration will live.

**Why this priority**: Placeholders prevent "dead ends" in the navigation — users clicking a tab and seeing nothing would question if the app is broken. However, the actual content for these tabs belongs to separate features (Activity Logging, Alerting). Delivering stubs with clear messaging is sufficient for the core frontend MVP. Note: the Modules tab is partially functional (US6) and is not a placeholder.

**Independent Test**: Can be tested by clicking each placeholder tab and verifying a styled placeholder with descriptive text renders correctly in both dark and light mode.

**Acceptance Scenarios**:

1. **Given** the user clicks "Activity Logs" in the sidebar, **When** the tab loads, **Then** a styled placeholder appears with a title, an icon, and a short description of the upcoming feature (e.g., "System execution and scraping history will appear here").
2. **Given** the user clicks "Settings" in the sidebar, **When** the tab loads, **Then** a placeholder appears describing notification and scheduling configuration.
3. **Given** the user is in dark mode, **When** they view any placeholder tab, **Then** the placeholder is styled appropriately for the active theme.

---

### User Story 9 - Handle Empty Inventory State (Priority: P3)

A first-time user opens Binocular with no devices or device types configured. Instead of seeing an empty page, the dashboard displays a welcoming empty state with clear guidance on how to get started — prompting them to create their first device type and add their first device. The stats bar shows zeros. The empty state uses the same responsive breakpoints as the dashboard (single-column on mobile, multi-column on desktop) without layout overflow or awkward spacing.

**Why this priority**: The first-run experience sets the tone for the product. An empty, confusing page will cause users to abandon the tool. However, it's P3 because the core layout and device rendering (P1/P2) are functional without it — empty state is polish that improves adoption but doesn't block core workflows.

**Independent Test**: Can be tested by loading the dashboard with an empty backend and verifying the empty state renders with guidance text and a call-to-action rather than a blank page.

**Acceptance Scenarios**:

1. **Given** the backend has no device types or devices, **When** the user loads the dashboard, **Then** the stats bar shows "Total Devices: 0", "Updates Available: 0", "Up to Date: 0" and a visually distinct empty state section appears below the stats bar with a heading, supportive text, and a getting-started call-to-action button.
2. **Given** the empty state is displayed, **When** the user reads the guidance, **Then** it includes a clear call-to-action to create their first device type (e.g., a button or link to the device type creation form).
3. **Given** the user is on mobile, **When** they view the empty state, **Then** the guidance text and call-to-action render cleanly without overflow or awkward spacing.

---

### Edge Cases

- What happens when the user's network connection drops while the dashboard is open? The interface should display an inline error indicator (e.g., banner or toast) when API calls fail, with a retry affordance, rather than showing a blank screen or stale data without warning.
- What happens when a device name is very long (close to the 200-character limit)? The name should be truncated with an ellipsis on the device card, with the full name visible on hover (tooltip) or in the edit form.
- What happens when the user rapidly clicks the "Confirm Update" button on the same device? The button should be disabled during the pending request, preventing duplicate submissions.
- What happens when a device type has no devices? The group heading should still appear with a "(0 devices)" indicator, or the empty group should be hidden with a note accessible elsewhere — consistent with the device type existing but being unpopulated.
- What happens when the confirm update action fails due to a concurrent deletion (device removed between page load and button click)? The UI should show a "device not found" error and remove the stale card from the display.
- What happens when the user opens the add/edit form and the API is unreachable? The form should display an error state when it cannot load prerequisite data (e.g., device type list) and should not let the user submit if submission will fail.
- What happens when the user resizes their browser from desktop to mobile width while the sidebar is open? The sidebar MUST follow the breakpoint rules (FR-001): at < 768px it collapses to the off-canvas mobile pattern; at ≥ 768px it remains fixed. No animation timing requirement — instant CSS-driven transition is acceptable.
- What happens when the browser's `localStorage` is unavailable or full (e.g., private browsing restrictions)? The dark mode toggle should fall back to in-memory state (defaulting to OS preference) and continue functioning without errors, just without persistence across sessions.

## Requirements

### Functional Requirements

- **FR-001**: System MUST render a responsive application shell with a fixed sidebar on desktop (≥ 768px) and a collapsible off-canvas sidebar on mobile (< 768px), matching the layout defined in the [design mockup](../../docs/mockup.jsx).
- **FR-002**: System MUST provide a dark mode and light mode toggle in the top header bar that switches the entire interface between themes.
- **FR-003**: System MUST detect the user's OS color scheme preference (`prefers-color-scheme`) and apply it as the default theme on first visit when no stored preference exists.
- **FR-004**: System MUST persist the user's theme choice in browser local storage so it survives page refreshes and browser restarts. If `localStorage` is unavailable (e.g., private browsing restrictions), the system MUST fall back to in-memory state defaulting to the OS preference and continue functioning without errors — persistence is lost but the toggle remains operational.
- **FR-005**: System MUST apply the stored theme preference before the first visible render to prevent a flash of the incorrect theme.
- **FR-006**: System MUST render a sidebar navigation with four items — Inventory, Activity Logs, Modules, Settings — using client-side routing that switches content without full page reloads.
- **FR-007**: System MUST display a sticky top header bar showing the current section title and the theme toggle, as shown in the [design mockup](../../docs/mockup.jsx).
- **FR-008**: System MUST display an inventory dashboard as the default landing view containing: (a) a summary stats row with total devices, updates available, and up-to-date counts; (b) device cards grouped by device type. Device type groups with zero devices MUST still display their group heading with a "(0 devices)" indicator.
- **FR-009**: System MUST render each device as a card showing: device name (truncated with ellipsis if it exceeds the card width, with the full name visible on hover via tooltip), last-checked timestamp (displayed as a relative time such as "2 hours ago" with the absolute timestamp visible on hover via tooltip), locally recorded firmware version, latest detected firmware version, and a visual status indicator for the tri-state: "update available" (visually prominent, using a distinct color and icon), "up to date" (neutral/positive), or "never checked" (distinct from up to date).
- **FR-010**: System MUST provide a "Confirm Update" (or "Sync Local") action button on each device card that has an update available. Clicking it MUST call the backend confirm endpoint and update the card and stats in place without a page refresh.
- **FR-011**: System MUST NOT display the confirm action on devices that have never been checked or that are already up to date.
- **FR-012**: System MUST provide an "Add Device" form accessible from the dashboard that collects: device name (required), device type (required, selected from existing types), and current firmware version (required), consistent with the backend API contract.
- **FR-013**: System MUST provide an "Edit Device" form accessible from each device card that allows modification of: device name, current firmware version, and notes.
- **FR-014**: System MUST provide a Modules tab accessible from the sidebar that lists installed extension modules (each defining a device type) and provides forms for creating and editing modules that collect: name (required), firmware source URL (required), and check frequency (optional, default: 360 minutes per the API contract). The form MUST also display a disabled/read-only field for extension module file association with a note indicating this capability is coming in a future release (Feature 2.3). The `extension_module_id` is sent as null until advanced module management is available.
- **FR-015**: System MUST provide a delete action for devices and device types. Deleting a device type with child devices MUST present a confirmation dialog showing the count of devices that will also be removed before proceeding.
- **FR-016**: System MUST validate form inputs on the client side before submission: non-empty required fields, trimmed whitespace, and maximum length enforcement (names ≤ 200 characters, firmware versions ≤ 100 characters, URLs ≤ 2048 characters, notes ≤ 2000 characters) consistent with backend validation rules.
- **FR-017**: System MUST display user-friendly error messages when API requests fail, mapping server-reported error conditions (e.g., duplicate name, resource not found, validation failure, cascade conflict, missing version data, internal server error) to human-readable descriptions shown inline near the relevant UI element.
- **FR-018**: System MUST disable form submit buttons and action buttons during pending API requests to prevent duplicate submissions.
- **FR-019**: System MUST render placeholder views for Activity Logs and Settings tabs that communicate the purpose of each section and indicate they are part of upcoming features. The Modules tab is partially functional (FR-014) and is not a placeholder.
- **FR-020**: System MUST render a contextual empty state on the dashboard when no device types or devices exist, with guidance text and a call-to-action to create the first device type.
- **FR-021**: System MUST update the statistics bar (total devices, updates available, up to date) reactively whenever a device is added, edited, deleted, or confirmed — without requiring a manual page refresh.
- **FR-022**: System MUST ensure all interactive elements (buttons, links, form controls) are accessible via keyboard navigation (Tab, Enter, Space) and have visible focus indicators.
- **FR-023**: System MUST provide a visible "Refresh" button on the dashboard that re-fetches all device and device type data from the backend API. The dashboard does NOT automatically poll for updates — data refreshes only in response to user-initiated actions (confirm, add, edit, delete) or an explicit Refresh click.
- **FR-024**: System MUST display skeleton placeholder screens (matching the layout structure: stats row skeletons, device card skeletons) during the initial dashboard data fetch and when switching to the Modules tab. Skeleton screens are replaced by actual content once data arrives. Inline spinners are used for individual action buttons (covered by FR-018).

### Key Entities

- **Device Type (display)**: Group heading in the inventory. Displayed attributes: name, device count. Used as a filter/grouping key for devices. Relationship: contains zero or more Devices.
- **Device (display)**: Individual card in the inventory. Displayed attributes: name, current firmware version, latest seen version, last-checked timestamp, update status (tri-state). Editable attributes: name, current version, notes. Actions: confirm update, edit, delete. Relationship: belongs to exactly one Device Type.
- **Dashboard Stats**: Computed summary metrics derived from device data: total device count, count with updates available, count up to date. Updated reactively as device state changes.
- **Theme Preference**: User's dark/light mode choice. Stored locally in the browser. Defaults to OS preference when no explicit choice has been made.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can open Binocular and see their full device inventory — grouped by type with firmware versions and status indicators — within 3 seconds of page load when the server and client are on the same local network (≤ 5ms latency, ≥ 10 Mbps throughput).
- **SC-002**: Users can add a new device to their inventory through the UI form and see it appear in the correct group on the dashboard within a single interaction session (no page refresh required).
- **SC-003**: Users can confirm a firmware update with a single click on the device card and see the card and stats update immediately — the round-trip from button press to updated UI completes in under 2 seconds.
- **SC-004**: The interface is fully usable on mobile devices (screen width 320px and above) — all content is readable, all actions are reachable, and no horizontal scrolling is required to perform core tasks.
- **SC-005**: Dark mode and light mode are both fully styled with no broken elements, invisible text, or missing backgrounds — switching between modes renders a complete, polished interface.
- **SC-006**: A first-time user with an empty inventory sees a helpful empty state with guidance rather than a blank or confusing page — at least one call-to-action directs them to create their first device type.
- **SC-007**: All form submissions provide immediate inline feedback — validation errors are visible within 1 second of submission attempt, and server-side errors are displayed as user-friendly messages rather than raw error codes.
- **SC-008**: Navigation between all tabs is instant (< 300ms perceived transition) with no full page reloads, and the currently active tab is visually indicated in the sidebar.

## Dependencies & Assumptions

- **Depends on Feature 00002 (Inventory API)**: The frontend consumes the CRUD and confirm endpoints defined in the Inventory API specification. All device types, devices, and confirm actions operate through these API endpoints.
- **Depends on Feature 00001 (Database Schema & Models)**: Indirectly, through the API layer. The frontend does not access the database directly.
- Assumes the backend serves the frontend as static files through the backend web server (single-port architecture as defined in project instructions).
- Assumes single-user environment — no concurrent multi-user state conflicts to manage in the UI.
- Assumes the backend API is the source of truth for all data. The frontend does not maintain a local database or offline cache in V1. Data freshness follows a manual-refresh model — the dashboard fetches data on load and updates only via user-initiated actions or an explicit Refresh button. No automatic background polling.
- The Activity Logs and Settings tabs are delivered as placeholders only. Their full functionality belongs to separate features (Feature 4.1 and Feature 4.2 respectively). The Modules tab is partially functional — it provides basic extension module / device type CRUD but defers advanced module management (upload, enable/disable, detailed configuration) to Feature 2.3.
- Filter and sort controls are explicitly deferred from V1. The grouped-by-type dashboard display is sufficient for the expected inventory size (5–50 devices). The backend API supports filtering/sorting for future frontend use.

## Compliance Check

**Result**: PASS — all project instruction principles satisfied or correctly out of scope.

### Principle-by-Principle Audit

#### I. Self-Contained Deployment — **PASS**
No external services, databases, or additional ports introduced. The spec explicitly states single-port architecture through the backend web server. Theme persistence uses browser `localStorage` — no server-side session store needed.

#### II. Extension-First Architecture — **PASS**
No vendor-specific logic is embedded in the frontend. Device types and devices are treated generically throughout. Vendor names ("Sony Alpha Bodies") appear only as illustrative examples in acceptance scenarios, not as hard-coded UI logic. The Modules tab is partially functional (US6/FR-014) — providing basic extension module / device type CRUD — with advanced module management deferred to Feature 2.3.

#### III. Responsible Scraping — **N/A** (correctly out of scope)
This spec covers the frontend UI layer only. No HTTP scraping occurs from the browser client. All data is consumed from the backend API, which is responsible for enforcing scraping policies.

#### IV. Type Safety & Validation — **PASS**
FR-016 enforces client-side validation consistent with backend constraints. FR-017 maps server-side validation errors to user-friendly messages. Frontend language choice (TypeScript) is an appropriate plan-phase decision.

#### V. Test-First Development — **PASS**
Each user story includes an "Independent Test" section and Given/When/Then acceptance scenarios. Edge cases are enumerated. Frontend testing framework selection is deferred to the plan phase.

#### VI. Technology Stack — **PASS**
Aligned with fixed stack: React (client-side routing, component architecture), Tailwind CSS (responsive breakpoints, dark mode), Vite (implicit via SPA build). No off-stack technologies introduced.

#### VII. Development Workflow — **PASS**
Testable acceptance criteria for every user story. FR-022 addresses keyboard accessibility. OpenAPI documentation inherited from Feature 00002 dependency.

| Principle | Verdict | Notes |
|---|---|---|
| I. Self-Contained Deployment | PASS | Single-port, no external deps |
| II. Extension-First Architecture | PASS | Generic device handling, no vendor logic |
| III. Responsible Scraping | N/A | Frontend only, no scraping |
| IV. Type Safety & Validation | PASS | Client-side validation, error mapping |
| V. Test-First Development | PASS | Independent tests, GWT scenarios |
| VI. Technology Stack | PASS | React + Tailwind + Vite aligned |
| VII. Development Workflow | PASS | Accessible, testable, documented |

**Audited**: 2026-03-01 | **Spec Version**: Draft | **Instructions Version**: 1.0.0
