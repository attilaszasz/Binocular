# Tasks: Collapsible Menu & Version Display
> Branch: `00030-collapsible-menu-version-display` | Epic: E029 | Generated: 2026-06-08

## Task List

### [P1] SETUP — VITE_APP_VERSION Build-Time Env Injection

- [X] **E029-T001**: Add `ARG VITE_APP_VERSION` and `ENV` to Docker frontend-builder stage
  - **Files**: `~ Dockerfile`
  - **Depends on**: None
  - **Details**: In the `frontend-builder` stage, insert `ARG VITE_APP_VERSION` then `ENV VITE_APP_VERSION=$VITE_APP_VERSION` immediately before `RUN npm run build`. Ensure the `.git` directory is present in the Docker build context (HINT-002). The env var is resolved at build time via `git describe --tags --first-parent --always --dirty` and passed as `--build-arg VITE_APP_VERSION="$(git describe --tags --first-parent --always --dirty)"`. Vite statically replaces `import.meta.env.VITE_APP_VERSION` at compile time. FR-005, AD-003, HINT-001.
  - **Acceptance**: `docker build --build-arg VITE_APP_VERSION="v1.0.0"` produces a frontend bundle where `import.meta.env.VITE_APP_VERSION` resolves to `"v1.0.0"`.
  - **Effort**: S

### [P1] FOUNDATIONAL — Collapse State Management

- [X] **E029-T002**: Add `isCollapsed` state with lazy `useState` initializer reading `localStorage`
  - **Files**: `~ frontend/src/App.tsx`
  - **Depends on**: None
  - **Details**: In the `App` component, add `const [isCollapsed, setIsCollapsed] = useState(() => { let stored: string | null = null; try { stored = localStorage.getItem('binocular-nav-collapsed'); } catch {} return stored === 'true'; });`. Use functional updater `setIsCollapsed(prev => !prev)` for rapid-click safety (HINT-004). The lazy initializer ensures synchronous localStorage read with no flash-of-wrong-state on first render. Use narrow try-catch scoped only to `getItem` (CHK098). Store value as raw `"true"`/`"false"` strings, not JSON (CHK099). FR-001, FR-006, AD-001.
  - **Acceptance**: On first render with no localStorage value, `isCollapsed` is `false` (sidebar expanded). With `localStorage['binocular-nav-collapsed'] === 'true'`, `isCollapsed` is `true`. Storage failures silently default to expanded.
  - **Effort**: S

### [P1] STORY — US1: Collapse/Expand Sidebar

- [X] **E029-T003**: Implement toggle button with `PanelLeftClose`/`PanelLeftOpen` icon and sidebar width transitions
  - **Files**: `~ frontend/src/App.tsx`
  - **Depends on**: E029-T002
  - **Details**: Add `PanelLeftClose, PanelLeftOpen` to the lucide-react import block. Position a `<button>` at the bottom of the `<aside>` (above the version area, outside the scrollable `<nav>`) using `flex-col` layout. When `isCollapsed === false` (expanded), show `PanelLeftClose` icon; when `true` (collapsed), show `PanelLeftOpen`. Apply `aria-label="Collapse sidebar"` when expanded, `"Expand sidebar"` when collapsed. Set `aria-expanded={!isCollapsed}` per HINT-004 (reflects the *opposite* of collapsed — true when sidebar IS expanded). Apply Tailwind width classes `md:w-64` (expanded) / `md:w-16` (collapsed) with `motion-safe:transition-[width] motion-safe:duration-300 motion-safe:ease-in-out` on the `<aside>` element (HINT-003, CHK085). Use `md:` prefix to scope collapsible behavior to viewport ≥768px (STF-001). FR-001, SC-001.
  - **Acceptance**: Clicking the toggle button switches the `<aside>` width between `md:w-64` and `md:w-16` with a smooth 300ms transition. The icon flips between `PanelLeftClose` and `PanelLeftOpen`. The toggle is a native `<button>` activated by Enter/Space.
  - **Effort**: M

