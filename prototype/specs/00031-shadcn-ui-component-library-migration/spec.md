---
feature_branch: "00031-shadcn-ui-component-library-migration"
created: "2026-06-08"
input: "E030 Shadcn UI Component Library Migration"
spec_type: "technical"
spec_maturity: "clarified"
epic_id: "E030"
epic_sources: "{SAD:ADR-0003}"
---

# Feature Specification: Shadcn UI Component Library Migration

**Feature Branch**: `00031-shadcn-ui-component-library-migration`  
**Created**: 2026-06-08  
**Status**: Draft  
**Spec Type**: technical  
**Spec Maturity**: clarified  
**Epic ID**: E030  
**Epic Sources**: {SAD:ADR-0003}

## Problem Statement

The Binocular frontend is a 1981-line monolithic `App.tsx` with ad-hoc Tailwind class patterns repeated on every element — no reusable component abstractions. A custom color token system (`--color-surface`, `--color-ink`, `--color-accent`) duplicates standard theming. The stack (React 18, Tailwind 3.4, PostCSS) is behind latest stable. Without migration to a standardized component library, every UI change requires fragile class-string edits, and accessibility/composability regressions are inevitable.

## Scope

### Included

- Upgrade: React 19, TypeScript 5.x, Vite 6, React Router 7, TanStack Query 5, lucide-react, vitest, Playwright, testing libraries
- Tailwind v3→v4 CSS-first (`@tailwindcss/vite`, `@import "tailwindcss"`, drop PostCSS/autoprefixer)
- Bootstrap shadcn/ui (New York, Zinc base, blue primary `221.2 83.2% 53.3%`) with Radix primitives, `class-variance-authority`, `clsx`, `tailwind-merge`, `tw-animate-css`
- Remove custom `--color-*` token system; map all classes to shadcn standard colors
- Generate shadcn components (Button, Input, Label, Select, Card, Badge, Table, Switch, Tooltip) via CLI; replace all ad-hoc patterns including checkboxes/radio groups and FrequencyEditor toggles
- Decompose App.tsx into `components/{ui,inventory,logs,modules,settings,layout}/`
- Verify all tests pass (vitest, Playwright, tsc strict, eslint, axe-core accessibility scan)

### Excluded

ThemeProvider rewrite (`.dark` toggling already compatible), backend changes, new features, visual redesign, CI/CD/Dockerfile changes, React Router v7 data-router API adoption (keep existing `<Routes>/<Route>` pattern).

### Edge Cases

- `@tailwindcss/upgrade` codemod runs BEFORE deleting `tailwind.config.ts`; codemod needs v3 config to migrate font families, shadows, colors
- React 19 makes `forwardRef` optional (not removed); existing usage remains valid; `@types/react` v19 changes addressed
- `motion-safe:` prefixes removed (v4 honors `prefers-reduced-motion`); `to-gradient-edge/50`→`to-background/50`
- Font families (Nunito Sans, JetBrains Mono) preserved via CSS `@theme { --font-sans: ...; --font-mono: ...; }` in index.css; Google Fonts `@import` kept at top
- Custom `shadow-quiet` preserved via CSS `@theme { --shadow-quiet: ...; }`
- Test selectors updated for shadcn composites; Playwright baselines updated (acceptable)
- shadcn CLI version pinned to ensure reproducible migration (added as devDependency)
- z-index conflicts between sidebar (z-50/40/30) and shadcn components audited and reconciled during migration

## Technical Objectives

### Objective 1 - Dependency & Toolchain Upgrade (P1)

Bump all deps to latest stable and migrate Tailwind v3→v4 CSS-first config.

**Why this priority**: Foundation — shadcn requires Tailwind v4 and React 19.

**Deliverables**: Updated `package.json`; `vite.config.ts` with `@tailwindcss/vite`; `index.css` with `@import "tailwindcss"` plus `@theme` block for font families and custom shadows; deleted `tailwind.config.ts` (after codemod) and `postcss.config.js`; `tsconfig.app.json` with `@/*` alias.

**Validation**: `npm run dev` starts; existing utilities apply without regressions; `npm run build` succeeds.

### Objective 2 - Bootstrap shadcn/ui (P1)

