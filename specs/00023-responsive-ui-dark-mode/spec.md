---
feature_branch: "00023-responsive-ui-dark-mode"
created: "2026-06-04"
input: "E016 Responsive UI & Dark Mode"
spec_type: product
spec_maturity: clarified
epic_id: "E016"
epic_sources:
  - PRD:CAP-012
---

# Feature Specification: Responsive UI & Dark Mode

**Epic ID**: E016 | **Epic Sources**: {PRD:CAP-012} | **Spec Maturity**: clarified | **Product Document**: specs/prd.md

## Problem Statement

Binocular's UI works on desktop but has inconsistent responsive behavior on mobile — tables overflow without readable fallbacks, touch targets are undersized, and form grids are cramped. Dark mode is wired up with Tailwind `dark:` variants, but a white flash precedes first paint and the defined CSS custom properties go unused. The self-hosting audience expects mobile parity and polished dark mode; gaps erode the "set-and-forget" trust the product promises.

## Scope

### Included

- Responsive layouts for all routable views (inventory incl. check UI, activity log, modules, settings) at 320px–1280px+
- Consistent dark mode across all view elements — no visual gaps
- FOUC elimination via theme-class injection before first paint
- Replace color-related `dark:` variants with CSS custom property tokens (`--color-*`) as sole theming; retain `dark:` for non-color concerns only
- Binary theme toggle (Light/Dark); `prefers-color-scheme` as initial default only; explicit user choice always wins
- Touch targets ≥44×44px on mobile; `prefers-reduced-motion` support

### Excluded

- Component extraction from `App.tsx` — no structural refactoring
- New features, pages, or data flows — polish only
- Cross-tab theme sync — each tab operates independently
- Print stylesheet; full a11y audit — touch/motion only
- `@tailwindcss/container-queries` plugin — breakpoints suffice for monolithic structure

### Edge Cases & Boundaries

- 50+ devices or 100+ log entries remain scrollable/readable at 320px
- Dark mode persists across refresh without re-flash; silent `prefers-color-scheme` fallback when localStorage unavailable
- Mobile sidebar: content scrollable when overflowed; tap-outside/nav-link dismisses; focus returns to trigger
- Long device/module names truncate via CSS text-overflow

## User Scenarios & Testing

### User Story 1 - Consistent Dark Mode Across All Views (Priority: P1)

As an operator working late, I want every screen to render correctly in dark mode so I can manage inventory without eye strain.

**Why this priority**: Dark mode is a first-class product requirement; inconsistency breaks the core visual experience.

**Independent Test**: Navigate all routes in dark mode — verify all text, borders, backgrounds, inputs, and badges are readable.

**Acceptance Scenarios**:

1. **Given** dark mode, **When** navigating any view or refreshing, **Then** all elements render with dark colors and no white flash
2. **Given** the operator toggles dark mode, **When** switching routes, **Then** theme stays consistent without reverting

### User Story 2 - Mobile-Usable Primary Views (Priority: P1)

As an operator checking firmware from my phone, I want every primary view fully usable on mobile.

**Why this priority**: Mobile parity is a core scope constraint; broken mobile views render the tool unusable.

**Independent Test**: Open each view at 320px — verify buttons/inputs/toggles reachable, text readable, hamburger navigation works.

**Acceptance Scenarios**:

1. **Given** 320px viewport, **When** opening inventory or modules, **Then** cards stack single-column, interactive elements ≥44×44px, inputs full-width
2. **Given** 320px viewport, **When** opening activity log, **Then** table is horizontally scrollable with visible overflow
3. **Given** 320px viewport, **When** opening hamburger menu, **Then** sidebar slides in with tappable nav items; tap-outside or nav-link dismisses

### User Story 3 - Polished Desktop Layout Consistency (Priority: P2)

As an operator with a large inventory, I want consistent spacing/alignment across views so the interface feels cohesive.

**Why this priority**: Visual consistency builds trust; layout drift undermines polish.

**Independent Test**: Compare all routable views at 1280px — verify consistent header heights, padding, card spacing, form widths.

**Acceptance Scenarios**:

1. **Given** a desktop viewport (1280px+), **When** navigating between views, **Then** content margins, headers, and card/panel spacing are consistent
2. **Given** a desktop viewport, **When** resizing the browser, **Then** grids/flex adapt smoothly without overlapping

### User Story 4 - Smooth Theme Transitions (Priority: P2)

As an operator switching themes, I want smooth transitions without flashes or layout shifts.

**Why this priority**: Theme-toggle flashes break immersion; smooth transitions are baseline polish.

**Independent Test**: Toggle dark mode repeatedly — verify no layout shift, smooth color transitions, immediate icon update.

**Acceptance Scenarios**:

1. **Given** any view is open, **When** toggling dark mode, **Then** elements transition within 200ms with no layout shift
2. **Given** `prefers-reduced-motion: reduce`, **When** toggling theme or opening sidebar, **Then** transitions are instant

## Requirements

### Functional Requirements

- **FR-001**: System MUST ensure every routable view renders correctly in dark mode — all text, controls, tables, forms, badges, and status indicators have sufficient contrast (WCAG AA: ≥4.5:1 body, ≥3:1 large) and no hardcoded light-only values
- **FR-002**: System MUST inject the `dark` class before first paint (FOUC prevention), with theme-resolution logic shared between inline script and ThemeProvider
- **FR-003**: System MUST use single-column layout below 640px (max-width: 639px queries), with touch targets ≥44×44px
- **FR-004**: System MUST make the activity log table horizontally scrollable on narrow viewports with visible overflow
- **FR-005**: System MUST replace all color-related `dark:` variants with CSS custom property tokens (`--color-surface`, `--color-panel`, `--color-ink`, `--color-muted`, `--color-accent`) as the exclusive color theming mechanism
- **FR-006**: System MUST respect `prefers-reduced-motion`, disabling sidebar/theme animations when active
- **FR-007**: System MUST truncate long user text at narrow widths via CSS text-overflow
- **FR-008**: System MUST persist binary theme preference in localStorage (`binocular-theme`), using `prefers-color-scheme` as initial default; explicit preference overrides OS changes
- **FR-009**: System MUST make the mobile sidebar scrollable when overflowed; tap-outside/nav-link dismisses with focus returned to trigger

### Key Entities

- **UI View**: Each routable screen (inventory including check UI, activity log, modules, settings) receiving responsive and dark-mode polish. No new data entities introduced.
- **Theme**: Light/dark binary mode persisted in localStorage, applied via `class` on `<html>`, using CSS tokens for theming.

## Assumptions & Risks

### Assumptions

- Existing UI components preserve behavior after presentation-only changes
- ThemeProvider, localStorage persistence, and `class`-based dark mode remain the foundation
- Tailwind CSS v3.4 breakpoint utilities are sufficient; no container-queries needed
- `App.tsx` remains monolithic; no structural refactoring

### Risks

- **Visual regression in light mode** *(likelihood: medium, impact: high)*: Replacing `dark:` variants with tokens could alter light colors. Mitigation: run existing snapshot tests.
- **Mobile layout breakage on edge content** *(likelihood: low, impact: medium)*: Long names could overflow. Mitigation: test with maximum-length fixtures.
- **FOUC script conflicts** *(likelihood: low, impact: low)*: Inline script may interact with Vite HMR. Mitigation: production-only guard.

## Implementation Signals

- `NEW-UI` — Responsive/dark-mode polish across all route components, shared layout, and theme infrastructure (FOUC script, CSS token adoption replacing Tailwind dark: colors)

## Success Criteria

### Measurable Outcomes

- **SC-001 [US1]**: Zero instances of unreadable text, invisible borders, or mismatched backgrounds in dark mode across all routable views at 320px, 768px, 1280px
- **SC-002 [US2]**: All routable views fully operable at 320px — interactive elements reachable/tappable/functional. Scrollable table rows exempt from 44px width (height ≥44px required)
- **SC-003 [US2]**: Mobile sidebar opens, navigates, and dismisses on touch — content scrollable; no focus trapping; dismissal returns focus
- **SC-004 [US3]**: Content padding, header height, card spacing, form field widths consistent (±4px) across all routable views at 1280px
- **SC-005 [US4]**: Theme toggle completes within 200ms with no visible layout shift (Playwright visual comparison — zero pixel displacement)
- **SC-006 [US4]**: When `prefers-reduced-motion: reduce` is active, all sidebar and theme animations disabled (instant)

## Glossary

| Term | Definition |
|------|------------|
| FOUC | Flash of Unstyled Content — white flash before dark mode CSS class applies |
| CSS Custom Properties | Reusable variables (e.g., `--color-surface`) that change with theme |
| WCAG AA | Web Content Accessibility Guidelines level AA — contrast ratios of 4.5:1 (normal text) and 3:1 (large text / UI components) |

## Clarifications *(see [clarifications.md](clarifications.md) for full Q&A and stress-test findings)*

All ambiguity resolutions and adversarial stress-test findings from the 2026-06-04 clarification session are integrated above. Key decisions: all routable views in scope (including settings), binary theme toggle, CSS tokens replace color `dark:` variants, WCAG AA contrast, single-column below 640px.

## Compliance Check

**Status**: PASS — No policy violations. All mandatory sections present, no unauthorized sections, no reordered priorities, no changed IDs, no manual markers.