- [X] **E029-T004**: Synchronize main content `margin-left` with sidebar width
  - **Files**: `~ frontend/src/App.tsx`
  - **Depends on**: E029-T003
  - **Details**: On the `<main>` element, conditionally apply `md:ml-64` (when `isCollapsed === false`) and `md:ml-16` (when `isCollapsed === true`). Use `motion-safe:transition-[margin-left] motion-safe:duration-300 motion-safe:ease-in-out` for synchronous animation with the sidebar width transition (CHK085). Both transitions share the same `duration-300` timing so the browser coalesces style recalc into a single layout pass per frame (CHK083). FR-001, SC-001, Q009.
  - **Acceptance**: When the sidebar collapses, the main content's left margin transitions from `ml-64` to `ml-16` in lock-step with the sidebar width. The content area does not overlap the sidebar in either state.
  - **Effort**: S

### [P1] STORY — US2: Icon Navigation with Tooltips

- [X] **E029-T005**: Add tooltip component to `NavItem` with CSS show/dismiss timing
  - **Files**: `~ frontend/src/App.tsx`
  - **Depends on**: E029-T002
  - **Details**: In the `NavItem` component (inside the `<NavLink>`), add a tooltip `<div>` using Tailwind's `group`/`group-hover` pattern. The tooltip is absolutely positioned to the right of the icon. Use `invisible group-hover:visible group-focus-visible:visible` classes for visibility (CHK110). Apply CSS transition delay: `transition-opacity delay-200 duration-150` for mouse hover 200-300ms delay, and keyboard focus shows immediately (the `group-focus-visible:visible` class overrides the delay — apply `focus-visible:delay-0`). Dismiss immediately on mouse leave (no auto-dismiss timeout while hovering per Q003). Escape key dismisses via a `onKeyDown` handler on the NavLink that focuses the trigger element. Use a `useRef<HTMLDivElement>` for the tooltip DOM node reference. CHK092, CHK104, CHK107, CHK114. FR-003, SC-002, AD-002.
  - **Acceptance**: Hovering a collapsed nav icon shows a tooltip after 200-300ms; moving the mouse away dismisses it immediately. Tabbing to the icon shows the tooltip immediately. Escape dismisses it. Tooltip is purely CSS-driven with no JavaScript state for visibility.
  - **Effort**: M

- [X] **E029-T006**: Add ARIA tooltip relations (`role="tooltip"`, `aria-describedby`) and `aria-label` on collapsed `NavLink`
  - **Files**: `~ frontend/src/App.tsx`
  - **Depends on**: E029-T005
  - **Details**: The tooltip `<div>` must carry `role="tooltip"`. Each collapsed `<NavLink>` must reference it via `aria-describedby` with a unique ID (e.g., `tooltip-${item.to.replace(/\//g, '')}`). In collapsed state, each `<NavLink>` must have `aria-label={item.label}` for screen reader announcement (FR-003). Dynamically set these attributes based on `isCollapsed`. The tooltip must NOT receive focus (focus stays on the trigger NavLink). In expanded state, these ARIA attributes are not needed because labels are visible. FR-003, SC-002.
  - **Acceptance**: Keyboard/screen reader users navigating collapsed sidebar hear the `aria-label` for each nav item. The tooltip element has `role="tooltip"` and is linked via `aria-describedby`. The toggle preserves existing navigation behavior (deep links, route clicks) per FR-007.
  - **Effort**: S

- [X] **E029-T007**: Conditionally hide/show nav item text labels using `invisible`/`visible` classes
  - **Files**: `~ frontend/src/App.tsx`
  - **Depends on**: E029-T002
  - **Details**: The `<span>{item.label}</span>` inside `NavItem` receives conditional classes: `invisible md:group-hover:visible` (or just `invisible` when collapsed, `visible` when expanded). Use `invisible` not `hidden` (CHK110) to avoid forced layout recalculation — `visibility: hidden` only triggers repaint, not layout. The label toggle is batch-rendered in the same commit as the width transition (CHK093). FR-002, SC-002.
  - **Acceptance**: When sidebar is collapsed, nav item text labels are invisible (not rendered as empty, just visually hidden). When expanded, labels are fully visible. The browser does not trigger forced layout from `display` changes.
  - **Effort**: S

### [P2] STORY — US3: Application Version Display

