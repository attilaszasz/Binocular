# Research: Core Frontend UI/UX

**Feature**: 00003-devices-ui  
**Date**: 2026-03-01  
**Purpose**: Inform user story priorities, acceptance criteria, and edge case identification for the core frontend specification.

**Context**: Domain best practices for Binocular's core frontend — a React + Tailwind CSS device inventory dashboard for homelab enthusiasts. Focus is on responsive layout, dark mode, dashboard information architecture, form UX, real-time feedback, accessibility, and empty states.

## 1. Dashboard Information Architecture

### Grouped Inventory with Status Indicators

- **Key findings**: Inventory dashboards for heterogeneous device fleets converge on a **grouped-by-category** layout with summary statistics at the top. The pattern is: global stats → category groups → individual item cards. This matches how users mentally model their inventory ("my camera bodies", "my lenses", "my network gear") and is validated by tools like Uptime Kuma (groups by tag), Portainer (groups by stack), and UniFi Console (groups by device type).
- **Visual hierarchy**: The most effective dashboards lead with **action-relevant information** — "what needs my attention?" — before exhaustive detail. The stats row (Total Devices, Updates Available, Up to Date) serves as the **executive summary** that answers this immediately.
- **Status indicator patterns**: The dominant pattern for update/health status is a **tri-state model**:
  1. **Up to date** (green/emerald) — no action needed.
  2. **Update available** (rose/amber) — action recommended.
  3. **Unknown/Never checked** (gray/muted) — data not yet available.
  A fourth transient state, **Checking** (spinner/pulse animation), is essential for feedback during operations.
- **Card vs. table**: For inventories of 5–50 items, **cards** outperform tables for scanability because each device has rich status data (two version numbers, last checked time, action buttons). Tables are superior only when comparing many identical columns across 50+ items. The mockup's card layout is well-chosen for the target scale.
- **Group collapsibility**: When groups grow beyond ~5 items, collapsible sections significantly improve scanability. Users with 30+ devices need to focus on a single group at a time without scrolling through everything.

### Relevance to Binocular

The existing mockup already demonstrates strong information architecture: stats → grouped cards → version comparison. The main gaps are: (1) no explicit "never checked" state, (2) no collapsible groups, (3) no sort/filter options.

### Specific Recommendations

- **REC-1.1**: Implement a tri-state + transient model for device status: `up_to_date`, `update_available`, `never_checked`, and `checking` (transient). Each state should have distinct visual treatment (color + icon + label).
- **REC-1.2**: Make device type groups collapsible with expand/collapse toggle. Persist collapse state in `localStorage` so users' layout preferences survive page reloads.
- **REC-1.3**: Add a filter/sort control bar below stats: filter by status (`All | Updates Available | Up to Date`), sort by name or last checked date. This is especially valuable at 20+ devices.
- **REC-1.4**: Show `device_count` and `updates_available_count` per group header so users can triage at the group level without scanning all cards.
- **REC-1.5**: Place the "Updates Available" stat card in the most visually prominent position (leftmost or use a stronger highlight) — this is the primary call-to-action driver.

---

## 2. Responsive Layout Patterns

### Sidebar Navigation for Mobile vs. Desktop

- **Key findings**: Self-hosted tool UIs have converged on a **collapsible sidebar** pattern: persistent on desktop (≥768px), off-canvas drawer on mobile. This is the dominant layout in Portainer, Grafana, Home Assistant, Uptime Kuma, Pi-hole, and UniFi Console. The existing mockup follows this pattern correctly.
- **Mobile sidebar trigger**: A hamburger menu (☰) in the top-left of the header is the standard trigger. On tap, the sidebar slides in from the left with an overlay dimming the main content. Tapping the overlay or a close (✕) button dismisses it.
- **Bottom navigation alternative**: Some mobile-first apps (like Home Assistant) use a bottom tab bar for primary navigation on small screens. However, for an app with only 4 tabs (Inventory, Logs, Modules, Settings), a bottom bar can feel sparse and wastes vertical space that's valuable for the device cards. The sidebar-drawer approach is more space-efficient and consistent with the desktop experience.
- **Breakpoint strategy**: The standard Tailwind breakpoints (`sm: 640px`, `md: 768px`, `lg: 1024px`, `xl: 1280px`) work well. Key responsive transitions:
  - **< md (768px)**: Sidebar hidden, hamburger menu shown, single-column card layout, stats cards stack vertically.
  - **md–lg**: Sidebar visible, two-column card grid, horizontal stats.
  - **≥ lg (1024px)**: Full layout, two-column card grid with comfortable spacing.
