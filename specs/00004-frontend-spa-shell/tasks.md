**Project Mode**: Mixed
**Epic**: E004 — Frontend SPA Shell
**Spec Type**: technical

## Phase 1: Setup (Repository / Workspace Delta)

- [X] T001 Initialize Vite project with React 19 + TypeScript in `frontend/` via `npm create vite@latest`
- [X] T002 Install Tailwind CSS v4 deps: `tailwindcss`, `@tailwindcss/vite` in `frontend/`
- [X] T003 Configure `frontend/vite.config.ts` with React plugin, Tailwind plugin, path aliases, `/api` proxy
- [X] T004 Configure `frontend/tsconfig.json` and `frontend/tsconfig.app.json` with strict mode and `@/` path alias
- [X] T005 [P] Create `frontend/eslint.config.js` with TypeScript + React rules
- [X] T006 [P] Create `frontend/src/index.css` with `@import "tailwindcss"`, `@theme` tokens, `@custom-variant dark`

## Phase 2: Foundational (shadcn/ui + Utilities)

- [X] T007 {TR-002} Run `npx shadcn@latest init` in `frontend/` with New York style, Zinc, blue primary after:T003
- [X] T008 {TR-002} Add shadcn/ui primitives: button, card, input, label, badge, select, switch, table, tooltip after:T007
- [X] T009 {TR-002} [COMPLETES TR-002] Verify `frontend/src/lib/utils.ts` has `cn()` utility (clsx + tailwind-merge) after:T007

## Phase 3: OBJ4 — Theme System 🎯 MVP

- [X] T010 [OBJ4] {TR-003} Create `frontend/src/components/theme-provider.tsx` with system/light/dark context after:T006
- [X] T011 [OBJ4] {TR-003} [COMPLETES TR-003] Create `frontend/src/hooks/use-theme.ts` hook for reading/setting theme after:T010

## Phase 4: OBJ3 — Application Layout & Navigation 🎯 MVP

- [X] T012 [OBJ3] {TR-004} Create `frontend/src/hooks/use-sidebar.ts` with collapsed state + localStorage persistence after:T006
- [X] T013 [OBJ3] {TR-008} Create `frontend/src/components/layout/version-display.tsx` with VITE_APP_VERSION fallback after:T006
- [X] T014 [OBJ3] Create `frontend/src/components/layout/brand.tsx` with app name and icon after:T006
- [X] T015 [OBJ3] {TR-004} Create `frontend/src/components/layout/nav-item.tsx` with active state styling after:T008
- [X] T016 [OBJ3] {TR-004} Create `frontend/src/components/layout/sidebar.tsx` with collapsible toggle after:T012
- [X] T017 [OBJ3] Create `frontend/src/components/layout/header.tsx` with sidebar toggle + theme switcher after:T011
- [X] T018 [OBJ3] {TR-004} [COMPLETES TR-004] Create `frontend/src/components/layout/app-layout.tsx` combining sidebar + header + outlet after:T016

## Phase 5: OBJ5 — React Router & Placeholder Pages 🎯 MVP

- [X] T019 [P] [OBJ5] {TR-005} Create placeholder pages: `frontend/src/pages/inventory.tsx`, `modules.tsx`, `logs.tsx`, `settings.tsx`, `not-found.tsx`
- [X] T020 [OBJ5] {TR-005} [COMPLETES TR-005] Create `frontend/src/App.tsx` with React Router, AppLayout wrapper, route definitions after:T018

## Phase 6: OBJ1 — Vite Build Validation 🎯 MVP

- [X] T021 [OBJ1] {TR-001,TR-009} [COMPLETES TR-001] Validate `npm run build` produces `dist/` and `npx tsc --noEmit` passes after:T020

## Phase 7: OBJ6 — Docker Build Integration & Static Serving 🎯 MVP

- [X] T022 [OBJ6] {TR-006} Create `backend/src/binocular/spa.py` with SPA serving helper (StaticFiles + catch-all) after:T021
- [X] T023 [OBJ6] {TR-006} [COMPLETES TR-006] Integrate SPA serving into `backend/src/binocular/app.py` after:T022
- [X] T024 [OBJ6] {TR-007} [COMPLETES TR-007] Update `Dockerfile` with `frontend-builder` Node stage, copy `dist/` to `/app/static_dist/` after:T021

## Phase 8: Polish & Cross-Cutting

- [X] T025 {TR-008} [COMPLETES TR-008] Verify version display shows VITE_APP_VERSION value or "dev" fallback after:T020
- [X] T026 {TR-009} [COMPLETES TR-009] Run `npx tsc --noEmit` and ESLint — fix any remaining errors after:T020
