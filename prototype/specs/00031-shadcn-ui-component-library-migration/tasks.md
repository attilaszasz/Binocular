# Tasks: Shadcn UI Component Library Migration

**Input**: Design documents from `specs/00031-shadcn-ui-component-library-migration/`
**Prerequisites**: `plan.md` (required), `spec.md` (required)

**Tests**: Test update tasks included (spec requires all tiers to pass as SC-006, SC-007, SC-008).

## Project Mode

`Brownfield` — migrates existing React SPA from ad-hoc Tailwind v3 to Tailwind v4 + shadcn/ui; decomposes monolithic App.tsx.

## Brownfield Notes

- Existing flows touched: All 4 routes (inventory, logs, modules, settings), all API clients preserved
- Compatibility concerns: ThemeProvider `.dark` toggling preserved; `<Routes>/<Route>` pattern preserved; Dockerfile unchanged
- Regression focus: Theme toggle, sidebar nav, inventory CRUD, module upload, activity log filtering, settings config, brand/version display

## Phase 1: Setup — Dependency & Toolchain Upgrade

- [X] T001 Record baseline bundle size and Lighthouse score in specs/00031-shadcn-ui-component-library-migration/baseline.json
- [X] T002 {TR-001} Bump deps in frontend/package.json — React 19, @types/react v19, Vite 6, React Router 7, TanStack Query 5, lucide-react
- [X] T003 [P] {TR-002} Install @tailwindcss/upgrade, run codemod, delete frontend/tailwind.config.ts and frontend/postcss.config.js
- [X] T004 [P] {TR-002} Install @tailwindcss/vite, configure frontend/vite.config.ts with tailwindcss() plugin and @/ path alias
- [X] T005 {TR-002,TR-003} Rewrite frontend/src/index.css — @import "tailwindcss", @theme block for fonts/shadows, @custom-variant dark after:T003
- [X] T006 [P] {TR-002} Add @/ path alias in frontend/tsconfig.app.json
- [X] T007 {TR-002} [COMPLETES TR-002] Gate — verify npm run build and npm run dev succeed after phase completion

---

## Phase 2: Foundational — Bootstrap shadcn/ui

- [X] T008 {TR-004} Install shadcn@^2.0.0 as devDependency in frontend/package.json
- [X] T009 {TR-004} Run npx shadcn@2.x.x init — New York, Zinc, TS, Vite, CSS vars after:T008
- [X] T010 {TR-005} Configure blue primary CSS vars (--primary: 221.2 83.2% 53.3%) in frontend/src/index.css after:T009
- [X] T011 [P] {TR-004} Verify components.json config and lib/utils.ts cn() utility exist and match spec after:T009
- [X] T012 {TR-008} Generate shadcn components via npx shadcn add button input label select card badge table switch tooltip after:T009
- [X] T013 {TR-004,TR-005,TR-008} [COMPLETES TR-004] Gate — verify cn() merges classes and bg-primary renders blue after:T010,T011,T012

---

## Phase 3: Color Token Migration (OBJ3) 🎯 MVP

- [X] T014 [OBJ3] {TR-007} Remove all motion-safe: prefixes from frontend/src/**/*.tsx and frontend/src/**/*.ts
- [X] T015 [OBJ3] {TR-006} Remap custom color classes to shadcn colors across all .tsx/.ts files per mapping table in plan.md
- [X] T016 [OBJ3] {TR-006} Remove --color-* CSS blocks and update body styles to bg-background text-foreground in index.css after:T015
- [X] T017 [OBJ3] {TR-006} Update shadow colors using shadcn CSS var syntax in frontend/src/index.css after:T016
- [X] T018 [OBJ3] {TR-006,TR-007} [COMPLETES TR-006] Gate — grep verify zero old patterns and zero --color- tokens after:T014,T017

---

## Phase 4: Adopt shadcn Components (OBJ4) 🎯 MVP