- **Touch targets**: On mobile, all interactive elements (buttons, nav items, card actions) must be minimum 44×44px per WCAG 2.5.8 / Apple HIG guidelines. The mockup's button sizes appear adequate but should be verified.
- **Viewport height management**: Sticky header + scrollable content is the correct pattern (as in the mockup). The sidebar should be `position: fixed` and full-height. On iOS Safari, use `100dvh` instead of `100vh` to handle the dynamic address bar.

### Relevance to Binocular

The mockup already implements the collapsible sidebar correctly. The main gap is verification of touch target sizes and mobile card layout for the version comparison section, which becomes cramped on narrow screens.

### Specific Recommendations

- **REC-2.1**: On screens < 640px (`sm`), stack the version comparison section (Local → Latest) vertically instead of horizontally to prevent text truncation on the version numbers.
- **REC-2.2**: Ensure all buttons and tappable areas are ≥ 44×44px on mobile. Particularly the per-device "Check" icon button (currently just a 16px icon with padding) and "Sync Local" button.
- **REC-2.3**: Use `100dvh` for mobile viewport height to account for iOS Safari's dynamic toolbar. Apply via Tailwind's `h-dvh` utility (available in Tailwind v3.4+).
- **REC-2.4**: Add scroll-to-top behavior when switching tabs on mobile — the user should always see the tab header, not be stranded mid-scroll.
- **REC-2.5**: The mobile menu overlay should trap focus within the sidebar for keyboard/screen reader accessibility (see §6 for ARIA details).

---

## 3. Dark Mode Implementation

### System Preference Detection and Toggle Persistence

- **Key findings**: The gold standard for dark mode is a **three-state model**: `system` (default), `light`, `dark`. The app respects `prefers-color-scheme` media query out of the box, and the user can override with an explicit toggle. The override is persisted in `localStorage`.
- **Implementation pattern (Tailwind CSS)**:
  1. Set `darkMode: 'class'` in `tailwind.config.js`.
  2. On app load: check `localStorage` for saved preference. If none, read `window.matchMedia('(prefers-color-scheme: dark)')`. Apply `dark` class to `<html>`.
  3. Listen for `matchMedia` changes (user switches OS theme mid-session) — only act on this event if the user hasn't set an explicit override.
  4. Toggle saves preference to `localStorage` and updates the `<html>` class immediately.
- **Flash of incorrect theme (FOIT)**: This is the #1 dark-mode UX pitfall. If the dark class is applied after React hydrates, users see a white flash on page load. The fix is a **blocking inline script in the `<head>`** of `index.html` that reads `localStorage` and applies the `dark` class before any rendering occurs. This is the canonical approach used by Next.js, Docusaurus, and Tailwind UI.

### Color Contrast and Palette

- **Key findings**: Dark mode is not "inverted light mode." Best practices from Material Design 3 and Tailwind UI:
  - Background layers should create depth: base (`slate-950`) → surface (`slate-900`) → elevated (`slate-800`). The mockup uses this correctly.
  - Text should use `slate-100` to `slate-400` for hierarchy, never pure white (`#fff`) on dark backgrounds — the contrast is too harsh and causes eye strain. The mockup correctly uses `text-white` sparingly (only for headings).
  - Primary accent colors (indigo in the mockup) should be **desaturated** slightly in dark mode for comfortable viewing. Tailwind's `indigo-400` in dark / `indigo-600` in light is a good pairing.
  - Status colors must meet WCAG AA contrast on dark backgrounds: `emerald-400` on `slate-900` (4.6:1 — passes), `rose-400` on `slate-900` (4.8:1 — passes), `amber-400` on `slate-900` (varies — verify).
- **Homelab context**: Dark mode is the **expected default** for self-hosted tools. Many homelab users check dashboards in dimly lit server rooms/closets. Default to dark, offer light as the alternative.

### Relevance to Binocular

The mockup defaults to `isDarkMode: true`, which is correct for the audience. The color choices are well-aligned with best practices. The main gap is the FOIT prevention script and the three-state model (system/light/dark).

### Specific Recommendations

- **REC-3.1**: Default to `system` preference (which will resolve to dark for most homelab users) rather than hardcoding dark. Persist explicit overrides in `localStorage` under a key like `binocular-theme`.
- **REC-3.2**: Add a blocking `<script>` in `index.html` `<head>` that reads `localStorage` and applies the `dark` class before React mounts, preventing theme flash.
- **REC-3.3**: Verify WCAG AA contrast ratios (≥ 4.5:1 for normal text, ≥ 3:1 for large text) for all status colors against their background surfaces in both light and dark modes. Particular scrutiny on `amber-400` on dark and `slate-400` text on `slate-900` backgrounds.
- **REC-3.4**: Consider a three-option toggle (Sun / Monitor / Moon icons) in the header instead of a simple two-state toggle. This is becoming standard (GitHub, VS Code, Tailwind UI site).
- **REC-3.5**: Ensure form inputs, modals, and dropdown menus have properly themed borders, backgrounds, and focus rings in dark mode — these are commonly missed.

