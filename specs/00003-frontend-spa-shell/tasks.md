# Tasks: Frontend SPA Shell

## Dependencies

| Phase | Depends On | Notes |
|-------|------------|-------|
| Setup | E001, E002 | Existing backend, Dockerfile, and CI workflow |
| Foundational | Setup | Toolchain and shared primitives |
| OBJ1 | Foundational | Frontend quality gates |
| OBJ2 | Foundational | Shell layout, routes, theme, client |
| OBJ3 | OBJ1, OBJ2 | Static serving and container integration |
| Polish | OBJ3 | Final validation artifacts |

## Phase 1: Setup

- [X] T001 {TR-001,TR-008} Create frontend package/tooling configs in frontend/package.json and related config files
- [X] T002 {TR-001} Create frontend source bootstrap files in frontend/src/main.tsx, frontend/src/index.css, and frontend/src/vite-env.d.ts after:T001

## Phase 2: Foundational

- [X] T003 {TR-003} Implement theme provider and hook in frontend/src/theme/ThemeProvider.tsx and frontend/src/theme/useTheme.ts after:T002 → exports: ThemeProvider,useTheme
- [X] T004 {TR-004} Implement typed API client in frontend/src/api/client.ts after:T002 → exports: ApiClient,ApiError

## Phase 3: OBJ1 — 🎯 MVP SPA Quality Gates

- [X] T005 [OBJ1] {TR-008} Add frontend tests for theme and API client in frontend/src/theme/ThemeProvider.test.tsx and frontend/src/api/client.test.ts after:T003
- [X] T006 [OBJ1] {TR-001,TR-008} [COMPLETES TR-001] Generate npm lockfile and verify frontend scripts after:T005 [COMPLETES TR-008]

## Phase 4: OBJ2 — 🎯 MVP Application Shell

- [X] T007 [OBJ2] {TR-002,TR-003,TR-004} Implement routed shell in frontend/src/App.tsx after:T004 ← T003:ThemeProvider ← T004:ApiClient
- [X] T008 [OBJ2] {TR-002,TR-003} Add shell route/theme tests in frontend/src/App.test.tsx after:T007 [COMPLETES TR-002] [COMPLETES TR-003]
- [X] T009 [OBJ2] {TR-004} Add API client export wiring in frontend/src/api/index.ts after:T004 [COMPLETES TR-004]

## Phase 5: OBJ3 — 🎯 MVP Static Serving and Container

- [X] T010 [OBJ3] {TR-005,TR-006} Implement FastAPI SPA static helper in backend/src/binocular/static.py after:T008 → exports: mount_spa()
- [X] T011 [OBJ3] {TR-005,TR-006} Wire SPA static serving in backend/src/binocular/app.py and tests in backend/tests/test_static.py after:T010 ← T010:mount_spa [COMPLETES TR-005] [COMPLETES TR-006]
- [X] T012 [OBJ3] {TR-007} Update backend package data and Docker frontend build integration in backend/pyproject.toml and Dockerfile after:T011 [COMPLETES TR-007]

## Phase 6: Polish and QC Readiness

- [X] T013 Run frontend and backend validation commands and document evidence in specs/00003-frontend-spa-shell/analysis-report.md