Init shadcn/ui (New York, Zinc, blue primary) with CSS variables and `cn()` utility. Remove all custom `--color-*` token blocks.

**Why this priority**: Theming foundation all components inherit.

**Deliverables**: `npx shadcn@2.x.x init` (pinned version, TS=yes, Vite, New York, Zinc, CSS vars=yes, alias `@/→frontend/src/`); `lib/utils.ts` with `cn()`; `components.json`; CSS vars (background, foreground, primary, muted, card, accent, destructive, border, input, ring, radius); `@custom-variant dark (&:is(.dark *))`; removed all `--color-*` custom property blocks from `:root` and `:root.dark`.

**Validation**: `cn('px-4', 'px-2')`→`'px-2'`; `bg-primary` renders blue; dark mode applies via existing ThemeProvider.

### Objective 3 - Color Token Migration (P1)

Map all custom color classes to shadcn standards: `bg-surface`→`bg-background`, `bg-panel`/`hover:bg-panel-hover`→`bg-card`/`hover:bg-muted`, `text-ink`/`hover:text-ink-hover`→`text-foreground`, `text-muted`→`text-muted-foreground`, `border-panel`/`border-muted`→`border`, `bg-accent`/`text-accent`→`bg-primary`/`text-primary`/`hover:bg-primary/90`, `focus:ring-accent-focus/20`→`focus:ring-ring/20`, error→`bg-destructive/10`+`border-destructive/30`+`text-destructive`, success→emerald, warning→amber, `text-ink-disabled`→`opacity-50` or `text-muted-foreground/50`, `to-gradient-edge/50`→`to-background/50`, indigo stat tone→`bg-primary/10 text-primary`. Remove all `motion-safe:` prefixes.

**Why this priority**: Must complete before component replacement.

**Validation**: Zero occurrences of `bg-surface`, `text-ink`, `border-panel`, `bg-accent`, `text-muted`, `motion-safe:` in source files; zero `--color-` declarations in CSS files.

### Objective 4 - Generate & Adopt shadcn Components (P1)

Generate via CLI (`button`, `input`, `label`, `select`, `card`, `badge`, `table`, `switch`, `tooltip`). Replace all ad-hoc patterns: buttons→`<Button variant size>`, InventoryInput→`<Label>`+`<Input>`, `<select>`→`<Select>` composite, DeviceCard/StatCard→`<Card>` composite (CardHeader/CardContent/CardFooter), status pills→`<Badge variant>`, activity log `<table>`→`<Table>` composite, theme toggle→`<Button ghost icon>`, collapsed sidebar→`<Tooltip>`, scheduler toggle→`<Switch>`+`<Label>`, file input→`<Input type="file">`, checkboxes→styled `<Input type="checkbox">` with `<Label>`, radio groups→shadcn-compatible styled inputs, FrequencyEditor→`<Switch>`.

**Why this priority**: Core deliverable — eliminates ad-hoc markup, establishes accessible primitives.

**Validation**: Zero ad-hoc `<button>` with Tailwind classes; zero native `<select>` elements; zero un-replaced card/table/badge/switch/tooltip patterns; no custom role="radiogroup"/"switch" patterns in source.

### Objective 5 - Decompose App.tsx (P2)

Extract into `components/ui/` (shadcn primitives), `components/inventory/` (InventoryPage, DeviceCard, StatCard, DeviceForm), `components/logs/` (LogsPage, LogTable, FilterBar, TracebackPanel), `components/modules/` (ModulesPage, ModuleUploadForm, ScheduleEditor), `components/settings/` (SettingsPage, ChannelConfigForm), `components/layout/` (Sidebar, Header, NavItem, Brand, VersionDisplay). App.tsx reduced to routes + layout (≤200 lines).

**Why this priority**: Maintainability — decomposition enables independent testing; doesn't block component migration.

**Validation**: All routes render full functionality; App.tsx ≤200 lines.

### Objective 6 - Verify Tests & Functionality (P1)