---

## 4. Form UX for Inventory Management

### Adding/Editing Devices with Parent-Child Relationships

- **Key findings**: Forms for creating child resources (devices) that belong to a parent (device type) should:
  - **Pre-select the parent** when launched from within a group context (e.g., "Add Device" clicked inside the "Sony Alpha Bodies" group should pre-fill the device type).
  - **Allow parent creation inline** — a "Create New Device Type" option in the device type dropdown prevents the user from abandoning the add-device flow to go create a type first. This is the pattern used by Jira (create project inline), GitHub (create label inline), and Notion.
  - **Minimize required fields**: For a quick-add flow, only `name` and `device_type` should be required. `firmware_url`, `notes`, `local_version` can be optional and editable later.

### Modal vs. Inline vs. Dedicated Page

- **Key findings**: For Binocular's form complexity (3–6 fields per device, 2–3 per device type), a **slide-over panel or modal** is the best fit:
  - **Modal/slide-over**: Keeps context (the user can still see the dashboard behind the overlay). Works for both "add" and "edit" flows. Best for 3–8 field forms. Dominant pattern in Portainer, Uptime Kuma, Linear, and most SaaS tools.
  - **Inline editing**: Best for single-field edits (renaming). Awkward for multi-field forms because it disrupts the card layout. Could be offered as a secondary pattern for quick edits (e.g., click device name to rename inline).
  - **Dedicated page**: Overkill for this form complexity. Loses dashboard context and adds unnecessary navigation.
- **Form validation**: Validate on submit (not on each keystroke) with field-level error messages. Highlight invalid fields with a red border and inline error text below the field. Preserve user input on validation failure — never clear the form.
- **Edit flow**: The "edit device" form should **pre-populate all fields** from the existing resource. Use the same form component for both add and edit, toggling between `POST` and `PATCH` behavior.

### Device Type Management

- **Key findings**: Device types are a simpler form (name + optional description/icon). They can be managed via:
  - A dedicated section accessible from Settings or a "Manage Types" link near the group headers.
  - Inline creation from the device form's type dropdown (recommended for flow efficiency).
  - The Modules tab could show associated device types since modules map to types.

### Relevance to Binocular

The mockup shows an "Add Device" button but doesn't detail the form. The spec needs to define the form fields, validation rules, and whether to use modals or slide-overs.

### Specific Recommendations

- **REC-4.1**: Use a **slide-over panel** (right-side drawer) for add/edit device and device type forms. This preserves dashboard context and works well on both desktop and mobile (full-screen on mobile).
- **REC-4.2**: Device form fields: `Name` (required, text), `Device Type` (required, dropdown with "Create new…" option), `Firmware URL` (optional, URL input), `Current Version` (optional, text), `Notes` (optional, textarea). Keep it lean for V1.
- **REC-4.3**: Pre-select device type when "Add Device" is triggered from within a device type group.
- **REC-4.4**: Implement **client-side validation** mirroring the API's rules: non-empty trimmed name (≤ 200 chars), valid URL format if provided. Show inline field errors on submit.
- **REC-4.5**: Provide "edit" access directly from device cards (e.g., a pencil icon or three-dot menu) to avoid forcing the user back to a separate management page.
- **REC-4.6**: After successful form submission, close the panel and update the dashboard in-place (optimistic or after response) — do not require a full page reload.

---

## 5. Real-Time Feedback Patterns

### Loading States for Firmware Checks

- **Key findings**: Firmware checks are inherently asynchronous operations (network scraping) that can take 1–10+ seconds. The UX must account for this:
  - **Immediate visual feedback**: The button should enter a "loading" state (spinner replacing the icon, disabled state) within 100ms of click. The mockup's `animate-spin` on the RefreshCw icon is the correct pattern.
  - **Per-device granularity**: Each device card should independently show its checking state. When "Check All" is triggered, all cards show spinners simultaneously. As each device completes, its spinner resolves independently (not all-at-once after the slowest one).
  - **Progress indication**: For "Check All" with many devices, consider a progress indicator: "Checking 3 of 12…" or a progress bar in the header area.

### Optimistic Updates vs. Server-Confirmed Updates

- **Key findings**: For **read-heavy, write-light** operations like Binocular:
  - **Confirm Update (Sync Local)**: This is a write operation — use **optimistic update**. Immediately update the UI (change local version, remove update badge), then send the PATCH/POST. If it fails, revert and show an error toast. This provides instant responsiveness. The operation is low-risk because it only changes the stored local version.
  - **Firmware Check**: This is a read-from-external operation — **server-confirmed** is the correct approach. Show a spinner/loading state, wait for the actual result, then update. There's no value in optimistically guessing a firmware version.
  - **Add/Edit/Delete Device**: Use **optimistic update with rollback** for deletes (visually remove immediately, rollback on error). For adds/edits, wait for server confirmation because the server generates the ID and validates uniqueness.

