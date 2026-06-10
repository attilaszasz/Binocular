---
feature_branch: "00030-collapsible-menu-version-display"
created: "2026-06-08"
input: "E029 Collapsible Menu & Version Display"
spec_type: product
spec_maturity: clarified
epic_id: "E029"
epic_sources:
  - PRD:CAP-012
---

# Feature Specification: Collapsible Menu & Version Display

**Feature Branch**: `00030-collapsible-menu-version-display`
**Created**: 2026-06-08
**Status**: Draft
**Spec Type**: product
**Spec Maturity**: clarified
**Epic ID**: E029
**Epic Sources**: {PRD:CAP-012}
**Product Document**: specs/prd.md

## Problem Statement

The left-side navigation is always expanded at full width on desktop, consuming horizontal space even when the operator knows the icon positions. The application version is not displayed anywhere in the UI, making it difficult for operators to confirm which build is running. Self-hosting users expect compact navigation that maximizes content area, and pinned dependency/container versions are a standard operability cue. Without these changes, the nav consumes unnecessary space and operators lack a quick way to verify the deployed version.

## Scope

### Included

- Desktop collapsible sidebar (viewport ≥768px) with a toggle button (positioned at the bottom of the sidebar, above the version string) using `PanelLeftClose`/`PanelLeftOpen` icon to switch between expanded (`md:w-64`) and icon-only collapsed (`md:w-16`) modes
- Main content area `margin-left` transitions synchronously with the sidebar width
- Icon-only collapsed state hiding all text labels, with hover and focus tooltips revealing the navigation item label
- Application version string displayed at the bottom of the sidebar, sourced from the build-time environment
- Application version string derived from the latest git tag at build time, injected as a compile-time constant
- localStorage persistence of the collapsed/expanded preference across sessions
- Dark and light mode compatibility matching the existing theme system

### Excluded

- Collapsible behavior on mobile (below 640px) — the existing mobile hamburger overlay pattern is retained and unchanged
- Version update checking or notification — version display is informational only
- User-configurable version label — the version is always auto-derived from the build
- Reordering or customizing nav items — structure remains as defined by E003
- Animation customization — uses default transitions consistent with the existing UI animation system

### Edge Cases & Boundaries

- When no git tag exists at build time, the version display falls back to an abbreviated commit SHA
- When localStorage is unavailable or throws, the sidebar defaults to expanded state without crashing
- Toggling between dark and light modes must not change sidebar collapse state
- Deep-linking to a route must work identically in both collapsed and expanded states
- The version display must handle unusually long version strings with text truncation
- Rapid repeated toggle clicks must not cause animation or layout glitches (debounce at the animation level via CSS transitions)
- Keyboard operators must be able to identify collapsed nav items via tooltip on focus and `aria-label` attributes
- All focusable sidebar elements (toggle button, nav links) MUST have a visible focus indicator in both collapsed and expanded states, using `:focus-visible` for keyboard-only focus styling
- The toggle button MUST appear after the navigation items in the DOM order to match visual order, with no `tabindex` reordering
- The sidebar `<aside>` element MUST carry an ARIA landmark role (e.g., `complementary`) for screen reader skip-nav functionality
- In development mode (`npm run dev`), the version string falls back to `git describe --tags --first-parent --always --dirty` output or `"dev"` if git is unavailable
- When the sidebar is collapsed with the dirty worktree flag (`--dirty`), the version string accurately reflects uncommitted changes in development builds

## User Scenarios & Testing

### User Story 1 — Collapse and Expand the Sidebar (Priority: P1)

The operator clicks a toggle button on the left sidebar to collapse the navigation to an icon-only state, reclaiming screen real estate for the main content area. Clicking the toggle again restores the full expanded view with labels.

**Why this priority**: Core value proposition — without the collapse/expand mechanism, the feature has no utility.

**Independent Test**: Toggle the sidebar and verify the width transitions between expanded and collapsed (icon-only) states.

