# Implementation Plan: Shadcn UI Component Library Migration

**Branch**: `00031-shadcn-ui-component-library-migration` | **Date**: 2026-06-08 | **Spec**: [spec.md](./spec.md)

## Summary

**Goal**: Migrate the Binocular React SPA from ad-hoc Tailwind 3 + custom `--color-*` tokens to Tailwind v4 + shadcn/ui (New York, Zinc, blue primary), decompose the 1981-line App.tsx into feature modules, and verify zero regressions across all test tiers.

**Approach**: Five sequential phases — dependency upgrade, shadcn bootstrap, color token remapping, component adoption, decomposition — each with its own verification gate. All API clients, routes, and the ThemeProvider remain unchanged.

**Key Constraint**: No product capability changes. Bundle size must not exceed 110% of baseline. Playwright visual baselines may shift (acceptable).

## Technical Context

**Language/Version**: TypeScript 5.x (latest)  
**Primary Dependencies**: React 19.x, React Router 7 (v6-compatible mode), Tailwind v4, shadcn/ui (New York style, Zinc base, blue primary), Radix primitives, TanStack Query 5, lucide-react, Vite 6  
**Storage**: N/A (frontend only; backend API `fetch` calls preserved)  
**Testing**: vitest + React Testing Library (unit/component), Playwright (E2E), axe-core (accessibility), Lighthouse (performance)  
**Target Platform**: Browser (latest Chrome/Firefox/Safari), served by FastAPI static files in Docker  
**Project Type**: web (React SPA)  
**Project Mode**: brownfield — upgrading and restructuring an existing frontend  
**Performance Goals**: Lighthouse performance ≥90, production bundle ≤110% of pre-migration baseline  
**Constraints**: Zero breaking changes to user-facing functionality; Docker multi-stage build must continue producing identical artifacts; `<Routes>/<Route>` pattern preserved (no data-router migration)  
**Scale/Scope**: Single-device inventory management dashboard; ~2KLOC of React code across 1 main file + 2 extracted components + 6 API modules + theme system; 4 routes

## Instructions Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Based on `project-instructions.md` v1.1.0 and the spec's compliance check:

| Gate | Status | Notes |
|------|--------|-------|
| `spec.md` exists | PASS | `specs/00031-shadcn-ui-component-library-migration/spec.md` — clarified maturity |
| Spec type is `technical` | PASS | Technical migration, no user stories required |
| Lifecycle order respected | PASS | Spec → Clarify → Plan (this artifact) |
| All 6 objectives have P1/P2 priority | PASS | OBJ1-OBJ4, OBJ6 = P1; OBJ5 = P2 |
| All 11 TRs mapped to objectives | PASS | TR-001 through TR-011 |
| Integration points preserved | PASS | IP-001 (ThemeProvider), IP-002 (API/Route) |
| Excluded scope respected | PASS | No backend changes, no visual redesign, no data-router adoption |

## Architecture

```mermaid
C4Container
  title Binocular Frontend — Post-Migration Architecture

  Container(browser, "Browser", "Chrome/Firefox/Safari")
  Container(vite, "Vite Dev Server", "vite 6 + @tailwindcss/vite")
  Container(fastapi, "FastAPI Backend", "Python 3.11, /api/v1")

  Container_Boundary(spa, "React SPA") {
    Component(main, "main.tsx", "Entry — QueryClient, BrowserRouter, ThemeProvider")
    Component(app, "App.tsx", "Routes + Layout Shell (≤200 lines)")
    Component(theme, "ThemeProvider", "E003 — .dark class toggle on <html>")
    Component(api, "API Clients", "E003/E005/E008/E010/E012/E014 — fetch wrappers")
    
    Container_Boundary(ui, "components/ui/") {
      Component(button, "Button", "shadcn — variant/size/asChild")
      Component(input, "Input", "shadcn — all form fields")
      Component(select, "Select", "shadcn composite — Trigger/Content/Item")
      Component(card, "Card", "shadcn composite — Header/Content/Footer")
      Component(badge, "Badge", "shadcn — variant: default/destructive/outline/secondary")
      Component(table, "Table", "shadcn composite — Header/Body/Row/Cell/Head")
      Component(switch_c, "Switch", "shadcn — binary toggles")
      Component(tooltip, "Tooltip", "shadcn — Trigger/Content")
      Component(label, "Label", "shadcn — form labels")
    }
    
    Container_Boundary(features, "components/{feature}/") {
      Component(inventory, "InventoryPage, DeviceCard, StatCard, DeviceForm", "Inventory management")
      Component(logs, "LogsPage, LogTable, FilterBar, TracebackPanel", "Activity log viewer")
      Component(modules, "ModulesPage, ModuleUploadForm, ScheduleEditor", "Module management + scheduling")
      Component(settings, "SettingsPage, ChannelConfigForm", "Notification channel config")
    }
    
    Container_Boundary(layout_components, "components/layout/") {
      Component(sidebar, "Sidebar", "Navigation sidebar with collapse/expand")
      Component(header, "Header", "Top bar — page title + theme toggle")
      Component(navitem, "NavItem", "Individual nav link with Tooltip when collapsed")
      Component(brand, "Brand", "Binocular logo + name")
      Component(version, "VersionDisplay", "Build version (VITE_APP_VERSION)")
    }
  }

  Rel(browser, vite, "localhost:5173", "HTTP")
  Rel(vite, spa, "bundles and serves")
  Rel(vite, fastapi, "/api, /healthz", "proxy")
  
  Rel(main, theme, "wraps")
  Rel(main, app, "renders")
  Rel(app, api, "calls")
  Rel(app, ui, "composes")
  Rel(app, features, "routes to")
  Rel(app, layout_components, "renders chrome")
  Rel(features, ui, "uses shadcn primitives")
  Rel(layout_components, ui, "uses shadcn primitives")
```

## Architecture Decisions

Feature-local tradeoffs only. Project-wide architectural decisions live in standalone ADRs under `specs/adrs/` — see ADR-0003 (React+Vite+Tailwind SPA), ADR-0001 (self-hosted monolith).