All `npm test`, `npm run test:e2e`, `npm run typecheck`, `npm run lint` pass. axe-core automated scan passes with zero critical/serious violations. Lighthouse performance ≥90. Bundle size not regressed >10%. All functionality preserved: theme toggle, sidebar, inventory CRUD, manual/bulk checks, module upload/delete, schedule editing, activity log filtering, settings channel config, brand/version display.

**Why this priority**: Zero-regression gate.

**Validation**: All quality-gate commands exit code 0; axe-core scan passes; Lighthouse score verified.

### Technical Constraints

No product capability changes. Docker multi-stage build must continue. `@/→frontend/src/`; `@import "tailwindcss"` before `@custom-variant`. `"jsx": "react-jsx"` (present). `components.json` uses CSS file for v4. shadcn CLI version pinned for reproducibility. z-index stack audited during migration.

## Integration Points

- **IP-001**: shadcn `@custom-variant dark` ↔ ThemeProvider (E003) `.dark` — no changes
- **IP-002**: API clients from E003/E005/E008/E010/E012/E014 unchanged; routes preserved using `<Routes>/<Route>` component-tree pattern; `VITE_APP_VERSION` from E029 preserved

## Requirements

- **TR-001**: Upgrade to React 19.x, `@types/react`/`@types/react-dom` v19
- **TR-002**: Run `@tailwindcss/upgrade` codemod BEFORE deleting `tailwind.config.ts`; migrate Tailwind v3→v4 via `@tailwindcss/vite`, `@import "tailwindcss"`, delete `tailwind.config.ts` (after codemod) and `postcss.config.js`
- **TR-003**: Preserve custom font families (Nunito Sans, JetBrains Mono) via CSS `@theme { --font-sans: ...; --font-mono: ...; }` in index.css; preserve `shadow-quiet` via CSS `@theme { --shadow-quiet: ...; }`
- **TR-004**: Init shadcn/ui with pinned version (TS=yes, Vite, New York, Zinc, CSS vars=yes, alias `@/→frontend/src/`)
- **TR-005**: Configure blue primary (`--primary: 221.2 83.2% 53.3%`, `--primary-foreground: 210 40% 98%`)
- **TR-006**: Remove all `--color-*` CSS blocks; map custom classes to shadcn standard colors including indigo→primary
- **TR-007**: Remove all `motion-safe:` prefixes
- **TR-008**: Generate shadcn components: button, input, label, select, card, badge, table, switch, tooltip
- **TR-009**: Replace ad-hoc `<button>`→`<Button>`, `<select>`→`<Select>`, cards→`<Card>`, badges→`<Badge>`, `<table>`→`<Table>`, toggle→`<Switch>`, checkboxes→`<Input type="checkbox">`+`<Label>`, FrequencyEditor toggles→`<Switch>`
- **TR-010**: Decompose App.tsx into `components/{inventory,logs,modules,settings,layout}/`; App.tsx ≤200 lines
- **TR-011**: Pass vitest, Playwright E2E, tsc strict, eslint all with zero errors; axe-core scan zero critical/serious; Lighthouse ≥90; bundle ≤110% of baseline

### Key Entities

- **shadcn Primitives**: Button, Input, Label, Select (Trigger/Content/Item), Card (Header/Content/Footer), Badge, Table (Header/Body/Row/Cell/Head), Switch, Tooltip (Trigger/Content)
- **CSS Variables**: shadcn OKLCH — `--background`, `--foreground`, `--primary`, `--primary-foreground`, `--muted`, `--muted-foreground`, `--card`, `--card-foreground`, `--accent`, `--accent-foreground`, `--destructive`, `--destructive-foreground`, `--border`, `--input`, `--ring`, `--radius`
- **CSS @theme Block**: Tailwind v4 configuration for custom fonts, shadows, and z-index tokens placed in `index.css`
- **cn()** (`lib/utils.ts`): `clsx` + `tailwind-merge` class utility
- **Feature Modules**: components under `inventory/`, `logs/`, `modules/`, `settings/`, `layout/`
- **components.json**: shadcn CLI config recording base color, style, aliases, and pinned CLI version

## Assumptions & Risks

**Assumptions**: `@tailwindcss/upgrade` handles most renames; ThemeProvider `.dark` compatible with `@custom-variant dark`; API contracts unchanged; `@/` alias doesn't break imports; RTL compatible with React 19; shadcn pinned version's generated components remain stable.