- [X] **E029-T008**: Create `VersionDisplay` component with env var reading, truncation, and tooltip
  - **Files**: `+ frontend/src/components/VersionDisplay.tsx`
  - **Depends on**: E029-T001
  - **Details**: Create a new memoized component `const VersionDisplay = React.memo(() => { ... })` (CHK105). Read the version from `import.meta.env.VITE_APP_VERSION` with fallback chain: if defined use the value, else `"dev"`. In expanded state, show full version string. In collapsed state, abbreviate: for SemVer tags truncate with text-ellipsis via Tailwind `truncate` class; for abbreviated SHA (7 chars) show full SHA truncated with ellipsis; for `"dev"` show untruncated (FR-004, STF-004). Add a tooltip following the same pattern as nav-item tooltips (group-hover/focus-visible, role="tooltip", aria-describedby) that exposes the full version string in collapsed state (CHK114). Use CSS custom property tokens for text color (`text-muted`). FR-004, SC-003.
  - **Acceptance**: `VersionDisplay` renders the version string from `VITE_APP_VERSION`. In expanded mode the full string is shown. In collapsed mode, long strings are truncated with ellipsis, and a tooltip reveals the full version. The component does not re-render on collapse toggle (React.memo).
  - **Effort**: M

- [X] **E029-T009**: Integrate `VersionDisplay` into sidebar with sticky-bottom positioning
  - **Files**: `~ frontend/src/App.tsx`
  - **Depends on**: E029-T008, E029-T002
  - **Details**: Import `VersionDisplay` from `./components/VersionDisplay`. Place it in the `<aside>` flex column after the scrollable `<nav>` and after the toggle button. Use `mt-auto` on the flex spacer before the version display to push it to the bottom without breaking flex layout on mobile (HINT-005). The version display must be sticky at the bottom, outside the scrollable `<nav>`, always visible regardless of nav item overflow (FR-004, Q005). Pass `isCollapsed` prop to `VersionDisplay` for truncation behavior. FR-004.
  - **Acceptance**: The version string renders at the bottom of the sidebar, below the toggle button, always visible in both collapsed and expanded states. It does not scroll with nav items.
  - **Effort**: S

### [P2] STORY — US4: Persist Collapse Preference

- [X] **E029-T010**: Write collapse state to localStorage on toggle with try-catch guards
  - **Files**: `~ frontend/src/App.tsx`
  - **Depends on**: E029-T002
  - **Details**: In the toggle `onClick` handler, after calling `setIsCollapsed(prev => !prev)`, write the new state to localStorage synchronously: `try { localStorage.setItem('binocular-nav-collapsed', String(newState)); } catch {}`. Use narrow try-catch scoped only to `setItem` (CHK098). Store raw string `"true"`/`"false"` not JSON (CHK099). On write failure, the in-memory state remains collapsed for the current session but persistence is lost (STF-003). Cross-tab synchronization is out of scope — last-write-wins is accepted (STF-005). The toggle handler must not await anything, and the state update must happen before the localStorage write so UI is never blocked (CHK094). FR-006, SC-004.
  - **Acceptance**: After toggling the sidebar and refreshing the page, the sidebar loads in the toggled state. If localStorage is unavailable, the sidebar defaults to expanded without crashing. On write failure, state is kept in-memory for the session.
  - **Effort**: S

### [P1] POLISH — Accessibility, Theming, and Responsive Edge Cases

- [X] **E029-T011**: Add ARIA landmark roles, `aria-expanded`, visible focus indicators, and breakpoint scoping
  - **Files**: `~ frontend/src/App.tsx`
  - **Depends on**: E029-T003, E029-T006
  - **Details**: Ensure the `<aside>` carries an ARIA landmark role for screen reader skip-nav (SC 2.4.1). The sidebar `<aside>` should have `role="complementary"` or `aria-label="Sidebar"` (CHK007). Add `:focus-visible` styling on toggle button and all NavLink elements using existing `focus-visible:ring-2 focus-visible:ring-accent-focus/40` pattern (already present on other interactive elements in the app). Ensure DOM order follows visual order — toggle button after nav items in the DOM, no `tabindex` reordering (SC 2.4.3, CHK006). The toggle button `aria-expanded` semantics must reflect the expanded state (`true` when sidebar IS expanded, following the Disclosure pattern from ARIA APG). Verify that all existing routes (`/inventory`, `/logs`, `/modules`, `/settings`) are reachable in both collapsed and expanded states with no console errors (FR-007, SC-005). Ensure deep-linking works identically in both states (Edge Cases). FR-001, FR-003, FR-007.
  - **Acceptance**: Screen reader user hears landmark role on sidebar. Toggle button has correct `aria-expanded` value. All focusable elements show a visible focus ring on `:focus-visible`. DOM order matches visual order. All routes load correctly in both states.
  - **Effort**: M