**Acceptance Scenarios**:

1. **Given** the sidebar is expanded, **When** the operator clicks the collapse toggle, **Then** the sidebar transitions to icon-only collapsed mode with labels hidden and the toggle icon reflects the collapsed state.
2. **Given** the sidebar is collapsed, **When** the operator clicks the expand toggle, **Then** the sidebar transitions to full expanded mode with labels visible.

### User Story 2 — Navigate with Icons in Collapsed Mode (Priority: P1)

With the sidebar collapsed to icon-only, the operator hovers over a navigation icon and sees a tooltip revealing the item label. Keyboard operators tabbing through nav items see the same tooltip on focus. Clicking the icon navigates to the target route as usual. All existing navigation behavior is preserved.

**Why this priority**: The collapsed state must remain fully navigable — unusable navigation defeats the purpose.

**Independent Test**: Collapse the sidebar, hover each nav icon, verify tooltips appear and clicking navigates correctly. Tab through nav items and verify tooltips appear on keyboard focus.

**Acceptance Scenarios**:

1. **Given** the sidebar is collapsed, **When** the operator hovers over a navigation icon for 200-300ms, **Then** a tooltip appears to the right of the icon showing the nav item label.
2. **Given** the sidebar is collapsed and the operator uses a keyboard, **When** the operator tabs to a navigation icon, **Then** a tooltip appears to the right of the focused icon showing the nav item label.
3. **Given** the sidebar is collapsed, **When** the operator clicks a navigation icon, **Then** the app navigates to the target route without errors, matching the behavior in the expanded state.

### User Story 3 — View Application Version at Menu Bottom (Priority: P2)

The operator looks at the bottom of the left sidebar and sees the current Binocular version string (e.g., "v1.2.3" or a commit SHA). The version is automatically derived from the latest git tag at build time, never hardcoded.

**Why this priority**: Significant value for operability and debugging, but the app works without it and the nav collapse is the primary deliverable.

**Independent Test**: Build the Docker image with a git tag, deploy, and verify the version string appears at the bottom of the sidebar matching the tag.

**Acceptance Scenarios**:

1. **Given** the Docker image was built from a tagged commit, **When** the sidebar renders, **Then** the version display at the bottom shows the SemVer tag (e.g., "v0.1.0").
2. **Given** the Docker image was built from an untagged commit, **When** the sidebar renders, **Then** the version display shows the abbreviated commit SHA.

### User Story 4 — Persist Collapsed/Expanded Preference (Priority: P2)

The operator collapses the sidebar, navigates to another page, and returns to find the sidebar still collapsed. The preference survives page navigation and browser tab close.

**Why this priority**: Enhances the P1 flows — remembering preference avoids repeated toggle actions, but the app works without it.

**Independent Test**: Collapse the sidebar, refresh the page, verify the sidebar loads in the collapsed state.

**Acceptance Scenarios**:

1. **Given** the operator has collapsed the sidebar, **When** they navigate to another route, **Then** the sidebar remains collapsed.
2. **Given** the operator has collapsed the sidebar, **When** they close and reopen the browser tab, **Then** the sidebar loads in the collapsed state.

## Requirements

### Functional Requirements

