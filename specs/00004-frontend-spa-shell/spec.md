---
feature_branch: "00004-frontend-spa-shell"
created: "2026-06-10"
input: "E004 React/Vite/Tailwind v4 SPA shell with shadcn/ui from day one, collapsible sidebar nav, dark mode, version display, and component directory structure"
spec_type: "technical"
spec_maturity: "clarified"
epic_id: "E004"
epic_sources: "{SAD:ADR-0003}"
---

# Feature Specification: Frontend SPA Shell

**Feature Branch**: `00004-frontend-spa-shell`
**Created**: 2026-06-10
**Status**: Draft
**Spec Type**: technical
**Spec Maturity**: clarified
**Epic ID**: E004
**Epic Sources**: {SAD:ADR-0003}
**Product Document**: specs/prd.md

## Problem Statement

Binocular has a running backend (E001) and data layer (E002) but no user interface. Every product epic — device inventory (E006), module management (E009), check workflows (E012), activity logging (E015) — requires a frontend application framework to render views. Without a standardized SPA shell with consistent component primitives, layout, navigation, and theming, each downstream feature would need to bootstrap its own UI infrastructure, leading to inconsistent UX and duplicated effort. The shell must establish the canonical React/Vite/Tailwind v4/shadcn/ui stack from day one so all subsequent frontend work builds on a shared, accessible foundation.

## Scope

### Included

- Vite 6 project initialized with React 19, TypeScript strict mode, and `@tailwindcss/vite`
- Tailwind CSS v4 CSS-first configuration via `@theme` directives — no `tailwind.config.ts`
- shadcn/ui initialization with New York style, Zinc base, blue primary accent
- shadcn/ui primitives: Button, Card, Select, Badge, Table, Switch, Tooltip, Input, Label
- `cn()` utility via clsx + tailwind-merge in `lib/utils.ts`
- ThemeProvider with system/light/dark modes toggling `.dark` class on `<html>`
- Layout components: collapsible Sidebar, Header, NavItem, Brand, VersionDisplay
- React Router with placeholder pages for Inventory, Modules, Logs, Settings
- `VITE_APP_VERSION` injected from environment at build time
- Multi-stage Dockerfile Node stage compiling frontend and copying `dist/` into backend image
- Backend `StaticFiles` mount serving `dist/` with SPA catch-all route
- Responsive layout on mobile and desktop
- Vite dev proxy for `/api` → backend during development

### Excluded

- Feature-specific page content (inventory lists, module forms, log tables) — deferred to E006, E009, E012, E015
- Playwright end-to-end tests — deferred until sufficient UI exists
- TanStack Query setup — deferred to first data-fetching epic (E006)
- React Hook Form setup — deferred to first form-heavy epic (E006/E009)
- Production CORS configuration — unnecessary with single-port serving

### Edge Cases & Boundaries

- Browser has JavaScript disabled — app shows a `<noscript>` message; no server-side rendering
- `VITE_APP_VERSION` unset — VersionDisplay shows "dev" fallback
- Backend unreachable during dev — Vite proxy returns 502; no special handling needed
- Sidebar state on narrow viewports — collapses to icon-only; toggleable via button
- Dark mode preference changes at OS level — ThemeProvider in "system" mode reacts via `prefers-color-scheme` media query listener
- Unknown routes — React Router catch-all renders a 404 placeholder page

## Technical Objectives

### Objective 1 - Vite/React/Tailwind Project Scaffold (Priority: P1)

Initialize the frontend build toolchain with all dependencies, TypeScript strict mode, and Tailwind v4 CSS-first configuration via `@tailwindcss/vite`.

**Why this priority**: Foundation for all frontend code — nothing renders without this.

**Rationale**: Tailwind v4 eliminates the PostCSS/autoprefixer pipeline and `tailwind.config.ts` in favor of CSS-native `@import "tailwindcss"` and `@theme` directives. The `@tailwindcss/vite` plugin handles processing.