### Polling vs. WebSockets for Long-Running Operations

- **Key findings**: For a single-user self-hosted tool:
  - **Short-polling** (periodic fetch) is the simplest and most robust. Poll every 2–3 seconds while a check is in progress, stop polling when complete. This avoids WebSocket complexity and connection management.
  - **WebSockets**: Overkill for single-user. Adds reconnection logic, server-side connection management, and complicates the single-port architecture.
  - **Server-Sent Events (SSE)**: A middle ground — simpler than WebSockets, natively supported by browsers, unidirectional (server→client). Good fit if "Check All" needs live per-device progress updates. FastAPI supports SSE via `StreamingResponse`.
  - **Recommendation for V1**: Use short-polling for check status. Consider SSE as a V2 enhancement if users request more granular progress.

### Toast Notifications for Action Feedback

- **Key findings**: Transient success/error feedback should use **toast notifications** (auto-dismissing snackbars). Placement: bottom-right or top-right. Auto-dismiss after 4–5 seconds for success, persistent until dismissed for errors. Use distinct colors: green for success, red for error, amber for warning.

### Relevance to Binocular

The mockup simulates checking with `setTimeout` but doesn't show error states, partial completion for bulk checks, or toast feedback. The spec needs to define these patterns.

### Specific Recommendations

- **REC-5.1**: Per-device spinner with independent completion. When "Check All" runs, each device card's spinner resolves as its individual check completes, not waiting for the entire batch.
- **REC-5.2**: Optimistic update for "Sync Local" (Confirm Update). Immediately reflect the change in the UI, revert on API failure with an error toast.
- **REC-5.3**: Use short-polling (2-second interval) for bulk check progress in V1. The frontend polls a status endpoint while `isCheckingAll` is true.
- **REC-5.4**: Implement a toast notification system for action feedback: success (device added, update confirmed), error (check failed, network error), warning (partial completion on bulk check).
- **REC-5.5**: Show a "Check All" progress indicator: "Checking 3 of 12 devices…" in the header or near the Check All button.
- **REC-5.6**: Disable the "Check All" button while a bulk check is in progress (already in the mockup), and disable per-device check buttons during a bulk check to prevent conflicting requests.

---

## 6. Accessibility in Dashboards

### ARIA Roles and Status Communication

- **Key findings**: Dashboards with dynamic status indicators have specific accessibility requirements:
  - **Stats cards**: Use `role="status"` or `aria-live="polite"` on the stats region so screen readers announce changes when checks complete (e.g., "Updates Available: 3" → "Updates Available: 2" after a confirm).
  - **Device cards**: Each card should have a descriptive `aria-label` combining the device name and status: `aria-label="Sony A7IV — Update available: local v2.00, latest v3.00"`.
  - **Checking state**: Use `aria-busy="true"` on a device card while a check is in progress. Announce completion via an `aria-live` region.
  - **Group sections**: Use `role="region"` with `aria-labelledby` pointing to the group heading for each device type section.

### Color-Blind Safe Status Indicators

- **Key findings**: Relying solely on red/green color to indicate update status is a WCAG failure (1.4.1 Use of Color). Approximately 8% of males have red-green color vision deficiency. Mitigation strategies:
  - **Redundant coding**: Pair colors with **distinct icons**: checkmark (✓) for up-to-date, alert triangle (⚠) or arrow-up for update available, dash (—) or clock for never checked. The mockup partially does this (ArrowRight for updates) but should be more explicit.
  - **Text labels**: Include text status labels (not just colors) — "Up to date" vs. "Update available" vs. "Never checked". Useful for all users, essential for color-blind users.
  - **Shape differentiation**: Use filled vs. outlined badges, or different icon shapes, not just color swaps.
  - **Tested palette**: The mockup's emerald/rose pairing is moderately safe (distinguishable in deuteranopia simulation) but adding icons and text labels is still recommended.

### Keyboard Navigation

- **Key findings**: Dashboard UX should be fully operable via keyboard:
  - **Tab order**: Logical flow — stats → filter bar → first group → first device card → card actions → next card → next group.
  - **Focus indicators**: Visible focus rings on all interactive elements. Tailwind's `focus:ring-2 focus:ring-offset-2` (present in the mockup) is the correct base. Ensure focus rings are visible in both light and dark modes.
  - **Card actions**: The "Check" and "Sync Local" buttons within cards must be focusable and operable via Enter/Space.
  - **Skip links**: A "Skip to main content" link (visually hidden, visible on focus) allows keyboard users to bypass the sidebar navigation.
  - **Escape key**: Close modals, slide-overs, and mobile menu on Escape press.