- **FR-001**: System MUST provide a visible toggle button at the bottom of the sidebar (just above the version string) using a `PanelLeftClose`/`PanelLeftOpen` icon that switches between expanded (`md:w-64`, full labels) and collapsed (`md:w-16`, icon-only) states on click. The toggle button MUST carry an `aria-label` of "Collapse sidebar" when expanded and "Expand sidebar" when collapsed. The main content area margin-left MUST transition synchronously between `md:ml-64` (expanded) and `md:ml-16` (collapsed) with a `motion-safe:duration-300 ease-in-out` CSS transition on the `margin-left` property. Collapsible sidebar behavior is scoped to viewport widths ≥768px (desktop).
- **FR-002**: System MUST hide all nav item text labels when the sidebar is collapsed; only icons remain visible.
- **FR-003**: System MUST show a tooltip with the nav item label when hovering over (mouse) or focusing on (keyboard) a collapsed nav icon. Tooltip must appear after 200-300ms on mouse hover and immediately on keyboard focus, and dismiss immediately on mouse leave, blur, or Escape key press, with focus remaining on the triggering NavLink. The tooltip container MUST carry `role="tooltip"` and each NavLink MUST reference it via `aria-describedby` for proper screen reader announcement. In collapsed state, each `NavLink` MUST carry an `aria-label` matching the nav item label for screen reader support.
- **FR-004**: System MUST display the application version at the bottom of the sidebar in both expanded and collapsed states. In expanded state, show the full version string. In collapsed state, show an abbreviated form: (1) for SemVer tags, show the tag truncated to icon-width with ellipsis; (2) for abbreviated SHA fallback, show the full 7-char SHA truncated with ellipsis if needed; (3) for development (`"dev"`), show `"dev"` untruncated. A tooltip on the version string SHOULD expose the full version in collapsed state, following the same show/dismiss behavior as nav-item tooltips (per FR-003). The version display MUST be sticky at the sidebar bottom outside the scrollable `<nav>` area, always visible regardless of nav item overflow.
- **FR-005**: System MUST derive the version string from the latest git tag (SemVer pattern) at build time using `git describe --tags --first-parent --always --dirty`, falling back to an abbreviated commit SHA when no tag exists. The result MUST be injected as the Vite environment variable `VITE_APP_VERSION` (accessible via `import.meta.env.VITE_APP_VERSION`), set via Docker build-arg `VITE_APP_VERSION`.
- **FR-006**: System MUST persist the sidebar collapsed/expanded state in `localStorage` under key `binocular-nav-collapsed`, defaulting to expanded when no value exists or storage is unavailable. Read and write operations MUST be wrapped in a try-catch to handle `SecurityError` (private browsing, `file://` origin, blocked cookies) and other storage exceptions; on write failure, the in-memory state remains collapsed for the current session but persistence is lost. Cross-tab synchronization via the `storage` event is out of scope — last-write-wins behavior is accepted.
- **FR-007**: System MUST NOT break existing client-side routing, deep links, theme toggle, or responsive mobile sidebar behavior when the collapsible feature is active.
- **FR-008**: System MUST apply the existing dark/light CSS custom property tokens (`--color-*`) to the toggle button, version display, tooltip, and focus ring elements for consistent theming. The existing token system provides WCAG AA 4.5:1 minimum contrast ratio for text (version text, tooltip text) and WCAG SC 1.4.11 3:1 minimum non-text contrast for the toggle icon and focus rings, in both dark and light modes.

### Key Entities

- **Navigation Component**: The sidebar `<aside>` element containing nav items, toggle button (bottom, above version), and version display (sticky bottom). State machine: `{expanded (md:w-64), collapsed (md:w-16), transitioning}` with CSS transitions, persisted in `localStorage` under key `binocular-nav-collapsed`. Main content `margin-left` transitions in sync. Desktop-only behavior (viewport ≥768px).
- **Version Env Var (`VITE_APP_VERSION`)**: A build-time environment variable resolved from `git describe --tags --first-parent --always --dirty` at Docker build time, passed as `ARG VITE_APP_VERSION` to Docker and injected into the client bundle via Vite's `import.meta.env.VITE_APP_VERSION` at compile time.

## Assumptions & Risks

### Assumptions

1. The `.git` directory is available in the Docker build context so `git describe` can read tags.
2. The operator uses a modern browser with JavaScript and localStorage enabled.
3. The existing sidebar structure from E003 remains stable (nav items defined as an array of `{ label, path, icon }` objects).
4. Git tags follow the existing SemVer convention (e.g., `v0.1.0`) established in E018.