- [X] T019 [OBJ4] {TR-009} Replace layout buttons with <Button> — theme toggle, sidebar toggle, mobile hamburger in App.tsx
- [X] T020 [OBJ4] {TR-009} Replace NavItem and VersionDisplay tooltips with <Tooltip> composite in App.tsx and VersionDisplay.tsx
- [X] T021 [OBJ4] {TR-009} Replace inventory components — DeviceForm <Input>/<Label>/<Select>, StatCard <Card>, DeviceCard <Card>/<Badge>/<Button> in App.tsx
- [X] T022 [OBJ4] {TR-009} Replace logs page — FilterBar <Select>, LogTable <Table>/<Badge>, TracebackPanel <Button> in App.tsx
- [X] T023 [OBJ4] {TR-009} Replace modules page — ModuleUploadForm <Input>/<Button>, ModuleCard <Card>/<Badge>, FrequencyEditor <Switch> in App.tsx and FrequencyEditor.tsx
- [X] T024 [OBJ4] {TR-009} Replace settings page — ChannelConfigForm <Input>/<Label>/<Card>, checkboxes <Input type="checkbox">, StatusMessage in App.tsx
- [X] T025 [OBJ4] {TR-009} [COMPLETES TR-009] Final cleanup — audit for stray <button>, native <select>, custom role patterns after:T019,T020,T021,T022,T023,T024

---

## Phase 5: Decompose App.tsx (OBJ5)

- [X] T026 [OBJ5] {TR-010} Extract layout components — Brand, NavItem, Sidebar, Header, VersionDisplay to components/layout/
- [X] T027 [P] [OBJ5] {TR-010} Extract inventory components — InventoryPage, DeviceForm, StatCard, DeviceCard to components/inventory/
- [X] T028 [P] [OBJ5] {TR-010} Extract log components — LogsPage, FilterBar, LogTable, TracebackPanel to components/logs/
- [X] T029 [P] [OBJ5] {TR-010} Extract module components — ModulesPage, ModuleUploadForm, ModuleCard, ModuleStatusBadge to components/modules/
- [X] T030 [P] [OBJ5] {TR-010} Extract settings components — SettingsPage, ChannelConfigForm, StatusMessage to components/settings/
- [X] T031 [OBJ5] {TR-010} Wire up App.tsx with imports and routes; verify ≤200 lines after:T026,T027,T028,T029,T030
- [X] T032 [OBJ5] {TR-010} [COMPLETES TR-010] Fix all import paths to use @/ alias across extracted components after:T031

---

## Phase 6: Verify Tests & Quality Gates (OBJ6) 🎯 MVP

- [X] T033 [OBJ6] {TR-011} Update unit tests — fix import paths in App.test.tsx and VersionDisplay.test.tsx
- [X] T034 [OBJ6] {TR-011} Update Playwright E2E test selectors for shadcn composite elements in e2e/*.spec.ts
- [X] T035 [OBJ6] {TR-011} Update Playwright visual baselines with --update-snapshots after:T034
- [X] T036 [OBJ6] {TR-011} Run axe-core accessibility scan on all 4 routes in light and dark modes
- [X] T037 [OBJ6] {TR-011} Run Lighthouse audit against production build; verify performance ≥90
- [X] T038 [OBJ6] {TR-011} Compare bundle size (dist/assets/*.js total) against baseline; verify ≤110%
- [X] T039 [OBJ6] {TR-011} [COMPLETES TR-011] Final gate — npm test, npm run test:e2e, npm run typecheck, npm run lint all pass

---

## Dependencies

Setup (Phase 1) → Foundational (Phase 2) → OBJ3 (Phase 3) 🎯 MVP → OBJ4 (Phase 4) 🎯 MVP → OBJ5 (Phase 5) → OBJ6 (Phase 6) 🎯 MVP

- Phase 1 must complete before Phase 2 (shadcn requires Tailwind v4).
- Phase 2 must complete before Phases 3–6 (all depend on shadcn bootstrap + generated components).
- Phase 3 (color tokens) must complete before Phase 4 (component adoption) — classes must map before replacing markup.
- Phase 4 (component adoption) must complete before Phase 5 (decomposition) — extracted components must use shadcn patterns.
- Phase 5 (decomposition) must complete before Phase 6 (verification) — tests operate on final file structure.
- Tasks marked `[P]` within a phase can run in parallel (different files, no shared state).
- Tasks with `after:T###` declare explicit cross-task dependencies; sequential T### ordering within a phase implies dependencies for non-[P] tasks.
