# Tasks: Responsive UI & Dark Mode

**Plan**: [plan.md](plan.md) | **Spec**: [spec.md](spec.md) | **Total Tasks**: 18

## Dependencies

```
T001 ──┬── T002 ──┬── T004 ── T005 ── T006 ── T007 ── T008
       │          │
       └── T003 ──┤
                  │
                  ├── T009 ── T010
                  ├── T011 ── T012
                  └── T013
                       
T014 (parallel with T002-T013)
T015 ── T016 (after all polish tasks)
T017 ── T018 (after viewport/dark tasks complete)
```

## Phase 1: Theme Foundation

- [x] T001 [P] [US1] {FR-005} Extract CSS custom property tokens and replace root `:root`/`:root.dark` definitions in `frontend/src/index.css` with complete token set (surface, panel, ink, muted, accent) covering all UI states (default, hover, focus, disabled, active) → exports: CSS token system
- [x] T002 [P] [US4] {FR-002} Add FOUC-prevention inline `<script>` to `frontend/index.html` that reads `localStorage` key `binocular-theme` and sets `document.documentElement` class before first paint
- [x] T003 [P] [US4] {FR-002} {FR-008} Extract theme-resolution function from `ThemeProvider.tsx` into shared logic used by both the inline script (copy-pasted) and ThemeProvider; update `useState` initializer and `useEffect` to use shared function [COMPLETES req FR-002 sync, FR-008 binary persist]

## Phase 2: Color Token Migration

- [x] T004 [P] [US1] {FR-001} {FR-005} Replace all color-related `dark:` Tailwind variants in inventory view (inventory page, device cards, stats cards, form, version badges) with CSS custom property tokens in `frontend/src/App.tsx`
- [x] T005 [P] [US1] {FR-001} {FR-005} Replace all color-related `dark:` Tailwind variants in activity log view (table, filter toolbar, status badges, expandable rows) with CSS custom property tokens in `frontend/src/App.tsx`
- [x] T006 [P] [US1] {FR-001} {FR-005} Replace all color-related `dark:` Tailwind variants in modules view (module cards, upload form, status badges, validation summary) with CSS custom property tokens in `frontend/src/App.tsx`
- [x] T007 [P] [US1] {FR-001} {FR-005} Replace all color-related `dark:` Tailwind variants in settings view (SMTP panel, Gotify panel, form grids) with CSS custom property tokens in `frontend/src/App.tsx`
- [x] T008 [P] [US1] {FR-001} {FR-005} Replace color-related `dark:` variants in shared layout (sidebar, header, nav items, overlay) with CSS custom property tokens and verify no hardcoded light-only values remain in `frontend/src/App.tsx`

## Phase 3: Responsive & Accessibility

- [x] T009 [P] [US2] {FR-003} Apply single-column responsive breakpoints (max-width:639px) to all view layouts: inventory device grid, module cards, settings panels — ensure touch targets ≥44×44px on all interactive elements in `frontend/src/App.tsx`
- [x] T010 [P] [US2] {FR-004} Ensure activity log table is horizontally scrollable on narrow viewports with visible scroll indicators (shadow/arrow hints); verify 6-column layout remains readable in `frontend/src/App.tsx`
- [x] T011 [P] [US4] {FR-006} Add `motion-safe:` prefix to all `transition-*` and `transform` utilities; add `motion-reduce:transition-none motion-reduce:transform-none` for instant state changes when `prefers-reduced-motion: reduce` in `frontend/src/App.tsx` and `frontend/src/index.css`
- [x] T012 [P] [US2] {FR-007} Apply `text-overflow: ellipsis` with `overflow: hidden` and `whitespace: nowrap` to all user-provided text elements (device names, module names, model fields) at narrow viewports in `frontend/src/App.tsx`
- [x] T013 [P] [US2] {FR-009} Make mobile sidebar nav list scrollable (`overflow-y: auto`) when nav items exceed viewport height; ensure tap-outside and nav-link dismissal return focus to hamburger trigger in `frontend/src/App.tsx`

## Phase 4: Testing & Verification

- [x] T014 [P] [US1] [US2] [US3] [US4] Add Playwright e2e test setup: install Playwright, create `frontend/e2e/` directory with config file targeting `http://localhost:5173`, add e2e test script to `package.json` → exports: Playwright test infrastructure
- [x] T015 [P] [US1] {FR-001} Write Playwright dark mode visual audit tests: navigate all routable views at 320px/768px/1280px with `dark` class applied, verify no unreadable text or invisible borders via screenshot comparison [COMPLETES req SC-001]
- [x] T016 [P] [US4] {FR-006} Write Playwright theme toggle tests: verify toggle within 200ms with zero layout shift (screenshot diff); verify instant transitions when `prefers-reduced-motion: reduce` [COMPLETES req SC-005, SC-006]
- [x] T017 [P] [US2] {FR-003} Write Playwright mobile operability tests: verify all views at 320px — buttons/inputs/toggles reachable, table scrollable, sidebar opens/dismisses correctly [COMPLETES req SC-002, SC-003]
- [x] T018 [P] [US3] {FR-003} Write Playwright desktop consistency test: measure content padding, header height, card spacing, form widths across all views at 1280px; assert all within ±4px [COMPLETES req SC-004]