### Risks

- **No git tags exist at build time** *(likelihood: low, impact: medium)*: The version display falls back to a commit SHA via `--always`, which is less informative but still uniquely identifies the build.
- **localStorage quota exceeded or unavailable** *(likelihood: low, impact: low)*: The sidebar defaults to expanded state without crashing. Preference is not persisted for that session.
- **Sidebar changes conflict with future responsive/mobile changes** *(likelihood: medium, impact: medium)*: Adding desktop collapse on top of the mobile hamburger overlay creates two interaction models on the same element. Mitigate by ensuring the mobile breakpoint (<640px) behavior is unchanged.
- **Keyboard-only operators cannot access hover tooltips** *(likelihood: medium, impact: high)*: Without keyboard-focus tooltips and `aria-label` on collapsed nav items, keyboard users cannot identify navigation destinations. Mitigated by FR-003 requiring focus tooltips and `aria-label` on all `NavLink` elements.

## Implementation Signals

- `NEW-UI`: Collapsible sidebar navigation component with toggle, icon-only state with tooltips, and version display.
- `NEW-CONFIG`: Build-time version env var injection at compile time. No runtime configuration.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: A toggle button exists at the bottom of the sidebar and clicking it switches between expanded width (`md:w-64`) and collapsed icon-only width (`md:w-16`) with a smooth `duration-300 ease-in-out` transition on viewport ≥768px. The main content area margin-left transitions synchronously.
- **SC-002** [US2]: All nav item text labels are hidden when the sidebar is collapsed; hovering over an icon for 200-300ms or tabbing to it via keyboard displays a tooltip with the label. Each collapsed `NavLink` carries an `aria-label` matching the item label.
- **SC-003** [US3]: The version string at the sidebar bottom appears in both expanded and collapsed states. In expanded state, shows the full version string matching the git tag (or abbreviated SHA fallback, or `"dev"`). In collapsed state, shows an abbreviated form: SemVer tag truncated to icon-width with ellipsis, full 7-char SHA truncated with ellipsis, or `"dev"` untruncated. A tooltip on the collapsed version string exposes the full version.
- **SC-004** [US4]: After collapsing the sidebar and refreshing the page, the sidebar loads in the collapsed state; navigating between routes preserves the state.
- **SC-005** [US2]: All existing routes (`/inventory`, `/logs`, `/modules`, `/settings`) are reachable and load correctly in both collapsed and expanded states with no console errors.
- **SC-006** [US1][US3]: The toggle button and version display render correctly in both light and dark modes, using the existing theming system without visual regressions.

## Clarifications

### Session 2026-06-08

- Q001: Where in the sidebar is the collapse/expand toggle button positioned, and what icon/visual representation does it use for each state? -> A: Positioned at the bottom of the sidebar, just above the version string, using a `PanelLeftClose`/`PanelLeftOpen` icon that flips on state change.
- Q002: What is the exact pixel/rem width of the sidebar in its collapsed (icon-only) state? -> A: `w-16` (64px / 4rem).
- Q003: When does the hover tooltip for collapsed nav items disappear? -> A: Show after 200-300ms hover, dismiss immediately on mouse leave. No auto-dismiss timeout while hovering.
- Q004: How do keyboard-only operators identify nav item labels when the sidebar is collapsed? -> A: Show the tooltip on both hover (mouse) and focus (keyboard) via CSS `:focus-visible` or JavaScript focus handler. Additionally, add `aria-label={item.label}` to each `NavLink` for screen reader support.
- Q005: Is the version string at the bottom of the sidebar always visible (sticky/fixed), or does it scroll with the nav content? -> A: The version display is sticky at the bottom of the sidebar — rendered outside the scrollable `<nav>` in the `<aside>` flex column, always visible.
- Q006: Does the version string appear at the bottom when the sidebar is in collapsed (icon-only) state? -> A: Version shown in both states; collapsed shows abbreviated form (tag only, truncated to icon-width), expanded shows full string.
- Q007: What is the exact environment variable name used to inject the version string at build time? -> A: `VITE_APP_VERSION`, injected via `import.meta.env.VITE_APP_VERSION` in client code.
- Q009: When the sidebar collapses, how does the main content area adjust? -> A: Main content `margin-left` transitions between `md:ml-64` (expanded) ↔ `md:ml-16` (collapsed) synchronously with the sidebar width transition.