- [X] **E029-T012**: Apply existing CSS custom property tokens for dark/light mode consistency
  - **Files**: `~ frontend/src/App.tsx`, `~ frontend/src/components/VersionDisplay.tsx`
  - **Depends on**: E029-T003, E029-T009
  - **Details**: The toggle button icon, version display text, tooltip text, and focus rings MUST use the existing `--color-*` CSS custom property tokens via Tailwind utility classes (e.g., `text-muted`, `text-ink`, `bg-panel`, `border-panel`, `focus-visible:ring-accent-focus/40`). Do not use raw hex values (FR-008, CHK011). Verify WCAG AA 4.5:1 contrast for version text and tooltip text, and WCAG SC 1.4.11 3:1 non-text contrast for the toggle icon and focus rings, in both dark and light modes (CHK009, CHK010). Theme toggle (dark/light) must NOT change collapse state — these are orthogonal (Edge Cases, CHK012). FR-008, SC-006.
  - **Acceptance**: The toggle icon, version text, and tooltip render correctly with proper contrast in both dark and light mode. Theme switching preserves sidebar collapse state.
  - **Effort**: S

- [X] **E029-T013**: Scope collapsible behavior to desktop breakpoint and verify mobile unchanged
  - **Files**: `~ frontend/src/App.tsx`
  - **Depends on**: E029-T003
  - **Details**: All collapsible-related width classes use `md:` prefix (`md:w-64`, `md:w-16`, `md:ml-64`, `md:ml-16`). Below the `md:` breakpoint (<768px), the sidebar continues to use the existing mobile hamburger overlay pattern unchanged (scrollable nav, `-translate-x-full`/`translate-x-0` transform, overlay backdrop). The `isMobileMenuOpen` state and its trigger (hamburger button in header) must remain untouched. Verify that on viewport <768px, the sidebar width is not affected by `isCollapsed` state. FR-001, FR-007, STF-001.
  - **Acceptance**: On viewport ≥768px, the sidebar collapses/expands with width transition. On viewport <768px, the mobile hamburger overlay pattern continues to work unchanged.
  - **Effort**: S

### [P1] TESTING — Unit, Integration, and Coverage

- [X] **E029-T014** [COMPLETES FR-006]: Write unit tests for collapse/expand toggle, margin sync, and localStorage persistence
  - **Files**: `~ frontend/src/App.test.tsx`
  - **Depends on**: E029-T004, E029-T010, E029-T011
  - **Details**: Extend the existing test suite with:
    1. **Collapse toggle**: Render app, find toggle button by `aria-label` ("Collapse sidebar"), click it, assert sidebar has collapsed width class (`md:w-16`). Click again, assert expanded width (`md:w-64`). Verify icon changes.
    2. **Margin sync**: Assert `<main>` has `md:ml-16` when collapsed and `md:ml-64` when expanded.
    3. **localStorage read**: Set `localStorage.setItem('binocular-nav-collapsed', 'true')` before render, verify sidebar loads collapsed.
    4. **localStorage write**: Toggle sidebar, assert `localStorage.setItem` was called with `'binocular-nav-collapsed'` and `'true'`/`'false'` string.
    5. **localStorage failure mock**: Mock `localStorage.getItem` to throw, verify app renders expanded without crash.
    6. **localStorage write failure mock**: Mock `localStorage.setItem` to throw, verify no crash and in-memory state persists.
    Use `vi.stubEnv`/`vi.unstubEnv` for env var isolation where needed. Mock `window.matchMedia` for resize. FR-001, FR-006, SC-001, SC-004.
  - **Acceptance**: All six test cases pass. localStorage mock is scoped per test. Toggle produces correct class changes. Failure modes are graceful.
  - **Effort**: M

- [X] **E029-T015** [COMPLETES FR-004]: Write unit tests for `VersionDisplay` component
  - **Files**: `+ frontend/src/components/VersionDisplay.test.tsx`
  - **Depends on**: E029-T008, E029-T012
  - **Details**: Create a new test file `VersionDisplay.test.tsx`. Test:
    1. **SemVer tag expanded**: Mock `import.meta.env.VITE_APP_VERSION = 'v1.2.3'`, `isCollapsed={false}`, assert full text "v1.2.3" renders.
    2. **SemVer tag collapsed**: Mock `VITE_APP_VERSION = 'v1.2.3'`, `isCollapsed={true}`, assert the version text is truncated (class `truncate` present) and tooltip exists.
    3. **SHA fallback**: Mock `VITE_APP_VERSION = 'abc1234'`, assert 7-char SHA renders.
    4. **Dev fallback**: Mock `VITE_APP_VERSION = 'dev'`, assert "dev" renders.
    5. **Tooltip**: In collapsed state, hover the version element, verify tooltip with full version appears.
    6. **Theme tokens**: Assert `text-muted` class applied.
    7. **React.memo**: Assert component does not re-render when `isCollapsed` prop changes but version string is same (use `React.mock` tracking).
    Use `vi.stubEnv('VITE_APP_VERSION', 'v1.2.3')`. FR-004, FR-005, SC-003.
  - **Acceptance**: All seven test cases pass. VersionDisplay renders correctly for all version string formats in both expanded and collapsed states.
  - **Effort**: M