| ID | Decision | Options Considered | Chosen | Rationale |
|----|----------|--------------------|--------|-----------|
| AD-001 | Tailwind v4 migration tool | (A) `@tailwindcss/upgrade` codemod + manual fix / (B) Manual rewrite of all classes | A — codemod + manual fix | Codemod automates ~90% of mechanical renames (opacity modifiers, legacy prefixes); remaining custom `--color-*` classes are manually mapped to shadcn CSS vars |
| AD-002 | shadcn style/variant | (A) New York style, Zinc base / (B) Default style, Neutral base / (C) New York, Slate base | A — New York, Zinc | New York provides the rounded corners and shadow treatment closest to the existing design with minimal visual drift; `--primary: 221.2 83.2% 53.3%` blue matches the existing accent color intent |
| AD-003 | Monolithic decomposition strategy | (A) Extract by route/feature + shared layout / (B) Atomic component extraction / (C) Full feature-sliced design | A — route/feature extraction | Minimizes friction with existing state management (all state lives in App.tsx); feature modules are simple presentational components receiving props; matches spec target of App.tsx ≤200 lines |
| AD-004 | App.tsx state colocation | (A) Keep all state in App.tsx, pass via props / (B) Extract to per-route context providers / (C) Migrate to TanStack Query hooks | A — state kept in App.tsx | Spec explicitly excludes a data-fetching pattern rewrite; API clients are already modular; this avoids scope creep and allows future refactors independent of this migration |
| AD-005 | z-index token scale | (A) Use CSS `@theme` z-index tokens / (B) Hardcode z-50/40/30 as today / (C) Use shadcn default overlay z-index | A — CSS `@theme` z-index tokens | The sidebar uses z-50 (sidebar) / z-40 (overlay) / z-30 (header); shadcn overlays (Select content, Tooltip) use z-50 by default. A defined scale avoids conflicts: `--z-sidebar: 40`, `--z-header: 30`, `--z-overlay: 50`, `--z-tooltip: 60` |
| AD-006 | shadcn CLI version pinning | (A) Pin `shadcn@2.x.x` as devDependency / (B) Use `npx shadcn@latest` / (C) Pin via `components.json` only | A — pin as devDependency | Spec TR-004 mandates pinned version for reproducible migration; `components.json` records the version used for generation; devDependency ensures the same version is available for `npx shadcn add` |
| AD-007 | `motion-safe:` prefix removal approach | (A) Search-and-replace with a script / (B) Manual removal per file / (C) Keep as-is (v4 drops them silently) | A — scripted removal | Tailwind v4 drops `motion-safe:` prefix support (built-in `prefers-reduced-motion` handling); a simple `sed` or regex find-replace removes all occurrences before any other class edits to reduce noise |
| AD-008 | Checkbox/radio migration approach | (A) Use shadcn `<Input type="checkbox">` + `<Label>` / (B) Use Radix Checkbox/Radio primitives directly | A — styled `<Input type="checkbox">` | Spec TR-009 explicitly specifies `styled <Input type="checkbox">` with `<Label>`; the Settings page checkboxes (SMTP enabled, TLS, Gotify enabled) and form checkboxes use native inputs; Radix primitives are only used via shadcn's generated components |

## Data Model Summary

N/A — no persistent data on frontend. All data is fetched from the FastAPI backend via API clients in `src/api/` and held in React state (`useState`/`useEffect`). No schema changes.

## API Surface Summary

N/A — no API surface changes. The existing API clients at `frontend/src/api/client.ts` and per-domain modules (`inventory.ts`, `modules.ts`, `checks.ts`, `schedules.ts`, `notifications.ts`, `activity.ts`) are preserved exactly. The `index.ts` barrel export and all type exports remain unchanged. The Vite dev server proxy (`/api` → `http://127.0.0.1:8000`) is preserved.

## Testing Strategy

| Tier | Tool | Scope | Mock Boundary | Install |
|------|------|-------|---------------|---------|
| Unit/Component | vitest + React Testing Library | All extracted components, App routing, ThemeProvider | API calls mocked via `vi.mock()` in test files; jsdom environment | `npm test` (configured) |
| Integration/E2E | Playwright | Full-page flows: sidebar nav, theme toggle, inventory CRUD, module upload, settings config, activity log filtering | Real backend via dev server proxy | `npm run test:e2e` (configured) |
| Accessibility | axe-core (automated in Playwright) | All 4 routes in both light + dark modes | — | Integrated into E2E test runs |
| Performance | Lighthouse (via Playwright or CLI) | Production build audit | — | Run against production build |
| Type checking | `tsc -b` (strict) | Entire frontend source | — | `npm run typecheck` (configured) |
| Lint | eslint | All `.ts`/`.tsx` files | — | `npm run lint` (configured) |
| Coverage | `@vitest/coverage-v8` | Unit/component test coverage | — | `vitest --coverage` (configured) |

## Error Handling Strategy

N/A — error handling patterns are unchanged. Existing components display errors via `error: string | null` state (rendered as red bordered divs with `bg-error-bg border-error-border text-error`). These error display patterns will be migrated to shadcn's `--destructive` CSS variables via `bg-destructive/10 border-destructive/30 text-destructive` during Objective 3 color token migration. No new error categories introduced.

## Integration Points

| Spec Reference | System/Service | Technical Approach | Contract |
|----------------|----------------|--------------------|----------|
| IP-001 | ThemeProvider (E003) ↔ shadcn dark mode | shadcn CSS uses `@custom-variant dark (&:is(.dark *))` — ThemeProvider toggles `.dark` on `<html>` exactly as today. No code changes to ThemeProvider. | ThemeProvider.tsx — unchanged |
| IP-002 | API clients (E003/E005/E008/E010/E012/E014) | All `fetch`-based API clients in `src/api/` preserved. Import paths from decomposed components reference `../../api` or `@/api`. | `src/api/index.ts` barrel — unchanged |
| IP-002 | React Router v7 (component-tree mode) | `<Routes>/<Route>` pattern preserved. `BrowserRouter` + basename logic in `main.tsx` unchanged. NavLink usage for sidebar preserved. | `src/main.tsx` — unchanged except import paths |
| IP-002 | VITE_APP_VERSION (E029) | `VersionDisplay` component reads `import.meta.env.VITE_APP_VERSION`. Component extracted to `components/layout/VersionDisplay.tsx` — logic unchanged. | `src/components/VersionDisplay.tsx` — extracted, logic preserved |
| — | Docker multi-stage build | `Dockerfile` copies `frontend/` and runs `npm ci && npm run build`. No changes to Dockerfile. The `@tailwindcss/vite` plugin handles CSS during `vite build`. | `Dockerfile` — unchanged |
| — | Google Fonts | `@import url(...)` for Nunito Sans + JetBrains Mono kept at top of `index.css`. Font families defined in CSS `@theme` block. | `index.css` — modified (v4 syntax), fonts preserved |

## Risk Mitigation

