---
adr_id: ADR-0003
status: accepted
date: 2026-06-08
tags: [frontend, ui, build, deployment, shadcn-ui, tailwind-v4, component-library]
supersedes: []
superseded_by: ""
related_artifacts: ["specs/prd.md#CAP-012", "specs/sad.md"]
---

# ADR-0003: React + Vite + Tailwind SPA with shadcn/ui Component Library, served by FastAPI as static files

## Status

Accepted.

## Context

The product requires a responsive UI that works on mobile and desktop, first-class dark mode, and real-time-feeling interactions (check spinners, live result polling). To preserve the single-container, single-port operability model (ADR-0001), the frontend must be deployable without a separate web server or CORS configuration in production. A frontend stack, build tool, and serving strategy must be chosen.

A component library strategy is now needed to replace ad-hoc hand-rolled Tailwind markup with standardized, accessible primitives. Tailwind CSS has released v4 with a CSS-first configuration model (no `tailwind.config.ts`, configuration via `@import "tailwindcss"` and CSS-based `@variant`/`@utility` directives), replacing the legacy PostCSS/autoprefixer pipeline with the `@tailwindcss/vite` plugin.

## Decision Drivers

- Responsive mobile + desktop UX (PRD core requirement)
- First-class dark mode (near-mandatory for self-hosted audience)
- Smooth client-side state for spinners/polling/optimistic updates
- Single-port deployment (no separate frontend server, no production CORS)
- Typed API consumption matching backend OpenAPI
- Accessible, composable UI primitives replacing repeated ad-hoc Tailwind class patterns

## Considered Options

### Option A: React 19 + TypeScript (strict) + Vite 6 + Tailwind CSS 4.x (CSS-first config via `@tailwindcss/vite`) + shadcn/ui (New York style, Zinc base + blue primary) with Radix UI primitives, class-variance-authority, clsx, tailwind-merge, and tw-animate-css; served by FastAPI `StaticFiles`

- **Pros**: shadcn/ui provides accessible, composable primitives (Button, Card, Select, Badge, Table, Switch, Tooltip) that replace ad-hoc Tailwind class patterns; Tailwind v4 CSS-first config via `@tailwindcss/vite` eliminates PostCSS/autoprefixer and `tailwind.config.ts`; dark mode via `@custom-variant dark (&:is(.dark *))` which integrates with the existing ThemeProvider `.dark` class toggling; React 19 adds native ref handling (no forwardRef wrappers needed); component library ensures consistent styling and accessibility across all views.
- **Cons**: Tailwind v4 requires migration of renamed utilities (shadow-sm→shadow-xs, rounded-sm→rounded-xs, outline-none→outline-hidden); shadcn adds ~15 Radix dependency packages; build adds shadcn-generated component source to repo.

### Option B: Server-side templates (Jinja2) rendered by FastAPI

- **Pros**: No separate build; single language.
- **Cons**: Clumsy for live spinners/polling/optimistic updates and responsive component reuse; dark-mode and rich interactions harder.

### Option C: Next.js (SSR) as a separate service

- **Pros**: SSR/SSG features.
- **Cons**: Needs a second runtime/process; breaks single-container single-port simplicity; SSR offers no benefit for a private single-user LAN tool.

## Decision Outcome

Chosen option: **A: React 19 + TypeScript + Vite 6 + Tailwind CSS 4 + shadcn/ui, served as static files by FastAPI** — it delivers the responsive, dark-mode, interactive UX the audience expects while preserving the single-container, single-port operability model. shadcn/ui provides a standardized component library with accessible Radix primitives, replacing ad-hoc hand-rolled Tailwind markup. Tailwind v4's CSS-first configuration model eliminates legacy tooling (PostCSS, autoprefixer, `tailwind.config.ts`) in favor of `@tailwindcss/vite`. A multi-stage Docker build runs the Vite build and the Python image serves the resulting `dist/` via `StaticFiles` with an SPA fallback. No production CORS is needed; a Vite dev proxy handles local development.

## Consequences

### Positive

- Fluid responsive UI with standardized shadcn/ui primitives (Button, Card, Select, Badge, Table, Switch, Tooltip)
- Tailwind v4 CSS-first dark mode (`@custom-variant dark`) integrates with existing ThemeProvider `.dark` class toggling
- Single-port deploy with no production CORS
- Typed fetch client mirrors OpenAPI
- TanStack Query for server state
- shadcn/ui's `cn()` utility (clsx + tailwind-merge) eliminates class conflict bugs
- Component library decomposition (ui/, inventory/, logs/, modules/, settings/, layout/) improves maintainability
- React 19 native ref handling removes forwardRef boilerplate

### Negative

- Multi-stage image includes a Node build stage
- Client-side rendering only (no SSR/SEO — irrelevant for a private tool)
- Tailwind v4 migration requires codemod for renamed utilities
- shadcn adds ~15 Radix dependency packages to the lockfile

### Neutral

- Frontend code under `frontend/src/`; React Router SPA; built with `npm ci && npm run build` to `frontend/dist/`.

## Links

- [specs/prd.md](../prd.md) — CAP-012 (Responsive UI & Dark Mode)
- [ADR-0001](0001-self-hosted-single-container-monolith-with-core-extension-separation.md) — Single-container monolith architecture
- [ADR-0002](0002-python-311-and-fastapi-for-the-backend.md) — FastAPI backend
- [ADR-0009](0009-module-derived-device-type-remove-standalone-device-type-field.md) — Module-derived device type