### Relevance to Binocular

The mockup includes focus ring styles but lacks ARIA attributes, skip links, live regions, and redundant status encoding. These are essential for inclusive UX and should be in the spec's acceptance criteria.

### Specific Recommendations

- **REC-6.1**: Add `aria-live="polite"` to the stats card region so screen readers announce count changes after checks or confirmations.
- **REC-6.2**: Include text status labels alongside color indicators on device cards: "Update Available" or "Up to Date" as visible text, not just color differences.
- **REC-6.3**: Use distinct icons per status state — not just color variants of the same icon. `CheckCircle2` for up-to-date, `AlertCircle` (or `ArrowUpCircle`) for update available, `Clock` or `Minus` for never checked.
- **REC-6.4**: Add a visually hidden "Skip to main content" link as the first focusable element.
- **REC-6.5**: Ensure focus ring colors have sufficient contrast in dark mode — Tailwind's default `ring-offset-slate-900` is correct but should be verified against the actual background.
- **REC-6.6**: Trap focus within modal/slide-over forms when open, and return focus to the trigger element when closed.
- **REC-6.7**: Add `aria-label` to icon-only buttons (e.g., the per-device check button should have `aria-label="Check for firmware updates"`).

---

## 7. Empty States and Onboarding

### First-Run Experience

- **Key findings**: Empty states are the user's **first impression** and a critical onboarding moment. Best practices from Linear, Notion, Uptime Kuma, and Mealie:
  - **Never show a blank page**: An empty dashboard with no devices should show an **illustrated empty state** with a clear call-to-action. The pattern is: illustration/icon + headline + supportive text + primary action button.
  - **Contextual empty states**: Each section should have its own empty state. The dashboard says "No devices yet — add your first device", the Modules tab says "No modules installed — upload a module to start checking for firmware", etc.
  - **Progressive disclosure**: Don't overwhelm first-time users. The ideal first-run flow:
    1. Dashboard shows empty state with "Add Your First Device" CTA.
    2. Adding a device naturally leads to selecting/creating a device type.
    3. After adding the first device, the dashboard populates and the user sees how it works.
  - **Guidance text**: Include brief explanatory text in the empty state: "Devices are grouped by Device Type. Each device type is linked to an Extension Module that knows how to check for firmware updates."

### Empty State Variations

- **Key findings**: There are multiple empty state contexts in Binocular, each needing its own treatment:
  1. **Global empty** (no devices at all): Big, welcoming illustration + "Get Started" flow.
  2. **Group empty** (device type exists but has no devices): Smaller inline empty state within the group section.
  3. **No results** (filters applied but nothing matches): "No devices match your filter. Try a different filter or reset."
  4. **Error state** (failed to load data): "Unable to load devices. Check your connection and try again." with a retry button.
  5. **Empty after deletion** (last device removed): Return to the global empty state gracefully.

### Onboarding Guidance