| Risk (from spec) | Likelihood | Impact | Mitigation | Owner |
|-------------------|------------|--------|------------|-------|
| Playwright visual drift | High | Low | Baselines are acceptable to update. Each Phase verification includes E2E run; snapshots updated and reviewed at end of Phase 5. | Phase 5 |
| Radix type edges (React 19 + `@types/react` v19) | Medium | Medium | `skipLibCheck: true` already present in `tsconfig.app.json`. If new type errors arise from Radix generics, add targeted `// @ts-expect-error` with comments or config workaround. | Phase 2/4 |
| Codemod misses RGB patterns (custom `--color-*` classes) | Low | Medium | Manual grep for all `--color-` references after codemod. Search for `bg-surface`, `text-ink`, `border-panel`, `bg-accent`, `text-muted`, `motion-safe:` in all source files. Phase 3 validation script ensures zero occurrences. | Phase 3 |
| Bundle size increase from Radix deps exceeds 10% threshold | Medium | Medium | Radix primitives are tree-shakeable; shadcn generates only used components. Measure bundle before (baseline) and after migration. If >110%, selectively optimize: lazy-load routes, audit unused Radix imports. SC-008 gates on this. | Phase 5 |
| `@tailwindcss/vite` plugin breaks existing dev proxy | Low | Medium | The Vite plugin replaces PostCSS pipeline. Dev server proxy config in `vite.config.ts` is orthogonal — tested separately. If proxy breaks, fallback to direct URL config. | Phase 1 |
| z-index conflicts — sidebar vs Select dropdown/Tooltip | Low | High | AD-005 defines a z-index token scale. Audit during Phase 4 component adoption. Test: open Select dropdown while sidebar is collapsed (z-40) — dropdown (z-50) must render above. Sidebar z-40 adjusted down if needed. | Phase 4 |
| shadcn v2.x generates components with v3-era patterns | Low | Low | Spec mandates pinned version. All generated components are committed as-is under `components/ui/`. If CLI version changes, re-generate from same pinned version. | Phase 2 |

## Requirement Coverage Map

| Req ID | Component(s) | File Path(s) | Notes |
|--------|--------------|--------------|-------|
| TR-001 | React 19, `@types/react`/`@types/react-dom` v19 | `package.json` | `npm install react@^19 react-dom@^19`; bump `@types/react`/`@types/react-dom` to v19 |
| TR-002 | `@tailwindcss/vite`, `@import "tailwindcss"`, codemod, delete configs | `vite.config.ts`, `index.css`, `tailwind.config.ts` (deleted), `postcss.config.js` (deleted) | Run `@tailwindcss/upgrade` BEFORE deleting `tailwind.config.ts` — codemod reads v3 config to preserve font families and shadows |
| TR-003 | CSS `@theme { --font-sans: ...; --font-mono: ...; }`; `shadow-quiet` | `index.css` | Google Fonts `@import` stays at top; font families and shadow moved into `@theme` block |
| TR-004 | shadcn init (pinned v2.x, New York, Zinc, TS, Vite, CSS vars) | `package.json`, `components.json`, `lib/utils.ts`, `index.css` | `npx shadcn@2.x.x init` with options answered; `cn()` utility created |
| TR-005 | Blue primary CSS vars | `index.css` | `--primary: 221.2 83.2% 53.3%`; `--primary-foreground: 210 40% 98%` |
| TR-006 | Remove `--color-*` blocks; map classes to shadcn colors | All `.tsx`/`.ts`/`.css` files | Systematic mapping per Objective 3 spec; grep verification |
| TR-007 | Remove `motion-safe:` prefixes | All `.tsx`/`.ts` files | Scripted removal before other class edits; verify with grep |
| TR-008 | Generate shadcn components via CLI | `components/ui/{button,input,label,select,card,badge,table,switch,tooltip}.tsx` | `npx shadcn add button input label select card badge table switch tooltip` |
| TR-009 | Replace ad-hoc patterns with shadcn components | All `.tsx` files in `src/` | `<button>`→`<Button>`, `<select>`→`<Select>`, cards→`<Card>`, badges→`<Badge>`, `<table>`→`<Table>`, toggle→`<Switch>`, checkboxes→`<Input type="checkbox">`+`<Label>` |
| TR-010 | Decompose App.tsx | `components/{inventory,logs,modules,settings,layout}/` | Extract feature components; App.tsx ≤200 lines |
| TR-011 | All tests pass; axe-core 0 critical/serious; Lighthouse ≥90; bundle ≤110% | All test/config files | Run quality gates; update Playwright baselines; measure bundle |

## Project Structure

### Source Code

```text
frontend/
├── package.json                              ~ bumped deps (React 19, Tailwind 4, shadcn)
├── vite.config.ts                            ~ add @tailwindcss/vite plugin, drop PostCSS path
├── tsconfig.app.json                         ~ add paths { "@/*": ["./src/*"] }
├── index.html                                = unchanged
├── eslint.config.js                          = unchanged
├── tailwind.config.ts                        - DELETED (after codemod)
├── postcss.config.js                         - DELETED
├── components.json                           + shadcn CLI config (New York, Zinc, TS, Vite, CSS vars)
│
├── src/
│   ├── main.tsx                              = preserved (import paths may shift)
│   ├── index.css                             ~ v4 rewrite: @import "tailwindcss", @theme block, shadcn CSS vars, @custom-variant dark
│   ├── vite-env.d.ts                         = unchanged
│   │
│   ├── lib/
│   │   └── utils.ts                          + cn() utility (clsx + tailwind-merge)
│   │
│   ├── components/
│   │   ├── ui/                               + shadcn generated primitives
│   │   │   ├── button.tsx                    +
│   │   │   ├── input.tsx                     +
│   │   │   ├── label.tsx                     +
│   │   │   ├── select.tsx                    +
│   │   │   ├── card.tsx                      +
│   │   │   ├── badge.tsx                     +
│   │   │   ├── table.tsx                     +
│   │   │   ├── switch.tsx                    +
│   │   │   └── tooltip.tsx                   +
│   │   │
│   │   ├── layout/                           + extracted from App.tsx
│   │   │   ├── Sidebar.tsx                   + (Brand, NavItem, collapse toggle, VersionDisplay)
│   │   │   ├── Header.tsx                    + (page title, theme toggle)
│   │   │   ├── NavItem.tsx                   + (NavLink + Tooltip when collapsed)
│   │   │   ├── Brand.tsx                     + (Binoculars icon + name)
│   │   │   └── VersionDisplay.tsx            > moved from components/VersionDisplay.tsx
│   │   │
│   │   ├── inventory/                        + extracted from App.tsx
│   │   │   ├── InventoryPage.tsx             + (route handler, stats, group listing)
│   │   │   ├── DeviceCard.tsx                + (individual device display)
│   │   │   ├── StatCard.tsx                  + (updates/up-to-date/total metrics)
│   │   │   └── DeviceForm.tsx                + (add/edit form with InventoryInput)
│   │   │
│   │   ├── logs/                             + extracted from App.tsx
│   │   │   ├── LogsPage.tsx                  + (route handler, data fetching)
│   │   │   ├── LogTable.tsx                  + (shadcn Table wrapper)
│   │   │   ├── FilterBar.tsx                 + (type/status filter dropdowns)
│   │   │   └── TracebackPanel.tsx            + (expandable traceback display with copy)
│   │   │
│   │   ├── modules/                          + extracted from App.tsx
│   │   │   ├── ModulesPage.tsx               + (route handler, data fetching, mutation)
│   │   │   ├── ModuleCard.tsx                + (individual module display + FrequencyEditor integration)
│   │   │   ├── ModuleUploadForm.tsx          + (file input + upload button)
│   │   │   └── ModuleStatusBadge.tsx         + (validation status badge)
│   │   │
│   │   └── settings/                         + extracted from App.tsx
│   │       ├── SettingsPage.tsx              + (route handler, channel config)
│   │       ├── ChannelConfigForm.tsx          + (SMTP/Gotify form sections)
│   │       └── StatusMessage.tsx             + (success/error message with dismiss)
│   │
│   ├── api/                                  = preserved (no changes)
│   │   ├── client.ts                         =
│   │   ├── inventory.ts                      =
│   │   ├── modules.ts                        =
│   │   ├── checks.ts                         =
│   │   ├── schedules.ts                      =
│   │   ├── notifications.ts                  =
│   │   ├── activity.ts                       =
│   │   └── index.ts                          =
│   │
│   ├── theme/                                = preserved (no changes)
│   │   ├── ThemeProvider.tsx                 =
│   │   ├── useTheme.ts                       =
│   │   ├── resolveTheme.ts                   =
│   │   └── *.test.ts(x)                      =
│   │
│   └── App.tsx                               ~ reduced to ≤200 lines (routes + layout shell only)
│
├── e2e/                                      = preserved (selectors updated in Phase 5)
│   ├── desktop.spec.ts                       ~
│   ├── mobile.spec.ts                        ~
│   ├── theme-toggle.spec.ts                  ~
│   └── dark-mode.spec.ts                     ~
│
└── vitest.config.ts                          = (embedded in vite.config.ts, unchanged)
```