**Deliverables**:
- `frontend/package.json` with React 19, TypeScript, Vite 6, `@tailwindcss/vite`, `tailwindcss` dependencies
- `frontend/tsconfig.json` with strict mode, path aliases (`@/` → `src/`)
- `frontend/vite.config.ts` with React plugin, Tailwind plugin, path alias, `/api` proxy
- `frontend/src/index.css` with `@import "tailwindcss"`, `@theme` tokens (Zinc palette, blue primary), `@custom-variant dark`
- `frontend/src/main.tsx` entry point rendering `<App />` into `#root`
- `frontend/index.html` with `<div id="root">`, `<noscript>` fallback, meta viewport

**Validation Criteria**:
1. **Given** the frontend directory, **When** `npm run build` executes, **Then** `dist/` is produced with `index.html` and hashed JS/CSS assets
2. **Given** TypeScript strict mode, **When** `npx tsc --noEmit` runs, **Then** zero errors reported

### Objective 2 - shadcn/ui Component Library (Priority: P1)

Install and configure shadcn/ui with the canonical primitives required by all downstream feature epics.

**Why this priority**: Component primitives are consumed by every subsequent UI epic — without them, downstream features cannot be built.

**Rationale**: shadcn/ui provides accessible Radix-based primitives as source code, ensuring full ownership and Tailwind v4 compatibility. New York style with Zinc base provides the self-hosted tool aesthetic.

**Deliverables**:
- `frontend/components.json` — shadcn/ui configuration
- `frontend/src/components/ui/button.tsx`, `card.tsx`, `select.tsx`, `badge.tsx`, `table.tsx`, `switch.tsx`, `tooltip.tsx`, `input.tsx`, `label.tsx`
- `frontend/src/lib/utils.ts` — `cn()` utility (clsx + tailwind-merge)

**Validation Criteria**:
1. **Given** a test page importing Button, Card, and Badge, **When** rendered, **Then** components display with correct Zinc/blue styling and are keyboard-accessible
2. **Given** the components directory, **When** `npx tsc --noEmit` runs, **Then** all shadcn components type-check clean

### Objective 3 - Application Layout & Navigation (Priority: P1)

Build the persistent layout shell with collapsible sidebar, header, branding, and version display.

**Why this priority**: Every page shares the layout — navigation and branding are the user's entry point.

**Rationale**: A collapsible sidebar with icon-only mode supports both desktop and mobile viewports. The layout must be in place before any feature page can be rendered.

**Deliverables**:
- `frontend/src/components/layout/sidebar.tsx` — collapsible sidebar with toggle button, icon+label nav items
- `frontend/src/components/layout/header.tsx` — top bar with sidebar toggle, theme switcher, branding
- `frontend/src/components/layout/nav-item.tsx` — navigation link component with active state
- `frontend/src/components/layout/brand.tsx` — logo/name display
- `frontend/src/components/layout/version-display.tsx` — shows `VITE_APP_VERSION` or "dev" fallback
- `frontend/src/components/layout/app-layout.tsx` — combines sidebar + header + content outlet

**Validation Criteria**:
1. **Given** the app renders, **When** the sidebar toggle is clicked, **Then** the sidebar collapses to icon-only mode and re-expands, and the state is persisted to `localStorage`
2. **Given** a narrow viewport (≤768px), **When** the app loads, **Then** the sidebar defaults to collapsed
3. **Given** the sidebar was collapsed by the user, **When** the page is reloaded, **Then** the sidebar remains collapsed
3. **Given** `VITE_APP_VERSION` is set to "1.2.3", **When** the layout renders, **Then** "1.2.3" appears in the version display

### Objective 4 - Theme System (Priority: P1)

Implement dark/light/system mode switching with CSS class toggling and persistent preference.

**Why this priority**: Dark mode is a core expectation for self-hosted tool audiences (PRD CAP-012).

**Rationale**: ThemeProvider manages the `.dark` class on `<html>` and persists preference to `localStorage`. Tailwind v4's `@custom-variant dark` scopes dark styles via `:is(.dark *)`.

**Deliverables**:
- `frontend/src/components/theme-provider.tsx` — context provider with system/light/dark modes
- `frontend/src/hooks/use-theme.ts` — hook for reading and setting theme
- Theme toggle UI integrated into Header