**Risks**: Playwright visual drift (high/low — baselines accepted); Radix type edges (medium/medium — `skipLibCheck` fallback); codemod misses RGB patterns (low/medium — manual fix); bundle size increase from Radix deps may exceed 10% threshold (medium/medium — monitored by SC-011).

## Implementation Signals

- `NEW-UI` — shadcn primitives under `components/ui/`
- `MIGRATION` — Tailwind v3→v4, custom tokens→CSS vars, class remapping
- `BREAKING-CHANGE` — `--color-*` removed; `forwardRef` made optional; deprecated classes gone
- `NEW-CONFIG` — `components.json`, `@tailwindcss/vite`, `@/` alias, `@custom-variant dark`, `@theme` block

## Success Criteria

- **SC-001 [OBJ1]**: `npm run build` succeeds with zero errors
- **SC-002 [OBJ2]**: `cn('px-4', 'px-2')` outputs `'px-2'`
- **SC-003 [OBJ3]**: Zero `bg-surface`, `text-ink`, `border-panel`, `bg-accent`, `text-muted`, `motion-safe:` in source files AND zero `--color-` declarations in CSS files
- **SC-004 [OBJ4]**: Zero ad-hoc `<button>` Tailwind; zero native `<select>`; zero un-replaced card/table/badge/switch/tooltip patterns in source
- **SC-005 [OBJ5]**: App.tsx ≤200 lines
- **SC-006 [OBJ6]**: `npm test`, `npm run test:e2e`, `npm run typecheck`, `npm run lint` all pass
- **SC-007 [OBJ6]**: axe-core automated scan passes with zero critical or serious violations
- **SC-008 [OBJ6]**: Lighthouse performance score ≥90; production bundle size ≤110% of pre-migration baseline

## Clarifications

### Session 2026-06-08

- Q1: "Should checkboxes/radios and FrequencyEditor toggles be migrated to shadcn patterns?" → A: Migrate to shadcn `<Input type="checkbox">`+`<Label>` and `<Switch>`; included in OBJ4 scope and TR-009
- Q2: "How are font families preserved after tailwind.config.ts deletion?" → A: CSS `@theme { --font-sans: ...; --font-mono: ...; }` in index.css; Google Fonts @import kept at top
- Q3: "Should shadcn CLI version be pinned?" → A: Yes — pin a specific version as devDependency for reproducible migration
- Q4: "How are z-index conflicts between sidebar and shadcn overlay components handled?" → A: Audit and reconcile during migration; define z-index scale in CSS theme
- Q5: "What maps the indigo stat tone after migration?" → A: Map to `bg-primary/10 text-primary` — semantically equivalent to current accent usage
- Q6: "Should custom shadow-quiet be preserved?" → A: Yes — define via CSS `@theme { --shadow-quiet: ...; }` in index.css
- Q7: "Should React Router v7 data-router API be adopted?" → A: No — keep existing `<Routes>/<Route>` component-tree pattern (v7 supports it)
- Q8: "Should accessibility and performance targets be added?" → A: Yes — axe-core zero critical/serious, Lighthouse ≥90, bundle ≤110% baseline

## Stress-Test Findings

### Session 2026-06-08

- **STF-001**: Font family migration unaddressed — RESOLVED: TR-003 added for CSS @theme font preservation; Edge Cases updated
- **STF-002**: SC-003 didn't verify `--color-*` CSS removal — RESOLVED: SC-003 extended to include zero `--color-` in CSS files
- **STF-003**: SC-004 only gated on button/select, not card/badge/table/switch/tooltip — RESOLVED: SC-004 extended to cover all replacement categories
- **STF-004**: Codemod (TR-006) and config deletion (TR-002) ordering unspecified — RESOLVED: TR-002 amended with explicit ordering constraint; Edge Cases updated
- **STF-005**: Edge Case incorrectly claimed React 19 "removes" forwardRef — RESOLVED: Edge Case corrected to "makes optional"

## Compliance Check

**Audited**: `project-instructions.md` v1.1.0 — **PASS**. Stack and layout align. No CRITICAL violations.
