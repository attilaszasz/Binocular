# Tasks: Core Frontend (UI/UX)

**Input**: Design documents from `specs/00003-devices-ui/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, quickstart.md, checklists/

**Tests**: Required — project instructions mandate Test-First Development (Principle V). Component tests use Vitest + React Testing Library with mocked API layer. One Playwright smoke test covers the critical happy path. Within each user story phase, tests are written first and expected to fail until implementation is complete.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Note**: User Stories 2 (Dark Mode), 3 (App Shell Navigation), and 8 (Placeholder Tabs) are implemented within the Foundational phase because their deliverables ARE the shared infrastructure every other story depends on. Their acceptance scenarios are covered by Foundational tasks and verified in the Polish phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Frontend**: `frontend/src/`, `frontend/tests/`
- **Backend**: `backend/src/` (minimal changes — SPA static file serving only)
- **Config**: `.vscode/`, `frontend/` root config files

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Scaffold the frontend project, install all dependencies, configure tooling.

- [ ] T001 Initialize frontend/ directory with Vite React-TypeScript template and install all dependencies: react-router-dom@7, @tanstack/react-query@5, react-hook-form, tailwindcss, postcss, autoprefixer, lucide-react (runtime); @biomejs/biome, vitest, @testing-library/react, @testing-library/jest-dom, @testing-library/user-event, jsdom, @playwright/test (dev)
- [ ] T002 [P] Configure TypeScript strict mode (strict: true, noUnusedLocals, noUnusedParameters) in frontend/tsconfig.json
- [ ] T003 [P] Configure Vite dev proxy (/api → localhost:8000), build output to frontend/dist/, and Vitest test environment (jsdom) in frontend/vite.config.ts (Research §13)
- [ ] T004 [P] Configure Tailwind CSS with darkMode: 'class' and content paths (['./index.html', './src/**/*.{ts,tsx}']) in frontend/tailwind.config.ts + frontend/postcss.config.js (AD-5, CHK013)
- [ ] T005 [P] Configure Biome lint and format rules in frontend/biome.json (Research §14)
- [ ] T006 [P] Create Vitest test setup (jsdom environment, RTL cleanup, jest-dom matchers) in frontend/tests/setup.ts
- [ ] T007 [P] Create Tailwind base styles (@tailwind base/components/utilities) in frontend/src/styles/index.css
- [ ] T008 [P] Create frontend/.gitignore (node_modules/, dist/, coverage/)
- [ ] T009 [P] Update .vscode/launch.json with "Binocular: Debug Frontend" config and "Binocular: Full Stack" compound per quickstart.md (AD-10)

**Checkpoint**: Frontend project scaffolded — `npm run dev` starts Vite, tooling configured, F5 launches full stack. No UI content yet.

---

## Phase 2: Foundational (Shell, Theme, API Client, Shared Components)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented. Delivers the application shell (US3), theme system (US2), API integration layer, placeholder tabs (US8), and all reusable UI primitives.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T010 Create TypeScript API interfaces (DeviceType, DeviceTypeCreateRequest, DeviceTypeUpdateRequest, DeviceTypeResponse, Device, DeviceCreateRequest, DeviceUpdateRequest, DeviceResponse, DeviceStatus literal union, ApiError, ErrorResponse) in frontend/src/api/types.ts (AD-3)
- [ ] T011 [P] Create queryKeys factory object (queryKeys.deviceTypes.all(), queryKeys.devices.all(), queryKeys.devices.byType(id)) in frontend/src/api/queryKeys.ts (AD-2, CHK003)
- [ ] T012 Create typed fetch wrapper apiFetch() with /api/v1 base path, JSON headers, error parsing into ApiError, and per-endpoint async functions (listDeviceTypes, listDevices, createDevice, updateDevice, deleteDevice, createDeviceType, updateDeviceType, deleteDeviceType, confirmDevice) in frontend/src/api/client.ts (AD-3, AD-9)
- [ ] T013 Create SPA entry point with FOIT-prevention blocking `<script>` in `<head>` that reads localStorage('binocular-theme') and applies 'dark' class to `<html>` before rendering in frontend/index.html (AD-5, FR-005, CHK011)
- [ ] T014 Create React root mount with StrictMode + QueryClientProvider (staleTime: 30_000) + RouterProvider in frontend/src/main.tsx (AD-1, AD-2, CHK001, CHK006)
- [ ] T015 [P] Create useTheme hook (localStorage persistence with 'binocular-theme' key, prefers-color-scheme detection, in-memory fallback when localStorage unavailable) in frontend/src/hooks/useTheme.ts (AD-5, FR-003, FR-004)
- [ ] T016 [P] Create useSidebar hook (mobile sidebar open/close toggle state) in frontend/src/hooks/useSidebar.ts
- [ ] T017 Create App.tsx with createBrowserRouter route definitions: AppShell layout route + DashboardPage at '/' (eager) + lazy-loaded ModulesPage at '/modules' + PlaceholderPage at '/logs' and '/settings' with descriptive content per FR-019 (AD-6, CHK028)
- [ ] T018 Create AppShell layout component (Sidebar + Header + `<Outlet/>` + responsive CSS grid) in frontend/src/components/AppShell.tsx (AD-1, AD-7)
- [ ] T019 [P] Create Sidebar component (desktop fixed 256px, mobile off-canvas h-dvh drawer with focus trap, 4 NavLink items with active styling, keyboard navigation, Escape-to-close) in frontend/src/components/Sidebar.tsx (AD-7, FR-006, FR-022, CHK016, CHK023)
- [ ] T020 [P] Create Header component (sticky bar, section title from route context, ThemeToggle slot, mobile hamburger trigger) in frontend/src/components/Header.tsx (FR-007)
- [ ] T021 [P] Create ThemeToggle component (Sun/Moon icons via named lucide-react imports, two-state switch, useTheme integration, aria-label, focus-visible ring) in frontend/src/components/ThemeToggle.tsx (AD-5, FR-002, CHK018, CHK021, CHK029)
- [ ] T022 [P] Create SlideOverPanel component (400px right-edge drawer, focus trap, Escape-to-close, full-screen on mobile <768px, backdrop overlay, focus-visible ring styles) in frontend/src/components/SlideOverPanel.tsx (AD-4, FR-022, CHK021, CHK023, CHK024)
- [ ] T023 [P] Create ConfirmDialog component (modal dialog, styled dark/light, Cancel + Confirm buttons, Escape-to-close, focus trap) in frontend/src/components/ConfirmDialog.tsx (AD-11)
- [ ] T024 [P] Create Skeleton loading primitives (pulse-animated bg-slate-200 dark:bg-slate-800, stats row shape, card shape, explicit dimensions matching loaded content) in frontend/src/components/Skeleton.tsx (AD-8, CHK027)
- [ ] T025 [P] Create ErrorBanner inline error display component with retry affordance in frontend/src/components/ErrorBanner.tsx (AD-9)
- [ ] T026 [P] Create shared form validation rules (names ≤200 chars, versions ≤100, URLs ≤2048, notes ≤2000, required, trimmed whitespace) in frontend/src/features/forms/validation.ts (FR-016, CHK040)
- [ ] T027 [P] Create PlaceholderPage generic component (lucide-react icon, title, description paragraph, styled dark/light) in frontend/src/features/placeholders/PlaceholderPage.tsx (FR-019)
- [ ] T028 [P] Create DashboardPage stub (heading + Skeleton layout placeholder) in frontend/src/features/dashboard/DashboardPage.tsx
- [ ] T029 [P] Create ModulesPage stub (heading + Skeleton layout placeholder) in frontend/src/features/modules/ModulesPage.tsx

**Checkpoint**: Foundation ready — app shell renders with sidebar, header, theme toggle, 4 navigable routes (stubs for Dashboard/Modules, functional placeholders for Logs/Settings). User story implementation can now begin.

---

## Phase 3: User Story 1 — View Device Inventory Dashboard (Priority: P1) 🎯 MVP

**Goal**: Render the primary device inventory dashboard with summary stats, device cards grouped by type, tri-state status indicators, version comparison, skeleton loading, and refresh (FR-008, FR-009, FR-021, FR-023, FR-024).

**Independent Test**: Load the dashboard with a pre-populated backend containing device types and devices in all three states and verify grouped rendering, correct stats, and skeleton-to-content transition.

### Tests for User Story 1

> **Write these tests FIRST — they MUST fail until implementation is complete.**

- [ ] T030 [P] [US1] Write component tests for DeviceCard (tri-state status rendering, version comparison display, name truncation with tooltip, action button slots, keyboard Enter on action buttons fires action per US3 AS7) in frontend/tests/components/DeviceCard.test.tsx
- [ ] T031 [P] [US1] Write component tests for StatsRow (correct totals from device data, aria-live region for screen reader announcements) in frontend/tests/components/StatsRow.test.tsx
- [ ] T032 [P] [US1] Write component tests for DashboardPage (grouped rendering by device type, skeleton loading state, refresh button triggers invalidateQueries, zero-device type group still shows heading) in frontend/tests/features/DashboardPage.test.tsx

### Implementation for User Story 1

- [ ] T033 [P] [US1] Create StatusIndicator component (CheckCircle2 for up_to_date, AlertCircle for update_available, Clock for never_checked — each with distinct icon + color + visible text label) in frontend/src/features/dashboard/StatusIndicator.tsx (FR-009, CHK020)
- [ ] T034 [P] [US1] Create VersionComparison component (Local vs Latest version display, responsive vertical stacking below sm breakpoint) in frontend/src/features/dashboard/VersionComparison.tsx (FR-009)
- [ ] T035 [US1] Create DeviceCard component with StatusIndicator, VersionComparison, last-checked timestamp, name with ellipsis truncation + hover tooltip, action button area in frontend/src/features/dashboard/DeviceCard.tsx (FR-009, CHK002)
- [ ] T036 [US1] Create DeviceTypeGroup component (heading with type name + device count badge + DeviceCard list using stable server IDs as keys) in frontend/src/features/dashboard/DeviceTypeGroup.tsx (FR-008, CHK002)
- [ ] T037 [US1] Create StatsRow component (3 stat cards — Total Devices, Updates Available, Up to Date — with aria-live="polite" region) in frontend/src/features/dashboard/StatsRow.tsx (FR-008, FR-021, CHK019)
- [ ] T038 [US1] Create useDevices() and useDeviceTypes() TanStack Query hooks using queryKeys factory with staleTime: 30_000 in frontend/src/features/dashboard/hooks.ts (AD-2, CHK003, CHK006)
- [ ] T039 [US1] Replace DashboardPage stub with full implementation: StatsRow + ActionBar (Add Device button + Refresh button) + DeviceTypeGroups + Skeleton loading state in frontend/src/features/dashboard/DashboardPage.tsx (FR-008, FR-023, FR-024)

**Checkpoint**: Dashboard renders grouped devices with stats, status indicators, version comparisons, and skeleton loading. Tests from T030–T032 should now pass. Confirm button not yet wired (US4).

---

## Phase 4: User Story 4 — Confirm a Firmware Update (Priority: P1) 🎯 MVP

**Goal**: One-click confirm action on device cards with optimistic update, rollback on error, and reactive stats update (FR-010, FR-011, FR-018, FR-021).

**Independent Test**: Set up a device with version mismatch, click confirm, verify card updates optimistically, stats decrement "Updates Available", and the change persists on refresh.

### Tests for User Story 4

> **Write these tests FIRST — they MUST fail until implementation is complete.**

- [ ] T040 [US4] Write tests for confirm action (optimistic update cycle, rollback on API error, button disabled during pending, button hidden for never_checked and up_to_date) appending to frontend/tests/components/DeviceCard.test.tsx (FR-010, FR-011, CHK005)

### Implementation for User Story 4

- [ ] T041 [US4] Create useConfirmDevice() mutation hook with full optimistic cycle (cancelQueries → snapshot previous → set optimistic value → rollback onError → invalidate onSettled) in frontend/src/features/dashboard/hooks.ts (AD-2, FR-010, CHK004, CHK005)
- [ ] T042 [US4] Wire ConfirmButton into DeviceCard (conditional rendering per FR-011, disabled during pending per FR-018, inline error banner on failure) in frontend/src/features/dashboard/DeviceCard.tsx (FR-010, FR-011, FR-018, CHK039)

**Checkpoint**: Confirm action works with optimistic UI. Tests from T040 should now pass. P1 MVP complete — dashboard is fully functional with view, stats, and confirm.

---

## Phase 5: User Story 5 — Add a New Device (Priority: P2)

**Goal**: Add Device form in a slide-over panel with client-side and server-error validation, query invalidation, and reactive stats update (FR-012, FR-016, FR-017, FR-021).

**Independent Test**: Click "Add Device", fill the form, submit successfully — device appears in correct group, stats increment. Submit with duplicate name — field error displayed inline.

### Tests for User Story 5

> **Write these tests FIRST — they MUST fail until implementation is complete.**

- [ ] T043 [P] [US5] Write form tests for DeviceForm (client-side max-length/required validation, server error mapping via setError, setError("root") for non-field errors, reset on close, clearErrors on resubmit) in frontend/tests/features/DeviceForm.test.tsx (CHK033, CHK036, CHK037)

### Implementation for User Story 5

- [ ] T044 [US5] Create DeviceForm component (name input, device type dropdown with last-used retention, current_version input, React Hook Form with validation from validation.ts, setError for field and root-level server errors) in frontend/src/features/forms/DeviceForm.tsx (AD-4, FR-012, FR-016, FR-017, CHK025, CHK036)
- [ ] T045 [US5] Create useCreateDevice() mutation hook with device-types + devices query invalidation in frontend/src/features/dashboard/hooks.ts (AD-2, FR-021, CHK004)
- [ ] T046 [US5] Wire "Add Device" button on DashboardPage to open SlideOverPanel with DeviceForm — close with reset() on success and cancel, isDirty confirmation dialog on cancel with unsaved changes in frontend/src/features/dashboard/DashboardPage.tsx (AD-4, CHK033, CHK034)

**Checkpoint**: Devices can be added through the UI form. Tests from T043 should now pass.

---

## Phase 6: User Story 6 — Manage Extension Modules / Device Types (Priority: P2)

**Goal**: Modules tab with full CRUD for device types/modules, cascade delete confirmation dialog, and slide-over forms (FR-014, FR-015, AD-11).

**Independent Test**: Navigate to Modules tab, create a module, verify it appears in the list and as a group on the dashboard. Edit its name. Delete one with child devices — cascade dialog shows count and requires confirmation.

### Tests for User Story 6

> **Write these tests FIRST — they MUST fail until implementation is complete.**

- [ ] T047 [P] [US6] Write component tests for ModulesPage (module list rendering, add/edit form in slide-over, cascade delete dialog shows device count, empty state) in frontend/tests/features/ModulesPage.test.tsx

### Implementation for User Story 6

- [ ] T048 [P] [US6] Create ModuleCard component (name, firmware source URL, check frequency, device count badge, edit + delete action buttons with aria-labels) in frontend/src/features/modules/ModuleCard.tsx (FR-014, CHK018)
- [ ] T049 [US6] Create DeviceTypeForm component (name, firmware_source_url, check_frequency with 360-min default, disabled extension_module_id field with "coming in future release" note, React Hook Form with validation) in frontend/src/features/forms/DeviceTypeForm.tsx (AD-4, FR-014)
- [ ] T050 [US6] Create useCreateDeviceType(), useUpdateDeviceType(), useDeleteDeviceType() mutation hooks — delete checks device_count and passes confirm_cascade=true when confirmed — in frontend/src/features/modules/hooks.ts (AD-2, AD-11, CHK004, CHK038)
- [ ] T051 [US6] Replace ModulesPage stub with full implementation: ModuleCard list + "Add Module" button + SlideOverPanel for add/edit forms + cascade ConfirmDialog + Skeleton loading + empty state in frontend/src/features/modules/ModulesPage.tsx (FR-014, FR-015, AD-11)

**Checkpoint**: Modules tab fully functional with CRUD and cascade delete. Tests from T047 should now pass. Dashboard groups update when modules are added/renamed.

---

## Phase 7: User Story 7 — Edit and Delete a Device (Priority: P2)

**Goal**: Edit device details via slide-over form pre-populated from API data, and delete with confirmation dialog (FR-013, FR-015, FR-021).

**Independent Test**: Edit a device's name and notes, verify the card updates. Delete a device, verify it disappears and stats decrement.

### Tests for User Story 7

> **Write these tests FIRST — they MUST fail until implementation is complete.**

- [ ] T052 [US7] Write tests for edit and delete flows (form pre-population via reset(apiData), update mutation with stats refresh, delete confirmation dialog) in frontend/tests/features/DeviceForm.test.tsx (CHK035)

### Implementation for User Story 7

- [ ] T053 [US7] Create useUpdateDevice() and useDeleteDevice() mutation hooks with device-types + devices query invalidation in frontend/src/features/dashboard/hooks.ts (AD-2, FR-021, CHK004)
- [ ] T054 [US7] Wire edit action on DeviceCard: open SlideOverPanel with DeviceForm pre-populated via reset(apiData) in useEffect keyed to fetched data, isDirty check on close in frontend/src/features/dashboard/DeviceCard.tsx (FR-013, CHK034, CHK035)
- [ ] T055 [US7] Wire delete action on DeviceCard: show ConfirmDialog with device name, call useDeleteDevice on confirm, card removed and stats updated in frontend/src/features/dashboard/DeviceCard.tsx (FR-015)

**Checkpoint**: Full device CRUD complete — add, edit, delete all working. Tests from T052 should now pass. All P2 stories delivered.

---

## Phase 8: User Story 9 — Handle Empty Inventory State (Priority: P3)

**Goal**: First-run empty state with guidance text and call-to-action when no devices or device types exist (FR-020).

**Independent Test**: Load the dashboard with an empty backend — verify guidance text, CTA button, and responsive layout. Add a device type — verify empty state disappears.

### Tests for User Story 9

> **Write these tests FIRST — they MUST fail until implementation is complete.**

- [ ] T056 [US9] Write tests for empty state (guidance text visible, CTA button present, responsive layout, hidden when data exists) in frontend/tests/features/DashboardPage.test.tsx

### Implementation for User Story 9

- [ ] T057 [US9] Create EmptyState component (icon/illustration, "No devices yet" heading, supportive text mentioning device types, "Create Your First Device Type" CTA button linking to Modules tab) in frontend/src/features/dashboard/EmptyState.tsx (FR-020)
- [ ] T058 [US9] Integrate EmptyState into DashboardPage — shown when useDeviceTypes() returns empty array, hidden when data exists in frontend/src/features/dashboard/DashboardPage.tsx (FR-020)

**Checkpoint**: First-run experience is welcoming and actionable. Tests from T056 should now pass. All user stories complete.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Cross-cutting component tests, E2E smoke test, production build integration, quality gates, and quickstart validation.

- [ ] T059 [P] Write ThemeToggle component tests (mode switching, localStorage persistence, OS preference fallback, no-localStorage graceful degradation) in frontend/tests/components/ThemeToggle.test.tsx
- [ ] T060 [P] Write SlideOverPanel component tests (open/close animation, focus trap, Escape key close, dirty form confirmation dialog) in frontend/tests/components/SlideOverPanel.test.tsx
- [ ] T061 [P] Write PlaceholderPage component tests (Activity Logs content matches FR-019, Settings content matches FR-019, correct rendering in dark and light modes) in frontend/tests/features/PlaceholderPage.test.tsx
- [ ] T062 Write Playwright smoke test (load dashboard → create device type via Modules → add device → confirm update → verify stats update) in frontend/tests/e2e/smoke.spec.ts
- [ ] T063 Update backend/src/main.py to mount frontend/dist/ via StaticFiles with SPA fallback returning index.html for all non-/api/* paths (Research §17)
- [ ] T064 Run biome check + biome format --check + tsc --noEmit on all frontend/ source and fix any lint or type errors (AD-12, CHK009)
- [ ] T065 Validate quickstart.md integration scenarios (§1–§7) against running full stack on localhost
- [ ] T066 [P] Write performance threshold assertions: Playwright timing test for SC-001 (< 3s initial load), SC-003 (< 2s confirm round-trip), SC-008 (< 300ms tab transition) in frontend/tests/e2e/smoke.spec.ts
- [ ] T067 [P] Write backend integration test asserting SPA fallback: GET /modules returns 200 with text/html content-type (validates T063 static file mount) in backend/tests/test_spa_fallback.py

**Checkpoint**: All quality gates pass, production build serves correctly, E2E smoke test green, performance thresholds validated.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational completion — dashboard is the primary rendering surface
- **US4 (Phase 4)**: Depends on US1 — adds confirm button to DeviceCard created in US1
- **US5 (Phase 5)**: Depends on US1 — wires "Add Device" button on DashboardPage created in US1
- **US6 (Phase 6)**: Depends on Foundational only — Modules tab is an independent route (can run in parallel with US1)
- **US7 (Phase 7)**: Depends on US1 — adds edit/delete actions to DeviceCard created in US1
- **US9 (Phase 8)**: Depends on US1 — adds empty state to DashboardPage created in US1
- **Polish (Phase 9)**: Depends on all user stories being complete

### Recommended Execution Order (Single Developer)

```
Phase 1 → Phase 2 → Phase 3 (US1) → Phase 4 (US4) → Phase 5 (US5) → Phase 6 (US6) → Phase 7 (US7) → Phase 8 (US9) → Phase 9
```

### Parallel Opportunities

**After Setup (Phase 1)**:
- T002–T009 can all run in parallel (different config files)

**After Foundational (Phase 2)**:
- **US1 (Phase 3) + US6 (Phase 6)** can start in parallel (different routes, different files)
- T019–T029 within Phase 2 can run in parallel (marked [P], different files)

**After US1 (Phase 3)**:
- **US4 + US5 + US7 + US9** can all start in parallel (different interaction layers on the same components, but care needed for shared files — hooks.ts and DeviceCard.tsx)
- In practice, US4 → US5 → US7 is safest sequentially since they all modify hooks.ts

**Within Each User Story**:
- Test tasks marked [P] can run in parallel with each other
- Implementation tasks follow: sub-components → container component → page integration

### User Story Dependencies

| Story | Priority | Depends On | Can Parallel With |
|---|---|---|---|
| US2 (Dark Mode) | P1 | — | Delivered in Foundational |
| US3 (App Shell) | P1 | — | Delivered in Foundational |
| US1 (Dashboard) | P1 | Foundational | US6 |
| US4 (Confirm) | P1 | US1 | — |
| US5 (Add Device) | P2 | US1 | US7, US9 (with care) |
| US6 (Modules) | P2 | Foundational | US1 |
| US7 (Edit/Delete) | P2 | US1 | US5, US9 (with care) |
| US8 (Placeholders) | P3 | — | Delivered in Foundational |
| US9 (Empty State) | P3 | US1 | US5, US7 (with care) |

---

## Coverage Map

### User Story → Task Mapping

| Story | Priority | Tasks | Count |
|---|---|---|---|
| — (Setup) | — | T001–T009 | 9 |
| — (Foundational) | — | T010–T029 | 20 |
| US1: View Dashboard | P1 | T030–T039 | 10 |
| US2: Dark/Light Mode | P1 | T013, T015, T021 (Foundational) + T059 (Polish) | 4 |
| US3: App Shell Navigation | P1 | T016–T020 (Foundational) | 5 |
| US4: Confirm Update | P1 | T040–T042 | 3 |
| US5: Add Device | P2 | T043–T046 | 4 |
| US6: Manage Modules | P2 | T047–T051 | 5 |
| US7: Edit/Delete Device | P2 | T052–T055 | 4 |
| US8: Placeholder Tabs | P3 | T017, T027 (Foundational) + T061 (Polish) | 3 |
| US9: Empty State | P3 | T056–T058 | 3 |
| — (Polish) | — | T059–T067 | 9 |
| **Total** | | | **67** |

### FR → Task Traceability

| Requirement | Tasks |
|---|---|
| FR-001 (Responsive shell) | T018, T019, T020 |
| FR-002 (Theme toggle) | T021 |
| FR-003 (OS preference) | T015 |
| FR-004 (Persist preference) | T015 |
| FR-005 (FOIT prevention) | T013 |
| FR-006 (Sidebar, client routing) | T017, T019 |
| FR-007 (Sticky header) | T020 |
| FR-008 (Dashboard: stats + groups) | T036, T037, T039 |
| FR-009 (Device card) | T033, T034, T035 |
| FR-010 (Confirm action) | T041, T042 |
| FR-011 (Hide confirm) | T042 |
| FR-012 (Add device form) | T044 |
| FR-013 (Edit device form) | T054 |
| FR-014 (Modules tab) | T048, T049, T051 |
| FR-015 (Delete + cascade) | T050, T051, T055 |
| FR-016 (Client validation) | T026, T044, T049 |
| FR-017 (Error messages) | T012, T025, T042, T044 |
| FR-018 (Disable during pending) | T042, T044, T049 |
| FR-019 (Placeholder tabs) | T027 |
| FR-020 (Empty state) | T057, T058 |
| FR-021 (Reactive stats) | T037, T038, T041, T045, T053 |
| FR-022 (Keyboard a11y) | T019, T022, T023 |
| FR-023 (Refresh button) | T039 |
| FR-024 (Skeleton loading) | T024, T039 |

### AD → Task Traceability

| Decision | Tasks |
|---|---|
| AD-1 (Feature-based components) | T014, T018 |
| AD-2 (TanStack Query) | T011, T014, T038, T041, T045, T050, T053 |
| AD-3 (Typed fetch wrapper) | T010, T012 |
| AD-4 (SlideOverPanel + RHF) | T022, T026, T044, T046, T049 |
| AD-5 (Dark mode + FOIT) | T004, T013, T015, T021 |
| AD-6 (React Router v7) | T017 |
| AD-7 (Responsive breakpoints) | T018, T019, T020 |
| AD-8 (Skeleton loading) | T024 |
| AD-9 (Error handling) | T012, T025 |
| AD-10 (F5 debugging) | T009 |
| AD-11 (Cascade delete) | T023, T050 |
| AD-12 (Performance budgets) | T064 |