**Validation Criteria**:
1. **Given** the app in light mode, **When** the theme toggle is clicked to dark, **Then** `<html>` gains `.dark` class, all UI updates to dark palette, and preference is stored in `localStorage`
2. **Given** theme set to "system" and OS preference is dark, **When** the app loads, **Then** dark mode is applied automatically

### Objective 5 - React Router & Placeholder Pages (Priority: P1)

Set up client-side routing with placeholder pages for each major feature area.

**Why this priority**: Downstream epics need route targets and navigation links to build upon.

**Rationale**: React Router v7 provides the SPA routing. Placeholder pages ensure the navigation works end-to-end before feature content is added.

**Deliverables**:
- `frontend/src/App.tsx` — React Router with layout wrapper and route definitions
- `frontend/src/pages/inventory.tsx` — placeholder
- `frontend/src/pages/modules.tsx` — placeholder
- `frontend/src/pages/logs.tsx` — placeholder
- `frontend/src/pages/settings.tsx` — placeholder
- `frontend/src/pages/not-found.tsx` — 404 catch-all page

**Validation Criteria**:
1. **Given** the app is running, **When** navigating to `/inventory`, **Then** the Inventory placeholder page renders within the layout
2. **Given** an unknown path `/foo`, **When** navigated to, **Then** the Not Found page renders

### Objective 6 - Docker Build Integration & Static Serving (Priority: P1)

Add the multi-stage Node build to the Dockerfile and configure FastAPI to serve the built SPA.

**Why this priority**: Without this, the frontend cannot ship inside the container — blocks all deployment.

**Rationale**: A `frontend-builder` Docker stage runs `npm ci && npm run build`. The final image copies `dist/` to `/app/static_dist/`. FastAPI mounts `StaticFiles` at `/` with an SPA catch-all returning `index.html` for non-API paths.

**Deliverables**:
- `Dockerfile` updated with `frontend-builder` stage (Node 22 slim)
- Backend static file serving via `StaticFiles` mount and SPA catch-all route
- `VITE_APP_VERSION` passed as Docker build arg

**Validation Criteria**:
1. **Given** the Dockerfile, **When** `docker build .` runs, **Then** the image builds successfully with frontend assets at `/app/static_dist/`
2. **Given** the running container, **When** `GET /` is requested, **Then** `index.html` is returned
3. **Given** the running container, **When** `GET /api/v1/healthz` is requested, **Then** the health endpoint responds (not intercepted by static serving)

### Technical Constraints

- React 19 with TypeScript strict mode
- Tailwind CSS 4.x CSS-first config only — no `tailwind.config.ts`, no PostCSS, no autoprefixer
- shadcn/ui New York style, Zinc palette, blue primary accent
- `@tailwindcss/vite` plugin — no other CSS processing pipeline
- Frontend source under `frontend/src/` per project Source Code Layout policy
- `tsc` strict and ESLint must pass per CI quality gates (E003)
- No external CDN or cloud dependencies for any assets

## Integration Points

- **IP-001**: E001 (Application Skeleton) provides FastAPI app factory and lifespan — this epic adds `StaticFiles` mount and SPA catch-all route
- **IP-002**: E001 `Dockerfile` and `entrypoint.sh` — this epic adds a `frontend-builder` stage and copies `dist/` into the final image
- **IP-003**: E003 (CI Pipeline) frontend quality gates — this epic provides `frontend/package.json` triggering conditional lint/type-check/test jobs
- **IP-004**: E006, E009, E012, E015 consume shadcn/ui primitives, layout components, ThemeProvider, `cn()`, and router routes

## Technical Requirements

