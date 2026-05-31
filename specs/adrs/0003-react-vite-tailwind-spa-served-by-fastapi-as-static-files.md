---
adr_id: ADR-0003
status: accepted
date: 2026-05-31
tags: [frontend, ui, build, deployment]
supersedes: []
superseded_by: ""
related_artifacts: [specs/prd.md#CAP-012]
---

# ADR-0003: React + Vite + Tailwind SPA served by FastAPI as static files

## Status

Accepted.

## Context

The product requires a responsive UI that works on mobile and desktop, first-class dark mode, and real-time-feeling interactions (check spinners, live result polling). To preserve the single-container, single-port operability model (ADR-0001), the frontend must be deployable without a separate web server or CORS configuration in production. A frontend stack, build tool, and serving strategy must be chosen.

## Decision Drivers

- Responsive mobile + desktop UX (PRD core requirement)
- First-class dark mode (near-mandatory for self-hosted audience)
- Smooth client-side state for spinners/polling/optimistic updates
- Single-port deployment (no separate frontend server, no production CORS)
- Typed API consumption matching backend OpenAPI

## Considered Options

### Option A: React 18 + TypeScript (strict) + Vite + Tailwind CSS, served by FastAPI `StaticFiles`

- **Pros**: Component model for responsive UI; Tailwind `darkMode: 'class'`; single-port single-container; fast Vite builds; typed client mirroring OpenAPI.
- **Cons**: Client-side rendering only (acceptable for a private tool); build adds a Node stage to the image.

### Option B: Server-side templates (Jinja2) rendered by FastAPI

- **Pros**: No separate build; single language.
- **Cons**: Clumsy for live spinners/polling/optimistic updates and responsive component reuse; dark-mode and rich interactions harder.

### Option C: Next.js (SSR) as a separate service

- **Pros**: SSR/SSG features.
- **Cons**: Needs a second runtime/process; breaks single-container single-port simplicity; SSR offers no benefit for a private single-user LAN tool.

## Decision Outcome

Chosen option: **A: React + TypeScript + Vite + Tailwind, served as static files by FastAPI** — it delivers the responsive, dark-mode, interactive UX the audience expects while preserving the single-container, single-port operability model. A multi-stage Docker build runs the Vite build and the Python image serves the resulting `dist/` via `StaticFiles` with an SPA fallback. No production CORS is needed; a Vite dev proxy handles local development.

## Consequences

### Positive

- Fluid responsive UI.
- Tailwind class-based dark mode with system-preference detection and persistence.
- Single-port deploy.
- Typed fetch client mirrors OpenAPI.
- TanStack Query for server state.

### Negative

- Multi-stage image includes a Node build stage.
- Client-side rendering only (no SSR/SEO — irrelevant for a private tool).

### Neutral

- Frontend code under `frontend/src/`; React Router SPA; built with `npm ci && npm run build` to `frontend/dist/`.

## Links

- [specs/prd.md](../prd.md) — CAP-012 (Responsive UI & Dark Mode)
- [ADR-0001](0001-self-hosted-single-container-monolith-with-core-extension-separation.md) — Single-container monolith architecture
- [ADR-0002](0002-python-311-and-fastapi-for-the-backend.md) — FastAPI backend