## Stress-Test Findings

### Session 2026-06-08

- **STF-001** [cross-requirement-contradiction, HIGH]: Sidebar width change applies at all viewport sizes while margin-left transition uses `md:` breakpoint, creating an undefined layout gap between 640px–767px. *Resolution:* Prefix sidebar width classes with `md:` in FR-001, SC-001, and Scope to scope collapsible behavior to desktop breakpoint.
- **STF-002** [cross-requirement-contradiction, HIGH]: Tooltip appearance delay of 200-300ms applies to keyboard focus per FR-003, contradicting SC-002. *Resolution:* Amend FR-003 to decouple timing — 200-300ms delay for mouse hover, immediate display on keyboard focus.
- **STF-003** [constraint-impossibility, MEDIUM]: localStorage write failure on toggle is not handled by FR-006, making SC-004's unconditional persistence guarantee impossible when storage is read-available but write-throws. *Resolution:* Add write-failure try-catch guard to FR-006; on write failure revert in-memory state and accept persistence loss for that session.
- **STF-004** [boundary-scale-stress, MEDIUM]: Abbreviation rule "tag only, truncated to icon-width" in collapsed state is undefined for non-tag version strings (commit SHA fallback or `"dev"` mode). *Resolution:* Extend FR-004 and SC-003 to define collapsed-state display for SHA (show full 7-char SHA truncated with ellipsis) and dev (`"dev"` untruncated) fallbacks.
- **STF-005** [concurrent-trigger-ambiguity, MEDIUM]: Multiple browser tabs persist and overwrite the same localStorage key with no cross-tab synchronization mechanism. *Resolution:* Accept last-write-wins behavior as documented; cross-tab sync explicitly out of scope for this feature.

## Glossary

| Term | Definition |
|------|------------|
| Collapsed state | Sidebar reduced to icon-only width with all text labels hidden |
| Expanded state | Sidebar at full width with all nav item labels visible |
| Build-time version env var | Compile-time environment variable containing the version string from the latest git tag |

## Compliance Check

**Audited**: 2026-06-08
**Auditor**: Policy Auditor (automated)

| Rule | Status | Notes |
|------|--------|-------|
| 1. Within Binocular product scope | PASS | Collapsible nav and version display are UI/UX enhancements under PRD:CAP-012; no domain feature creep. |
| 2. Aligns with technology constraints | PASS | Frontend-only changes (React/Vite sidebar, Vite env var, localStorage); no backend/DB/deployment changes. |
| 3. Respects trusted-LAN single-user model | PASS | No authentication, user management, roles, or multi-tenancy introduced. |
| 4. Does not contradict ADR-0001–ADR-0009 | PASS | Version env var consistent with ADR-0003 Vite build; no backend/DB changes to conflict with ADR-0004 or ADR-0008. |
| 5. No external dependencies/cloud/telemetry | PASS | Uses only standard browser API (localStorage) and build-time git tag injection; no cloud or telemetry. |
| 6. Scope boundaries clear and consistent with E029 | PASS | Included/excluded/edge cases match project-plan E029 description; depends on E003 as specified. |
| 7. FR-### requirement IDs unique | PASS | FR-001 through FR-008 — all unique, no gaps or duplicates. |
| 8. Implementation signals use only allowed tags | PASS | `NEW-UI` and `NEW-CONFIG` are both in the allowed set. |

**Overall**: PASS