- [X] **E029-T016**: Write integration tests for tooltip show/dismiss timing, keyboard focus, and ARIA attributes
  - **Files**: `~ frontend/src/App.test.tsx`
  - **Depends on**: E029-T006, E029-T007
  - **Details**: Extend the existing test suite with:
    1. **Collapse sidebar first**, then hover a nav item: use `userEvent.hover()` and `vi.advanceTimersByTime(250)` to verify tooltip becomes visible after 200-300ms.
    2. **Keyboard focus**: Tab to a collapsed nav item (with `userEvent.tab()`), verify tooltip appears immediately without timer advancement.
    3. **Dismiss on mouse leave**: Show tooltip via hover, then `userEvent.unhover()`, verify tooltip becomes invisible immediately.
    4. **Escape dismiss**: Focus a nav item, press Escape, verify tooltip dismisses and focus stays on the trigger.
    5. **ARIA assertions**: Verify `role="tooltip"` on tooltip container, `aria-describedby` on NavLink, `aria-label={item.label}` on collapsed NavLink.
    6. **Label visibility**: Assert nav item `<span>` has `invisible` class when collapsed, `visible` when expanded.
    7. **Navigation still works**: After collapsing, click a nav icon, verify route navigation occurs.
    Use `vi.useFakeTimers()` for delay assertions, real timers restore after test. FR-003, SC-002, SC-005.
  - **Acceptance**: All seven test cases pass. Tooltip timing matches spec (200-300ms hover, immediate focus). ARIA attributes present. Navigation works in collapsed state.
  - **Effort**: M

- [X] **E029-T017** [COMPLETES FR-001] [COMPLETES FR-003] [COMPLETES FR-007]: Write accessibility, theme compatibility, and edge case tests
  - **Files**: `~ frontend/src/App.test.tsx`
  - **Depends on**: E029-T011, E029-T012, E029-T013
  - **Details**: Extend the existing test suite with:
    1. **Landmark role**: Assert `<aside>` has `role="complementary"` or appropriate landmark role.
    2. **Focus order**: Assert toggle button appears after nav items in DOM (test DOM position).
    3. **Focus indicator**: Assert `:focus-visible` CSS class is present on focusable elements (check for `focus-visible:ring-2` in class list).
    4. **Theme compatibility**: Toggle dark mode, assert sidebar elements still render with correct class names (`text-muted`, `bg-panel`). Verify collapse state unchanged after theme toggle.
    5. **Deep-link works**: Navigate directly to `/modules` with collapsed sidebar, verify route loads correctly.
    6. **Mobile unchanged**: Set viewport to 375px width (`window.innerWidth = 375`), assert hamburger menu works and collapsible width classes are not applied.
    7. **Rapid toggles**: Programmatically toggle 5 times in rapid succession, assert final state is correct (no glitch, CSS transition handles interruption).
    8. **console.error check**: Assert no console errors occurred during all test scenarios.
    FR-001, FR-003, FR-007, FR-008, SC-005, SC-006.
  - **Acceptance**: All eight test cases pass. No console errors. The sidebar is accessible, theme-compatible, and mobile behavior is unchanged.
  - **Effort**: M

---

**Total tasks**: 17
**Breakdown by phase/story**: SETUP 1, FOUNDATIONAL 1, US1 2, US2 3, US3 2, US4 1, POLISH 3, TESTING 4
**Dependency chain**: T001 → T008 → T009 → T012 → T015; T002 → T003/T005/T007/T010; T003 → T004 → T014; T005 → T006 → T016; T006+T003 → T011 → T017; T008+T002 → T009; T004+T010+T011 → T014; T006+T007 → T016; T011+T012+T013 → T017
