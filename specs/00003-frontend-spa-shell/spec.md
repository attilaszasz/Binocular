---
spec_type: technical
epic_id: E003
epic_sources:
  - SAD:ADR-0003
spec_maturity: draft
---

# Feature Specification: Frontend SPA Shell

## Problem Statement

Binocular currently has a runnable FastAPI backend but no browser application for operators to manage inventory, modules, logs, or settings. Later product epics depend on a reusable React shell, typed API access, and static-file serving through the single container. Without this foundation, UI feature work would fragment across ad hoc setup and routing decisions.

## Scope

### Included

- Create a React 18 + TypeScript + Vite + Tailwind frontend under `frontend/`.
- Provide a shared application layout with navigation, responsive behavior, and dark/light theme primitives.
- Provide client-side routing with deep-link compatibility.
- Provide a typed API client wrapper for `/api/v1` calls.
- Integrate FastAPI static serving so the built SPA is served at `/` while API routes remain available under `/api/v1` and `/healthz`.
- Update the Docker image build to compile the SPA and copy `dist/` into the Python runtime image.
- Activate frontend CI gates once `frontend/package.json` exists.

### Excluded

- Real device, module, log, or settings persistence; later product epics own those data-backed workflows.
- Authentication and optional basic-auth controls; E013 owns operability/security controls.
- Full responsive/dark-mode polish across final feature surfaces; E016 owns cross-view polish.

### Edge Cases & Boundaries

- Deep links such as `/modules` must return the SPA entry point, not a 404.
- API and health endpoints must not be shadowed by the SPA catch-all.
- If the frontend build output is absent during local backend development, FastAPI must still start and serve API routes.
- The shell must remain usable on narrow mobile widths.

## Technical Objectives

### OBJ1 [P1] SPA project scaffold and quality gates

**Why this priority**: The Vite/React/TypeScript/Tailwind project is the foundation every later UI epic consumes.

**Rationale**: Establish one frontend toolchain, source root, and test/lint/type-check path rather than letting later epics bootstrap their own.

**Deliverables**: `frontend/package.json`, TypeScript config, Vite config, Tailwind/PostCSS config, source root, test setup, lint script.

**Validation Criteria**: Given a clean checkout, when frontend dependencies are installed, then `npm run lint`, `npm run typecheck`, `npm test -- --run`, and `npm run build` succeed.

### OBJ2 [P1] Reusable application shell

**Why this priority**: Later inventory, module, manual-check, and log screens need shared routing, navigation, theme state, and API access.

**Rationale**: A stable shell reduces duplicated UI wiring and makes product epics focus on domain behavior.

**Deliverables**: routed React app, layout/navigation components, theme provider, typed API client, baseline pages.

**Validation Criteria**: Given the frontend app is running, when an operator navigates among shell routes and toggles theme, then visible route content and theme state update without page reloads.

### OBJ3 [P1] FastAPI static serving and container build integration

**Why this priority**: The product must remain a single deployable container and serve the SPA from the backend process.

**Rationale**: ADR-0003 requires the Vite build to be copied into the Python image and served by FastAPI with SPA fallback.

**Deliverables**: FastAPI static mount/catch-all, package data inclusion, Docker Node build stage, CI-compatible Docker build.

**Validation Criteria**: Given a production build artifact exists, when FastAPI starts, then `/`, `/inventory`, and `/modules` return the SPA while `/healthz` and `/api/v1/healthz` still return API responses.

## Integration Points

| Integration | Contract | Owner |
|-------------|----------|-------|
| FastAPI app factory | Mount static assets after API routers and provide SPA fallback for non-API paths | Backend |
| `/api/v1` API namespace | Frontend API client targets backend JSON endpoints under `/api/v1` | Backend + Frontend |
| Docker build | Node stage produces `frontend/dist`; Python wheel includes copied static files | Runtime image |
| GitHub Actions CI | Existing frontend job activates because `frontend/package.json` exists | CI |

## Requirements

TR-001: System MUST include a React 18 + TypeScript + Vite + Tailwind frontend under `frontend/src/` with strict TypeScript checking.
TR-002: System MUST provide client-side routes for inventory, activity logs, modules, and settings within a shared responsive layout.
TR-003: System MUST provide first-class dark/light theme primitives that persist user preference locally.
TR-004: System MUST provide a typed API client wrapper for `/api/v1` requests.
TR-005: System MUST serve the built SPA from FastAPI at `/` and preserve SPA deep links.
TR-006: System MUST ensure API and health endpoints are not shadowed by static serving or SPA fallback.
TR-007: System MUST update the Docker build so the frontend build is included in the single non-root runtime image.
TR-008: System MUST provide frontend lint, strict type-check, unit test, and production build scripts compatible with CI.

## Assumptions & Risks

### Assumptions

- Node 22 is available locally and in CI.
- Frontend state in this epic can use mock/static shell data only; persistent domain data arrives in later epics.
- Browser support targets modern evergreen browsers on trusted LAN clients.
- FastAPI can start without frontend build output during backend-only development.

### Risks

- Docker build complexity increases by adding a Node stage (likelihood: medium, impact: medium).
- Static route ordering could accidentally shadow API endpoints (likelihood: low, impact: high).
- Frontend dependency changes may add new audit findings in CI (likelihood: medium, impact: medium).

## Implementation Signals

- **NEW-UI**: Add the frontend SPA source tree and reusable shell components.
- **NEW-API**: Add a typed client wrapper for `/api/v1` calls; no new backend domain endpoints.
- **NEW-CONFIG**: Add Vite, Tailwind, TypeScript, Vitest, and lint configuration.
- **BREAKING-CHANGE**: Modify Docker build inputs and backend package data to include static assets.

## Success Criteria

SC-001 [OBJ1]: Frontend lint, strict type-check, unit tests, and production build all pass from the `frontend/` directory.
SC-002 [OBJ2]: Operators can switch among inventory, logs, modules, and settings shell routes without a full page reload.
SC-003 [OBJ2]: Theme selection changes the rendered UI and persists across reloads.
SC-004 [OBJ3]: FastAPI returns the SPA for `/` and deep-link routes while `/healthz` and `/api/v1/healthz` continue returning JSON.
SC-005 [OBJ3]: The Docker image builds successfully with frontend assets included and still runs as the non-root `binocular` user.

## Glossary

| Term | Definition |
|------|------------|
| SPA | Single-page application delivered as static assets with client-side routing. |
| Deep link | A direct browser request to a client-side route such as `/modules`. |
| Theme primitive | Shared state and CSS mechanism used by feature screens to render light or dark mode. |

## Compliance Check

| Check | Result | Notes |
|-------|--------|-------|
| Project instructions alignment | PASS | Single-container delivery, strict typing, frontend source root, and no external services preserved. |