**Patterns to reuse**:
- API client pattern: `export async function listInventory(): Promise<InventoryResponse>` — each module exports typed async functions
- Test pattern: `render(<MemoryRouter><QueryClientProvider><ThemeProvider><App /></ThemeProvider></QueryClientProvider></MemoryRouter>)` + `vi.mock('../api/inventory')`
- Existing `FrequencyEditor.tsx` already uses a component-per-file pattern with explicit `Props` type export — follow this pattern for all new feature components
- `VersionDisplay.tsx` uses `React.memo` and `useRef`/`useCallback` patterns — preserve when moving to `components/layout/`

**Tests to extend**:
- `src/App.test.tsx` — import paths adjust; tests remain structurally identical (App renders routes)
- `src/components/VersionDisplay.test.tsx` — import path updated when file moves
- `src/theme/ThemeProvider.test.tsx` — no changes needed
- `src/api/*.test.ts` — no changes needed
- `e2e/desktop.spec.ts` — selectors updated for shadcn composite components
- `e2e/mobile.spec.ts` — selectors updated; mobile breakpoint behavior verified
- `e2e/theme-toggle.spec.ts` — verify dark mode toggle still applies `.dark` class
- `e2e/dark-mode.spec.ts` — verify shadcn dark variants render correctly

**Naming conventions**:
- Component files: `PascalCase.tsx`
- Test files: `ComponentName.test.tsx` (co-located with source)
- API modules: `kebab-case.ts`
- Feature directories: `kebab-case/` under `components/`
- Exported types: `PascalCase` (`DeviceGroup`, `InventoryDevice`, etc.)
- Props types: `ComponentNameProps` or inline in function signature

## Component Tree Mapping

Old patterns (inline in App.tsx) → new shadcn components:

| Old Pattern | Old Location | New Component | New Location | Migration Notes |
|-------------|-------------|---------------|--------------|-----------------|
| `function Brand()` (line 476) | App.tsx | `Brand` | `components/layout/Brand.tsx` | `bg-accent/10`→`bg-primary/10 text-primary`; icon unchanged (lucide) |
| `function NavItem()` (line 487) | App.tsx | `NavItem` | `components/layout/NavItem.tsx` | `role="tooltip"` div → `<Tooltip>` composite; NavLink preserved |
| sidebar `<aside>` (line 343-391) | App.tsx | `Sidebar` | `components/layout/Sidebar.tsx` | Contains Brand, NavItems, collapse toggle, VersionDisplay; collapse toggle `<button>` → `<Button variant="ghost" size="icon">` |
| header `<header>` (line 394-416) | App.tsx | `Header` | `components/layout/Header.tsx` | Page title preserved; theme toggle `<button>` → `<Button variant="ghost" size="icon">` |
| Theme toggle button (lines 408-415) | App.tsx — Header | Inside Header | `components/layout/Header.tsx` | Moon/Sun icons from lucide unchanged |
| `function InventoryPage()` (line 538) | App.tsx | `InventoryPage` | `components/inventory/InventoryPage.tsx` | Route handler; delegates to StatCard, DeviceForm, DeviceCard |
| `function InventoryInput()` (line 756) | App.tsx | Inline in `DeviceForm.tsx` | `components/inventory/DeviceForm.tsx` | `<label>`+`<input>` → `<Label>`+`<Input>` |
| `function StatCard()` (line 770) | App.tsx | `StatCard` | `components/inventory/StatCard.tsx` | Ad-hoc card `<div>` → `<Card>` composite; tone classes remapped |
| `function DeviceCard()` (line 802) | App.tsx | `DeviceCard` | `components/inventory/DeviceCard.tsx` | `<article>` → `<Card>`; action buttons → `<Button variant>`; unlinked badge → `<Badge variant="outline">` |
| `function VersionBlock()` (line 930) | App.tsx | Inline in `DeviceCard.tsx` | `components/inventory/DeviceCard.tsx` | Simple `div` with text — no shadcn equivalent needed |
| `function LogsPage()` (line 945) | App.tsx | `LogsPage` | `components/logs/LogsPage.tsx` | Route handler; delegates to FilterBar, LogTable |
| Filter toolbar (lines 1037-1072) | App.tsx — LogsPage | `FilterBar` | `components/logs/FilterBar.tsx` | Native `<select>` elements → `<Select>` composite |
| Activity log `<table>` (lines 1080-1221) | App.tsx — LogsPage | `LogTable` | `components/logs/LogTable.tsx` | `<table>`→`<Table>` composite; type/status pills → `<Badge variant>`; traceback panel extracted |
| Inline traceback panel (lines 1187-1211) | App.tsx — LogsPage | `TracebackPanel` | `components/logs/TracebackPanel.tsx` | Copy button → `<Button variant="ghost" size="sm">` |
| `function ModulesPage()` (line 1235) | App.tsx | `ModulesPage` | `components/modules/ModulesPage.tsx` | Route handler; delegates to ModuleUploadForm, ModuleCard |
| Module upload form (lines 1350-1371) | App.tsx — ModulesPage | `ModuleUploadForm` | `components/modules/ModuleUploadForm.tsx` | File `<input>`→`<Input type="file">`; upload button → `<Button>` |
| Individual module card (lines 1438-1534) | App.tsx — ModulesPage | `ModuleCard` | `components/modules/ModuleCard.tsx` | `<article>`→`<Card>`; FrequencyEditor integration preserved; delete button → `<Button variant="destructive">` |
| Module validation status (line 1973) | App.tsx — ModuleStatus | `ModuleStatusBadge` | `components/modules/ModuleStatusBadge.tsx` | `<span>` → `<Badge variant={status === 'valid' ? 'default' : 'destructive'}>` |
| `function ValidationSummary()` (line 1542) | App.tsx | Inline in `ModulesPage` | `components/modules/ModulesPage.tsx` | Error display; ad-hoc card → `<Card>` with `<Badge>` |
| `function SettingsPage()` (line 1568) | App.tsx | `SettingsPage` | `components/settings/SettingsPage.tsx` | Route handler; delegates to ChannelConfigForm |
| SMTP/Gotify form sections (lines 1751-1951) | App.tsx — SettingsPage | `ChannelConfigForm` | `components/settings/ChannelConfigForm.tsx` | Form `<input>`→`<Input>`; checkbox `<input>`→`<Input type="checkbox">`+`<Label>`; Save/Test buttons → `<Button>`; sections → `<Card>` |
| Status message (lines 1737-1749) | App.tsx — SettingsPage | `StatusMessage` | `components/settings/StatusMessage.tsx` | `<div>`→ shadcn styled alert |
| `function PageHeader()` (line 1955) | App.tsx | Shared inline or extracted | `components/layout/` or inline in feature pages | Simple heading — inline in each page or extracted as shared |
| `function TableHead()` (line 1964) | App.tsx | Replaced by shadcn `<TableHead>` | N/A (shadcn Table provides this) | shadcn `<TableHead>` is the primitives' equivalent |
| `FrequencyEditor` custom toggle (lines 186-215) | `components/FrequencyEditor.tsx` | `<Switch>`+`<Label>` | Modified in existing `FrequencyEditor.tsx` | `role="switch"` button → `<Switch>`; preset radio buttons → `<Button variant="outline">` row (shadcn doesn't ship a radio group — use styled buttons) |
| Mobile menu overlay (lines 334-341) | App.tsx — sidebar overlay | Moved to `Sidebar.tsx` | `components/layout/Sidebar.tsx` | z-index token applied (see AD-005) |

## Implementation Phases

### Phase A — Dependency & Toolchain Upgrade (OBJ1, TR-001, TR-002, TR-003)
**Goal**: Bootstrap the new toolchain without changing any product code.

**Steps**:
1. **Measure baseline**: Record `npm run build` output size and Lighthouse score for comparison in Phase E.
2. **Bump dependencies**: `npm install react@^19 react-dom@^19` + bump `@types/react`, `@types/react-dom` to v19. Update `vite` to latest (v6+), `@vitejs/plugin-react` to latest, `@tanstack/react-query` to ^5, react-router-dom to ^7, lucide-react to latest.
3. **Add `@tailwindcss/upgrade` codemod**: `npm install -D @tailwindcss/upgrade` (temporary — for codemod run only).
4. **Run codemod**: `npx @tailwindcss/upgrade` — this reads `tailwind.config.ts` and migrates `darkMode: 'class'` to `@custom-variant dark`, converts `rgb(var(--color-*) / <alpha-value>)` patterns, and updates deprecated Tailwind v3 utility names. Output stored in `index.css`.
5. **Install `@tailwindcss/vite`**: `npm install -D @tailwindcss/vite`.
6. **Rewrite `vite.config.ts`**: Add `import tailwindcss from '@tailwindcss/vite'` and include in `plugins: [tailwindcss(), react()]`. Keep existing server proxy and test config.
7. **Rewrite `index.css`**: Replace `@tailwind base/components/utilities` with `@import "tailwindcss"`. Add `@theme` block with font families and custom shadows from `tailwind.config.ts`. Add `@custom-variant dark (&:is(.dark *))`. Remove the `@media (prefers-reduced-motion)` block (v4 handles this automatically).
8. **Delete `tailwind.config.ts` and `postcss.config.js`**: Only after codemod has successfully run and v4 output is verified.
9. **Add `@/` path alias**: In `tsconfig.app.json`, add `"paths": { "@/*": ["./src/*"] }`. In `vite.config.ts`, add `resolve: { alias: { '@': '/src' } }` (Vite needs this for runtime resolution even though tsc uses `paths` for type-checking).
10. **Gate check**: `npm run dev` starts without errors; `npm run build` succeeds (expecting visual breakage but zero build errors); `npm run typecheck` passes.

**Gate: Phase A complete when** `npm run build` exits 0 and `npm run dev` shows the app loading (visual regressions expected but no white screen).

---

### Phase B — Bootstrap shadcn/ui (OBJ2, OBJ4 partial, TR-004, TR-005, TR-008)
**Goal**: Initialize shadcn and generate all needed UI primitives.

**Steps**:
1. **Pin shadcn version**: `npm install -D shadcn@^2.0.0` (pinned per spec).
2. **Run init**: `npx shadcn@2.x.x init` with answers: TypeScript=yes, framework=Vite, style=New York, base color=Zinc, CSS variables=yes, alias=`@/→frontend/src/`.
3. **Configure primary color**: In the generated `index.css` shadcn section, set `--primary: 221.2 83.2% 53.3%` and `--primary-foreground: 210 40% 98%`.
4. **Verify `components.json`**: Check that `style`, `baseColor`, `aliases`, and `tailwind.css` / `cssVariables` keys are present and correct.
5. **Verify `lib/utils.ts`**: Confirm `cn()` exports from `frontend/src/lib/utils.ts` and uses `clsx` + `tailwind-merge`.
6. **Generate components**: 
   ```bash
   npx shadcn add button input label select card badge table switch tooltip
   ```
   This creates `components/ui/{button,input,label,select,card,badge,table,switch,tooltip}.tsx` and installs Radix primitives and dependencies (`@radix-ui/react-select`, `@radix-ui/react-switch`, `@radix-ui/react-tooltip`, `class-variance-authority`, `clsx`, `tailwind-merge`, `tw-animate-css`).
7. **Gate check**: `cn('px-4', 'px-2')` returns `'px-2'` (test in browser console or vitest); `npm run dev` starts with shadcn CSS vars loading; `bg-primary` class renders blue.

**Gate: Phase B complete when** `components/ui/` has all 9 generated files, `cn()` works, and shadcn CSS vars are present in `index.css`.

---

### Phase C — Color Token Migration (OBJ3, TR-006, TR-007)
**Goal**: Remove all custom `--color-*` tokens and `motion-safe:` prefixes. All classes now reference shadcn standard colors.

**Steps**:
1. **Remove `motion-safe:` prefixes**: Run `sed -i 's/motion-safe://g' src/**/*.tsx src/**/*.ts` to strip all `motion-safe:` prefixes. Tailwind v4 already respects `prefers-reduced-motion`.
2. **Systematic color remapping** — edit each source file:

   | Search Pattern | Replace With |
   |---------------|--------------|
   | `bg-surface` | `bg-background` |
   | `hover:bg-surface-hover` | `hover:bg-muted` |
   | `bg-panel` | `bg-card` |
   | `hover:bg-panel-hover` | `hover:bg-muted` |
   | `text-ink` | `text-foreground` |
   | `hover:text-ink-hover` | `hover:text-foreground` (or keep as `text-foreground` — hover provides contrast via background) |
   | `text-muted` | `text-muted-foreground` |
   | `text-ink-disabled` | `text-muted-foreground/50` |
   | `border-panel` | `border` |
   | `border-muted` | `border` |
   | `hover:border-muted-hover` | `hover:border-foreground/20` |
   | `bg-accent` (buttons/actions) | `bg-primary` |
   | `text-accent` | `text-primary` |
   | `hover:bg-accent-hover` | `hover:bg-primary/90` |
   | `hover:text-accent-hover` | `hover:text-primary` |
   | `bg-accent/10` | `bg-primary/10` |
   | `bg-accent/20` | `bg-primary/20` |
   | `focus:ring-accent-focus/20` | `focus:ring-ring/20` |
   | `focus:ring-accent-focus/40` | `focus:ring-ring/40` |
   | `focus:border-accent` | `focus:border-primary` |
   | `text-accent` (indigo accent for icon container) | `text-primary` |
   | `border-error-border` | `border-destructive/30` |
   | `bg-error-bg` | `bg-destructive/10` |
   | `text-error` | `text-destructive` |
   | `bg-success-bg` | `bg-emerald-50 dark:bg-emerald-950` |
   | `text-success` | `text-emerald-600 dark:text-emerald-400` |
   | `border-success-border` | `border-emerald-200 dark:border-emerald-800` |
   | `bg-warning-bg` | `bg-amber-50 dark:bg-amber-950` |
   | `text-warning` | `text-amber-700 dark:text-amber-300` |
   | `border-warning-border` | `border-amber-200 dark:border-amber-800` |
   | `to-gradient-edge/50` | `to-background/50` |
   | `indigo` tone (StatCard, section icons) | `bg-primary/10 text-primary` |
   | `bg-slate-950` (traceback container) | `bg-zinc-950` (Zinc base) |
   | `text-slate-*` | `text-zinc-*` (match Zinc base) |
   | `border-slate-*` | `border-zinc-*` |
   | `bg-muted` (FrequencyEditor toggle off state) | `bg-muted` (shadcn `--muted` is now a proper color) |
   | `bg-emerald-600/10 text-emerald-600` | `bg-emerald-500/10 text-emerald-500` |

3. **Remove all `--color-*` CSS blocks**: In `index.css`, delete the entire `/* ── Theme Token System ── */` section (lines 7-110), including the `:root` and `:root.dark` blocks. Shadcn's `@layer base { :root { ... } }` now provides all color tokens.
4. **Update base `body` styles**: Replace `background: rgb(var(--color-surface)); color: rgb(var(--color-ink))` with `@apply bg-background text-foreground`.
5. **Update shadow colors**: Replace `dark:shadow-[0_0_15px_rgb(var(--color-error-border)/0.12)]` with `dark:shadow-[0_0_15px_hsl(var(--destructive)/0.12)]`.
6. **Gate check — grep verification**:
   ```bash
   grep -rn 'bg-surface\|text-ink\|border-panel\|bg-accent\|text-muted\|motion-safe:' src/ && echo "FAIL: found old patterns" || echo "PASS: all patterns migrated"
   grep -rn '\-\-color-' src/index.css && echo "FAIL: found --color- tokens" || echo "PASS: all --color- tokens removed"
   ```
7. **Visual spot-check**: Run `npm run dev` and verify main pages render without broken colors. Both light and dark modes should reflect shadcn Zinc + blue primary theme.

**Gate: Phase C complete when** both grep commands return PASS and `npm run build` succeeds.

---

### Phase D — Adopt shadcn Components (OBJ4, TR-009)
**Goal**: Replace all ad-hoc HTML patterns with shadcn generated components. This is the most labor-intensive phase — it touches every component in App.tsx and the existing extracted components.

**Steps** (recommended order — handle one section at a time and verify build after each):

#### D.1 — Layout Components (low risk, no user interaction changes)
1. **Theme toggle** (in Header): `<button>` → `<Button variant="ghost" size="icon">`. Import `Button` from `@/components/ui/button`.
2. **Sidebar collapse toggle**: Same pattern — `<Button variant="ghost" size="icon">`.
3. **Mobile hamburger**: `<Button variant="ghost" size="icon">`.
4. **NavItem tooltip**: Replace `role="tooltip"` div → `<TooltipProvider>` + `<Tooltip>` + `<TooltipTrigger>` + `<TooltipContent>`. The existing `group-hover:visible`/`group-focus-visible` pattern is replaced by Radix's built-in hover/focus behavior.
5. **VersionDisplay tooltip**: Replace manual tooltip state management → `<Tooltip>` composite. Remove `tooltipVisible`, `showTooltip`, `hideTooltip` state and refs.

#### D.2 — Inventory Page
1. **"Add Device" / "Check All" buttons**: `<Button variant="outline">` for secondary actions, `<Button>` (default/primary) for primary actions.
2. **Form `<input>` fields** (DeviceForm): Replace `InventoryInput` `<label>`+`<input>` with `<Label htmlFor={id}>` + `<Input id={id}>`.
3. **Form `<select>`** (Module dropdown): Replace with `<Select>` composite — `<SelectTrigger>`, `<SelectValue>`, `<SelectContent>`, `<SelectItem>`.
4. **Form action buttons** (Add/Save/Cancel): `<Button>` variants.
5. **Error/success/warning messages**: Keep as `<div>` with shadcn color classes (mapped in Phase C). Optional: use `<Alert>` / `<AlertDescription>` pattern later.
6. **StatCard**: Wrap in `<Card>` composite — `<CardContent className="flex items-center justify-between">`.
7. **DeviceCard**: `<article>` → `<Card>` composite; header → `<CardHeader>`, content → `<CardContent>`, footer → `<CardFooter>`. Action buttons → `<Button variant="outline" size="sm">`. "Sync Local" button → `<Button variant="default" size="sm">`. Unlinked badge → `<Badge variant="outline">`.
8. **Status pills**: `<Badge variant="default">` for success, `<Badge variant="destructive">` for error, `<Badge variant="secondary">` for neutral.
9. **Inline manual result**: Keep as a custom block within `<CardContent>` — no shadcn component directly maps.

#### D.3 — Logs Page
1. **Filter `<select>` elements**: Replace both (type filter, status filter) with `<Select>` composites.
2. **Refresh button**: `<Button variant="outline">`.
3. **Log table**: Replace `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` with `<Table>`, `<TableHeader>`, `<TableBody>`, `<TableRow>`, `<TableHead>`, `<TableCell>`.
4. **Type/Status pills** in table cells: `<Badge variant="secondary">` (type) and `<Badge variant="default">` or `<Badge variant="destructive">` (status).
5. **Expand/collapse chevron button**: `<Button variant="ghost" size="icon">`.
6. **Copy button** in traceback panel: `<Button variant="outline" size="sm">`.

#### D.4 — Modules Page
1. **Upload form**: File `<input>` → `<Input type="file">`; Upload button → `<Button variant="outline">`.
2. **Warning banner**: Keep as `<div>` with warning classes (mapped in Phase C).
3. **ModuleCard**: `<article>` → `<Card>` composite. Icon container → keep as custom `<div>` inside `<CardContent>`. Module status → `<Badge>`. Delete button → `<Button variant="destructive" size="sm">`.
4. **Frequency display** (schedule): The `<span>` pill with `<Clock>` icon and "Active/Paused" indicator → use shadcn `<Badge variant="outline">` for the frequency label and `<Badge variant="default">`/`<Badge variant="secondary">` for active/paused status.
5. **FrequencyEditor toggle**: Replace `role="switch"` `<button>` → `<Switch>` + `<Label htmlFor>`. The existing keyboard handling (`onKeyDown` for Space/Enter) is handled by Radix Switch.
6. **FrequencyEditor preset buttons** (radio group): Keep as styled `<Button>` row (`variant="outline"` for unselected, `variant="default"` for selected). The `role="radiogroup"` / `role="radio"` / `aria-checked` pattern persists for accessibility — shadcn doesn't ship a RadioGroup in the base set.
7. **FrequencyEditor action buttons** (Cancel/Save): `<Button variant="outline">` and `<Button>`.

#### D.5 — Settings Page
1. **All form `<input>` fields** (SMTP host, port, username, password, mail from, mail to, Gotify URL, token): Replace with `<Label htmlFor>` + `<Input id>`.
2. **Checkboxes** (SMTP enabled, TLS, Gotify enabled): Replace `<input type="checkbox">` with `<Input type="checkbox" id={id}>` + `<Label htmlFor={id}>`. Note: shadcn Input with type="checkbox" renders a native checkbox styled with shadcn classes.
3. **Save/Test buttons**: `<Button variant="default">` (Save) and `<Button variant="outline">` (Test).
4. **Status message**: Custom component or use `<Alert>` / `<AlertDescription>`.
5. **Channel config sections** (SMTP, Gotify): Wrap each in `<Card>` composite — `<CardHeader>` for title + enable checkbox, `<CardContent>` for form fields, `<CardFooter>` for action buttons.
6. **Section icons**: `text-indigo-500` → `text-primary` (mapped in Phase C).

#### D.6 — Final Cleanup
1. **Audit for `role="radiogroup"` / `role="switch"` patterns**: The FrequencyEditor preset buttons (radio group) and the old toggle are replaced. Verify no custom `role="radiogroup"` or `role="switch"` patterns remain.
2. **Check for stray ad-hoc `<button>` elements with Tailwind classes**: grep for `<button` and verify each uses `<Button>` or is a justified exception (e.g., form submit buttons are `<Button>`).
3. **Check for native `<select>` elements**: grep for `<select` and verify zero remain.

**Gate: Phase D complete when** grep finds zero ad-hoc `<button className=` with Tailwind, zero native `<select>`, and all pages render correct shadcn-styled components. `npm run build` and `npm run typecheck` pass.

---

### Phase E — Decompose App.tsx + Verify (OBJ5, OBJ6, TR-010, TR-011)
**Goal**: Extract all inline components into their feature directories, reduce App.tsx to ≤200 lines, and verify all quality gates.

**Steps**:

#### E.1 — Extraction (order matters — start from leaf components, work up)
1. **Extract shared utilities**: `PageHeader` (can stay inline in each page or become a tiny shared component — 4 lines, not worth extracting alone). `ModuleStatus` → `components/modules/ModuleStatusBadge.tsx`.
2. **Extract layout components**:
   - `Brand` → `components/layout/Brand.tsx` (lines 476-485)
   - `NavItem` → `components/layout/NavItem.tsx` (lines 499-535, already fairly self-contained)
   - `Sidebar` → `components/layout/Sidebar.tsx` (the entire `<aside>` block, lines 343-391, including Brand, NavItem loop, collapse toggle, VersionDisplay)
   - `Header` → `components/layout/Header.tsx` (the `<header>` block, lines 394-416)
   - Move `VersionDisplay.tsx` from `components/` to `components/layout/`
3. **Extract inventory components**:
   - `DeviceForm` → `components/inventory/DeviceForm.tsx` (the form block, lines 629-695, including `InventoryInput` inline)
   - `StatCard` → `components/inventory/StatCard.tsx` (lines 770-799)
   - `DeviceCard` → `components/inventory/DeviceCard.tsx` (lines 802-915, includes `VersionBlock` inline and `displayStatus`)
   - `InventoryPage` → `components/inventory/InventoryPage.tsx` (lines 538-754)
4. **Extract log components**:
   - `FilterBar` → `components/logs/FilterBar.tsx` (the filter toolbar, lines 1037-1072)
   - `TracebackPanel` → `components/logs/TracebackPanel.tsx` (lines 1187-1211)
   - `LogTable` → `components/logs/LogTable.tsx` (the table + scroll gradient, lines 1080-1221)
   - `LogsPage` → `components/logs/LogsPage.tsx` (lines 945-1225)
5. **Extract module components**:
   - `ModuleUploadForm` → `components/modules/ModuleUploadForm.tsx` (lines 1350-1371)
   - `ModuleCard` → `components/modules/ModuleCard.tsx` (lines 1438-1534, includes FrequencyEditor integration)
   - `ModulesPage` → `components/modules/ModulesPage.tsx` (lines 1235-1540)
6. **Extract settings components**:
   - `StatusMessage` → `components/settings/StatusMessage.tsx` (lines 1737-1749)
   - `ChannelConfigForm` → `components/settings/ChannelConfigForm.tsx` (the SMTP + Gotify card sections, lines 1753-1951)
   - `SettingsPage` → `components/settings/SettingsPage.tsx` (lines 1568-1953)

#### E.2 — Wire up App.tsx
After extraction, App.tsx should contain only:
- State declarations (all useState hooks)
- Handler functions (all async handlers)
- `useMemo`/`useEffect`/`useCallback` hooks
- `useTheme()` hook
- `useLocation()` hook
- `closeMobileMenu` callback
- JSX: `<div className="min-h-screen bg-background text-foreground">` → `<Sidebar>` + `<Header>` + `<main>` with `<Routes>`
- Each `<Route>` passes props to the extracted page component

Target: ≤200 lines. Verify with `wc -l src/App.tsx`.

#### E.3 — Fix import paths
- All internal imports use `@/` alias: `@/components/ui/button`, `@/components/layout/Sidebar`, `@/api`, `@/theme/useTheme`, etc.
- Run `npm run typecheck` after each extraction block to catch import path errors early.

#### E.4 — Update tests
1. **Unit tests**: Update `App.test.tsx` import paths. If specific components were tested via App rendering, those tests still work. Add component-level tests for extracted components if coverage is below threshold.
2. **Playwright E2E tests**: Update selectors to target shadcn composite elements:
   - `button` → `button` (shadcn Button renders as `<button>`, selectors may need `[data-slot]` attributes or accessible roles)
   - `select` → `button[role="combobox"]` (shadcn Select renders a custom trigger, not native `<select>`)
   - Table elements: shadcn Table uses standard `<table>`, `<th>`, `<td>` — selectors largely unchanged
   - Card: use `role="article"` or data attributes if needed
   - Switch: `button[role="switch"]`
   - Checkbox: `input[type="checkbox"]`
   - Tooltip: `div[role="tooltip"]`
3. **Update Playwright visual baselines**: Run `npx playwright test --update-snapshots` to accept visual changes from the UI migration.

#### E.5 — Verify quality gates
1. `npm run typecheck` — zero errors
2. `npm run lint` — zero errors
3. `npm test` — all pass
4. `npm run test:e2e` — all pass (with updated baselines)
5. Run axe-core accessibility scan on all 4 routes in both light and dark modes:
   ```typescript
   // In Playwright test or separate script
   import { test, expect } from '@playwright/test';
   import AxeBuilder from '@axe-core/playwright';
   
   for (const route of ['/inventory', '/logs', '/modules', '/settings']) {
     test(`axe scan ${route}`, async ({ page }) => {
       await page.goto(route);
       const results = await new AxeBuilder({ page }).analyze();
       expect(results.violations.filter(v => v.impact === 'critical' || v.impact === 'serious')).toEqual([]);
     });
   }
   ```
6. Lighthouse audit: Run against production build
7. Bundle size comparison: Compare `dist/assets/*.js` total size against Phase A baseline. Must be ≤110%.

**Gate: Phase E complete when** `.qc-passed` marker is created — all 8 success criteria from the spec are met.

## Implementation Hints

- **[HINT-001] Order Dependency**: The `@tailwindcss/upgrade` codemod MUST run while `tailwind.config.ts` still exists. If the config is deleted first, the codemod cannot migrate non-standard color spaces, font families, or inline opacity modifiers. After codemod completes and output is verified, then delete both `tailwind.config.ts` and `postcss.config.js`.
- **[HINT-002] Breakage Cascade**: Phase C (color token migration) causes the most visual breakage. All custom `--color-*` class names (e.g., `bg-surface`, `text-ink`) become unknown Tailwind utilities after removing the custom color definitions. Replace ALL color classes BEFORE starting Phase D (component adoption), or the app will have broken styling on intermediate commits.
- **[HINT-003] shadcn Select Migration Complexity**: The shadcn `<Select>` composite replaces native `<select>` with a Radix-based custom dropdown. This requires rewriting every dropdown from a simple `<select>` + `<option>` JSX block to `<Select>` + `<SelectTrigger>` + `<SelectContent>` + `<SelectItem>`. Additionally, Playwright selectors that target `select` elements must be updated to target `button[role="combobox"]`. Plan for this to be the most time-consuming single replacement in Phase D (inventory module dropdown, two log filter dropdowns).
- **[HINT-004] Tooltip Provider Requirement**: shadcn's `<Tooltip>` component requires a `<TooltipProvider>` ancestor. Add it once in `main.tsx` wrapping the entire app tree (similar to how `<QueryClientProvider>` wraps), or locally in `Sidebar` wrapping only the collapsed nav items. The `delayDuration` prop on `<TooltipProvider>` can replace the existing 200ms delay on `VersionDisplay` and the CSS `delay-200` on `NavItem` tooltips.
- **[HINT-005] z-index Audit in Sidebar Layout**: The sidebar uses `z-50` (sidebar), `z-40` (overlay), `z-30` (header). shadcn Select dropdowns and Tooltip popovers also use `z-50` by default. When the sidebar is open, Select dropdowns originating inside `<main>` should appear above the sidebar — this works because `<main>` is later in the DOM and the sidebar is `fixed`. However, when testing, verify that Select dropdowns and Tooltips inside the sidebar itself (NavItem tooltips, FrequencyEditor interactions) layer correctly. If conflicts arise, define CSS custom properties `--z-sidebar: 40`, `--z-header: 30`, `--z-overlay: 50`, `--z-tooltip: 60` in the `@theme` block and apply them to respective elements.

## Success Criteria Mapping

| SC ID | Description | Verification Method | Phase Gate |
|-------|-------------|---------------------|------------|
| SC-001 | `npm run build` succeeds with zero errors | Run `npm run build` | Phase A+ |
| SC-002 | `cn('px-4', 'px-2')` outputs `'px-2'` | vitest unit test on `lib/utils.ts` | Phase B |
| SC-003 | Zero `bg-surface`, `text-ink`, `border-panel`, `bg-accent`, `text-muted`, `motion-safe:` in source AND zero `--color-` in CSS | grep verification script | Phase C |
| SC-004 | Zero ad-hoc `<button className=` Tailwind; zero native `<select>`; zero un-replaced card/table/badge/switch/tooltip | grep + manual review | Phase D |
| SC-005 | App.tsx ≤200 lines | `wc -l src/App.tsx` | Phase E |
| SC-006 | `npm test`, `npm run test:e2e`, `npm run typecheck`, `npm run lint` all pass | Run all commands | Phase E |
| SC-007 | axe-core scan passes 0 critical/serious violations | Automated axe-core in Playwright | Phase E |
| SC-008 | Lighthouse ≥90; bundle ≤110% baseline | Lighthouse CLI + bundle size comparison | Phase E |