- **Key findings**: For a tool targeting tech-savvy users, heavy onboarding wizards are unwelcome. The preferred approach:
  - **Contextual hints**: Subtle inline guidance that appears only when relevant (e.g., a tip near an empty modules list: "Binocular ships with Sony and Panasonic modules. Upload additional modules here.").
  - **No forced tours**: Avoid step-by-step walkthrough overlays. Homelab users prefer to explore on their own.
  - **Documentation links**: Include a "Learn more" link to documentation in empty states and complex sections.
  - **Sample data option**: Consider (but don't force) a "Load example data" button on first run so users can see how the UI looks when populated. Must be clearly labeled and easily deletable.

### Relevance to Binocular

The mockup shows a populated dashboard but no empty states. Since the app starts with zero data, the first thing every new user sees is an empty state — getting this right is critical for first impressions.

### Specific Recommendations

- **REC-7.1**: Design a welcoming empty state for the dashboard: Binocular icon/illustration + "No devices yet" headline + "Start by adding your first device to track firmware updates" body text + prominent "Add Device" button.
- **REC-7.2**: Each navigational section (Logs, Modules, Settings) should have a unique contextual empty state explaining what the section does and how to populate it.
- **REC-7.3**: The empty state for the dashboard should mention that pre-built modules for Sony and Panasonic are available, pointing users toward the Modules tab: "Binocular ships with modules for Sony Alpha and Panasonic Lumix. Visit Modules to get started."
- **REC-7.4**: After the last device or device type is deleted, gracefully return to the empty state — do not show a broken/empty card grid.
- **REC-7.5**: Include a "No results" empty state for when filters are applied but nothing matches, with a "Clear filters" action button.
- **REC-7.6**: Error states (backend unreachable, API errors on load) should show a friendly message with a "Retry" button, not an empty or broken layout.
- **REC-7.7**: Avoid forced onboarding wizards — rely on contextual hints and well-designed empty states. The target audience is technically savvy and prefers self-guided exploration.

---

## Key Takeaways for Specification

### Priority Guidance

1. **P1 (MVP-critical)**: Dark mode with system detection + responsive sidebar layout + device card grid with version comparison + stats cards + "Check Now" / "Check All" with loading states + "Sync Local" confirm action + Add/Edit device form (slide-over) + basic empty state for dashboard.
2. **P2 (High-value)**: Group collapsibility + filter/sort controls + toast notification system + per-device independent check completion + accessibility (ARIA labels, keyboard nav, color-blind safety) + contextual empty states for all sections.
3. **P3 (Polish)**: Three-option theme toggle (system/light/dark) + inline editing for device name + "Check All" progress indicator + skip links + sample data on first run + error-state recovery screens.

### Critical Edge Cases

- **Theme flash**: White flash on load before dark class is applied (FOIT). Must be prevented by inline `<head>` script.
- **Mobile version comparison**: Long version strings (e.g., `3.2.12-beta.4`) truncating or overflowing in the version comparison panel on narrow screens.
- **Simultaneous actions**: User clicks "Check" on a device while "Check All" is already running — must not fire duplicate checks or corrupt state.
- **Stale dashboard state**: User has two tabs open; Tab A confirms an update, Tab B still shows the old state. Must handle gracefully (stale data is acceptable in V1 since single-user, but "Confirm" on already-confirmed device must be idempotent per API contract).
- **Form state loss**: User opens the add-device form, fills out fields, accidentally closes the panel — data is lost. Consider a confirmation dialog for unsaved changes.
- **Empty device type dropdown**: User tries to add a device but no device types exist yet. The form must provide a path to create one inline.
- **Network loss during check**: Backend becomes unreachable while a check is in progress. Spinner should time out and show an error, not spin indefinitely.
- **Very long device/type names**: Names up to 200 chars (API limit) must not break card layouts. Truncate with ellipsis and show full name on hover/tooltip.
- **Zero devices in a type**: A device type with zero devices should still show in the UI (empty group state) — it shouldn't silently disappear.
- **Rapid confirm clicks**: Double-clicking "Sync Local" must not cause issues — the optimistic update handles this naturally since the second click is a no-op on an already-synced device.

### Reference Implementations

| Tool | Relevant Pattern | URL |
|------|-----------------|-----|
| Uptime Kuma | Grouped status dashboard, tri-state indicators, empty states | https://github.com/louislam/uptime-kuma |
| Portainer | Sidebar navigation, dark mode, container cards | https://www.portainer.io/ |
| Home Assistant | Mobile-responsive dashboard, device grouping, entity cards | https://www.home-assistant.io/ |
| Mealie | FastAPI + React, slide-over forms, CRUD inventory UX | https://mealie.io/ |
| UniFi Console | Device inventory grouping, firmware update indicators | https://ui.com/ |
| Linear | Empty states, keyboard-first navigation, slide-over forms | https://linear.app/ |
| Tailwind UI | Dark mode patterns, component accessibility, dashboard layouts | https://tailwindui.com/ |

---

## 8. Package Manager

- **Decision**: Use `npm` with `package-lock.json` committed to the repository.
- **Rationale**: Zero additional tooling — npm ships with Node.js and is the path of least resistance for a monorepo with a single `frontend/` workspace. The project instructions require "exact versions in a lock file"; `package-lock.json` with `npm ci` satisfies this. No workspaces or monorepo hoisting needed — the backend uses Python/Poetry, so there's no shared dependency tree.
- **Alternatives**: pnpm (faster installs, stricter node_modules) rejected because it adds a global installation step and Docker layer; yarn rejected for similar reasons plus ongoing v1-vs-v4 fragmentation.
- **Pitfalls**: Always use `npm ci` (not `npm install`) in CI and Docker builds to ensure reproducible installs from the lock file.

---

## 9. React Router

- **Decision**: React Router v7 (latest stable) with a flat route configuration. Four top-level routes: `/` (Inventory dashboard, default), `/logs` (Activity Logs placeholder), `/modules` (Modules tab), `/settings` (Settings placeholder).
- **Rationale**: React Router is the de facto routing library for React SPAs. The 4-tab layout maps naturally to 4 routes with a shared `AppShell` layout route wrapping sidebar + header. No nested routing needed — tab content is a single page, not a drill-down hierarchy. The `<NavLink>` component provides active-tab styling out of the box (FR-006, SC-008).
- **Alternatives**: TanStack Router (excellent type safety but adds learning curve for a simple 4-route app); file-based routing (Remix convention) rejected — overkill for 4 routes.
- **Pitfalls**: Configure the Vite dev server and FastAPI production server to return `index.html` for all unmatched routes (SPA fallback) so deep-linking and browser refresh work on `/modules`, etc.

---

## 10. State Management

- **Decision**: TanStack Query v5 for all server state (device lists, device types, modules). Local UI state (sidebar open, theme toggle, form inputs) uses plain React `useState`/`useReducer`.
- **Rationale**: TanStack Query eliminates manual loading/error/refetch boilerplate — every API call gets caching, background revalidation, and optimistic mutation support for free. The confirm action (FR-010) benefits from `useMutation` with `onMutate` for optimistic UI updates. Cache invalidation after create/edit/delete operations keeps the dashboard stats (FR-021) automatically in sync. There's no need for a global state library (Zustand, Redux) because there's no cross-cutting client-side state beyond the theme preference and sidebar toggle.
- **Alternatives**: Plain `fetch` + `useState` (simpler but requires manual cache invalidation, loading states, and error handling for every endpoint — roughly doubles the boilerplate); Zustand (lightweight but doesn't address async data fetching, which is the main concern).
- **Pitfalls**: Set `staleTime` generously (e.g., 30 seconds) since this is a single-user app — avoids unnecessary re-fetches. Disable refetchOnWindowFocus in development to prevent confusing re-renders.

---

## 11. API Client

- **Decision**: Hand-written typed `fetch` wrapper in a single `frontend/src/api/` module. One function per API operation (e.g., `listDeviceTypes()`, `createDevice()`, `confirmDevice()`). Return types mirror the OpenAPI response schemas as TypeScript interfaces.
- **Rationale**: With only 12 API endpoints, a code-generator (openapi-typescript-codegen, orval) adds tool complexity that exceeds the value. A hand-written client is ~150 lines, fully typed, and trivially maintainable. The base URL is `/api/v1` (same-origin), so no CORS configuration needed. Error responses are parsed into a typed `ApiError` structure matching the backend error envelope (`{ detail, error_code, field }`).
- **Alternatives**: `openapi-fetch` or `orval` for auto-generated client — rejected because adding a code-gen step to the build pipeline is over-engineering for 12 endpoints. `axios` — rejected because the `fetch` API is built into all target browsers and avoids an extra dependency.
- **Pitfalls**: Always check `response.ok` before parsing JSON — a common fetch pitfall is silently succeeding on 4xx/5xx. Centralize error parsing so error codes are available to TanStack Query's `onError` callbacks.

---

## 12. Form Management

- **Decision**: React Hook Form for all CRUD forms (add/edit device, add/edit device type/module).
- **Rationale**: React Hook Form provides uncontrolled inputs with minimal re-renders, built-in validation, and — critically — a `setError()` API that maps backend error responses directly to form fields. When the API returns `{ error_code: "DUPLICATE_NAME", field: "name" }`, the form can call `setError("name", { message: "A device with this name already exists" })` without custom plumbing. This directly supports FR-017 and SC-007 (inline error feedback).
- **Alternatives**: Native form handling + `useState` (viable for 3-field forms but loses `setError()` integration and requires manual dirty/pristine tracking); Formik (heavier, re-renders on every keystroke by default, largely superseded).
- **Pitfalls**: Keep validation schemas colocated with form components, not in a separate file — the forms are simple enough that centralized validation adds indirection without benefit.

---

## 13. Vite Dev Proxy

- **Decision**: Configure Vite's `server.proxy` to forward `/api` requests to `http://localhost:8000` during development. The frontend dev server runs on port 5173 (Vite default).
- **Rationale**: During development, the React app and FastAPI backend run as separate processes. The proxy avoids CORS issues and mirrors the production single-port setup. The `changeOrigin: true` setting ensures the backend sees the correct `Host` header. This is the standard Vite pattern for API proxying.
- **Alternatives**: CORS middleware on the backend (viable but introduces config that doesn't exist in production); running both through a common reverse proxy (Caddy/nginx) — overkill for local dev.
- **Pitfalls**: Ensure the proxy matches the full `/api` prefix so health checks and all versioned routes are forwarded. Websocket proxying is not needed (no WebSockets in V1).

---

## 14. Frontend Quality Gates

- **Decision**: Biome (single tool for linting + formatting) plus `tsc --noEmit` for type checking. Addresses the Principle VII gap identified in the instructions check.
- **Rationale**: Biome is the frontend equivalent of Ruff — a single, fast Rust-based tool that handles both linting and formatting with zero plugins. This mirrors the backend's single-tool approach. `tsc --noEmit` in strict mode is the TypeScript equivalent of `mypy --strict`. These three checks (`biome check`, `biome format --check`, `tsc --noEmit`) run as pre-merge gates alongside the Python `ruff` + `mypy` checks.
- **Alternatives**: ESLint + Prettier (the traditional stack but requires two tools, plugin configuration, and resolving formatting conflicts between them); dprint (fast formatter but lacks linting).
- **Pitfalls**: Biome's rule coverage is ~95% of ESLint's core + recommended rule sets as of 2025 — verify that any project-specific rules needed are supported. Pin the Biome version in `package.json` to avoid rule drift.

---

## 15. Testing Strategy

- **Decision**: Vitest + React Testing Library (RTL) for component-level tests. One optional Playwright smoke test for the critical happy path (load dashboard → confirm device → verify stats update).
- **Rationale**: Vitest is Vite-native (shared config, fast HMR-style test execution) and API-compatible with Jest. RTL encourages testing user behavior rather than implementation details — consistent with the project instructions' principle of testing "API behavior and integration boundaries, not internal implementation details." Playwright is reserved for a single smoke test only, to avoid the CI overhead (browser binaries, 10x slower execution) that full E2E coverage adds to a 5–50 device single-user tool.
- **Alternatives**: Jest (viable but slower startup, requires separate config, no Vite integration); Cypress (heavier than Playwright, slower); full Playwright suite (excessive CI cost for the scope).
- **Pitfalls**: Mock the API layer in component tests (using MSW or TanStack Query's test utilities) to keep tests fast and deterministic. Do not mock React Router — render components within a `MemoryRouter` for realistic route testing.

---

## 16. CSS Strategy

- **Decision**: Tailwind CSS v3.4+ with `darkMode: 'class'` strategy. Dark mode is toggled by adding/removing the `dark` class on the `<html>` element.
- **Rationale**: The `class` strategy gives programmatic control over the theme (required for manual toggle + localStorage persistence + OS preference fallback). The mockup already uses Tailwind utility classes throughout (`bg-slate-950`, `text-indigo-400`, etc.), so no conversion needed. The `tailwind.config.ts` file uses TypeScript for type-safe configuration.
- **Alternatives**: `darkMode: 'media'` strategy (follows OS preference only, no manual toggle — doesn't meet FR-002/FR-004); CSS custom properties with `data-theme` attribute (more flexible but breaks Tailwind's `dark:` prefix convention and loses the mockup's existing class usage).
- **Pitfalls**: Ensure the FOIT-prevention script (REC-3.2) in `index.html` applies the `dark` class before React hydrates. Use Tailwind's `h-dvh` utility for mobile viewport height (REC-2.3). Purge unused styles in production build for minimal CSS bundle.

---

## 17. Build Output & Integration

- **Decision**: Vite builds to `frontend/dist/`. In production, FastAPI mounts this directory via `StaticFiles` at `/` with a catch-all fallback to `index.html` for SPA routing. The Docker build uses a multi-stage Dockerfile: Node stage runs `npm ci && npm run build`, Python stage copies `frontend/dist/` and serves it.
- **Rationale**: This is the canonical single-port SPA pattern — the backend owns the HTTP port and serves both API routes (`/api/v1/*`) and static files (`/*`). The catch-all ensures browser refreshes on `/modules` or `/settings` don't 404. Multi-stage Docker keeps the final image small (no Node runtime in production).
- **Alternatives**: Serving frontend via nginx sidecar (violates single-container principle); embedding build output in the Python package (complicates the build pipeline and makes frontend iteration harder).
- **Pitfalls**: Route ordering matters — mount API routes first, then the static file catch-all, so `/api/*` requests never hit the SPA fallback. Set correct `Cache-Control` headers for hashed assets (`immutable, max-age=31536000`) vs. `index.html` (`no-cache`).

---

## Summary (Architecture Decisions)

| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| Package Manager | npm + package-lock.json | Zero-setup, lock file satisfies project instructions |
| Routing | React Router v7 (flat, 4 routes) | De facto standard, NavLink active styling, simple SPA layout |
| Server State | TanStack Query v5 | Eliminates async boilerplate, native optimistic mutations |
| API Client | Hand-written typed fetch wrapper | 12 endpoints don't justify code-gen tooling |
| Forms | React Hook Form | setError() maps backend errors to form fields directly |
| Dev Proxy | Vite server.proxy → localhost:8000 | Mirrors production single-port; no CORS config |
| Quality Gates | Biome + tsc --noEmit | Ruff-equivalent single tool; addresses Principle VII |
| Testing | Vitest + RTL; one Playwright smoke test | Vite-native, behavior-focused, minimal CI overhead |
| CSS | Tailwind v3.4+, darkMode: 'class' | Mockup already uses Tailwind utilities; class strategy enables toggle |
| Build & Serve | Vite → dist/, FastAPI StaticFiles, multi-stage Docker | Single-port, small image, SPA fallback |