- **TR-001**: System MUST initialize a Vite 6 project with React 19, TypeScript strict mode, and `@tailwindcss/vite` producing a buildable `dist/` output
- **TR-002**: System MUST include shadcn/ui primitives (Button, Card, Select, Badge, Table, Switch, Tooltip, Input, Label) under `components/ui/` with `cn()` utility
- **TR-003**: System MUST provide a ThemeProvider supporting system, light, and dark modes, toggling `.dark` class on `<html>` with `localStorage` persistence
- **TR-004**: System MUST render a collapsible sidebar with icon-only collapsed state, responsive to viewport width
- **TR-005**: System MUST configure React Router with placeholder pages for Inventory, Modules, Logs, Settings, and a 404 catch-all
- **TR-006**: System MUST serve the built SPA via FastAPI `StaticFiles` with an SPA catch-all route that does not intercept `/api` paths
- **TR-007**: System MUST add a `frontend-builder` Docker stage using Node 22 slim that compiles the frontend and copies `dist/` into the final image
- **TR-008**: System MUST display `VITE_APP_VERSION` in the UI, falling back to "dev" when unset
- **TR-009**: System MUST pass `tsc --noEmit` in strict mode and lint checks without errors

## Clarifications

### Session 2026-06-10

- Q: Should sidebar collapsed/expanded state persist across sessions? -> A: Yes, persist in `localStorage` (consistent with theme persistence pattern)
- Q: ESLint or Biome for frontend linting (project-instructions lists "Biome/ESLint")? -> A: ESLint (CI already configured from E003)

## Assumptions & Risks

### Assumptions

- Node 22 LTS is available as a Docker base image for the build stage
- shadcn/ui CLI (`npx shadcn@latest`) supports Tailwind CSS v4 and generates v4-compatible component source
- React Router v7 is stable and compatible with React 19
- The backend's `/api` prefix convention is established and will not change

### Risks

- **Tailwind v4 / shadcn/ui compatibility** *(likelihood: low, impact: high)*: shadcn/ui components may need minor CSS adjustments for v4's renamed utilities. Mitigation: test each component after generation and apply codemod if needed.
- **Docker build time increase** *(likelihood: medium, impact: low)*: Adding a Node stage increases build time. Mitigation: use Docker layer caching and `npm ci` for deterministic installs.

## Implementation Signals

- `NEW-UI` — Complete frontend SPA shell with layout, navigation, theming, and placeholder pages
- `NEW-CONFIG` — Vite configuration, Tailwind CSS-first config, shadcn/ui `components.json`, TypeScript config
- `MIGRATION` — Dockerfile updated from single-stage Python to multi-stage with Node builder

## Success Criteria

### Measurable Outcomes

- **SC-001** [OBJ1]: `npm run build` produces a valid `dist/` with `index.html` and hashed assets; `tsc --noEmit` reports zero errors
- **SC-002** [OBJ2]: All nine shadcn/ui primitives render correctly and are keyboard-accessible
- **SC-003** [OBJ3]: Sidebar collapses and expands via toggle; defaults to collapsed at ≤768px viewport
- **SC-004** [OBJ4]: Theme switching between system/light/dark works, persists across page reloads, and updates all UI elements
- **SC-005** [OBJ5]: All four placeholder pages and the 404 page are reachable via navigation and direct URL
- **SC-006** [OBJ6]: `docker build .` succeeds; container serves `index.html` at `/` and health endpoint at `/api/v1/healthz` remains accessible

## Glossary

| Term | Definition |
|------|------------|
| CSS-first configuration | Tailwind CSS v4 approach where theme tokens and variants are defined in CSS via `@theme` and `@custom-variant` directives instead of a JavaScript config file |
| shadcn/ui | A component library that generates accessible React component source code into the project using Radix UI primitives, rather than installing a pre-built package |
| SPA catch-all | A server route that returns `index.html` for any path not matching an API route, enabling client-side routing |

## Compliance Check

### Instructions Check Report
**Target**: spec.md
**Status**: PASS

| Principle | Verdict | Notes |
|-----------|---------|-------|
| I. Honest Failure | N/A | UI shell — no scraping or detection |
| II. Polite by Default | N/A | No outbound requests |
| III. Data Ownership & Self-Containment | PASS | No external services, CDNs, or cloud dependencies |
| IV. Least-Privilege & Explicit Trust Boundary | N/A | Frontend-only, no privilege changes |
| V. Type Safety & Correctness-First | PASS | TypeScript strict mode, `tsc` pass required (TR-009) |
| VI. Set-and-Forget Reliability | PASS | Static assets served from container, no external dependencies |
| VII. Agent Output Style | N/A | Artifact convention, not runtime output |
