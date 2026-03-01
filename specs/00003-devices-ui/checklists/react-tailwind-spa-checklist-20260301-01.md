# Checklist: React + Tailwind SPA Best Practices

**Feature**: `00003-devices-ui` | **Domain**: React + Tailwind SPA  
**Date**: 2026-03-01  
**Depth**: Standard (30–40 items) | **Audience**: Reviewer (PR review)

**Focus Areas**: Component Architecture & State Management, Responsive Layout & Dark Mode, Accessibility, Performance & Bundle Size, Form UX & Error Handling

---

## Component Architecture & State Management

- [X] CHK001 Is `<StrictMode>` wrapping the root mount in `main.tsx` to catch impure components, missing cleanup, and stale closures in development? [Correctness, Plan §AD-1]
- [X] CHK002 Do all `.map()` calls rendering device/type/module lists use stable server-generated IDs (`device.id`, `device_type.id`) as `key` — never array indices? [Correctness, Spec §US1]
- [X] CHK003 Are TanStack Query keys structured as hierarchical arrays from a centralized `queryKeys` factory object (e.g., `queryKeys.devices.list()`) to prevent typos and enable targeted invalidation? [Maintainability, Plan §AD-2]
- [X] CHK004 Does every `useMutation` define an `onSuccess` or `onSettled` callback that invalidates the affected query keys after create/edit/delete/confirm operations? [Completeness, Spec §FR-021]
- [X] CHK005 Does the "Sync Local" optimistic mutation implement the full cycle: `cancelQueries` → snapshot previous cache → set optimistic value → rollback in `onError` → invalidate in `onSettled`? [Correctness, Spec §FR-010, Plan §AD-2]
- [X] CHK006 Is `gcTime` ≥ `staleTime` on all query configurations to prevent garbage-collecting cache entries that are still logically fresh? [Correctness, Plan §AD-2]
- [X] CHK007 Are all component compositions achieved via children props or render slots — with zero class-based components and no inheritance hierarchies? [Consistency, Plan §AD-1]
- [X] CHK008 Is prop drilling limited to ≤ 2 intermediate levels, with shared state extracted into context or lifted queries at the nearest common ancestor? [Maintainability, Plan §AD-1]
- [X] CHK009 Does every `useEffect` have a complete dependency array, enforced by Biome's `useExhaustiveDependencies` rule? [Correctness, Plan §AD-14 Quality Gates]

## Responsive Layout & Dark Mode

- [X] CHK010 Does the responsive layout implement all three breakpoint tiers (< 768px mobile, 768–1023px tablet, ≥ 1024px desktop) with the correct sidebar, stats row, and card grid behavior per Plan §AD-7? [Completeness, Spec §FR-001]
- [X] CHK011 Does the FOIT-prevention blocking `<script>` in `index.html` `<head>` read `localStorage('binocular-theme')` and apply the `dark` class to `<html>` before any rendering occurs? [Correctness, Spec §FR-005, Plan §AD-5]
- [X] CHK012 Does the theme toggle persist the user's choice to `localStorage` and fallback to in-memory state (OS preference) when `localStorage` is unavailable (private browsing)? [Robustness, Spec §FR-004]
- [X] CHK013 Does the `content` array in Tailwind config cover all template files (`.html`, `.tsx`, `.ts`) to prevent JIT from silently dropping used classes from the production build? [Correctness, Plan §AD-5]
- [X] CHK014 Are all Tailwind class names written as complete static literals (no dynamic string interpolation like `bg-${color}-500`) to ensure JIT can detect them? [Correctness, Plan §AD-5]
- [X] CHK015 Is `@apply` usage restricted to ≤ 1 base/reset stylesheet, with all component styling done via utility classes directly in JSX? [Performance, Plan §AD-5]
- [X] CHK016 Does the mobile sidebar implementation use `100dvh` (Tailwind's `h-dvh`) instead of `100vh` to handle iOS Safari's dynamic address bar? [Correctness, Research §REC-2.3]
- [X] CHK017 Are all dark mode styles consistently applied — no missing `dark:` variants on form inputs, dropdown menus, slide-over panels, or confirmation dialogs? [Completeness, Spec §SC-005, Research §REC-3.5]

## Accessibility (a11y)

- [X] CHK018 Do all icon-only buttons (check/refresh, edit, delete) have descriptive `aria-label` attributes? [Compliance, Spec §FR-022, Research §REC-6.7]
- [X] CHK019 Does the stats row region use `aria-live="polite"` so screen readers announce count changes after confirm/add/delete operations? [Compliance, Research §REC-6.1]
- [X] CHK020 Do device status indicators use redundant encoding — distinct icons per state (CheckCircle2, AlertCircle, Clock) plus visible text labels ("Up to Date", "Update Available", "Never Checked") — not color alone? [Compliance, Spec §FR-009, Research §REC-6.2, REC-6.3]
- [X] CHK021 Do focus ring styles use `focus-visible:` prefix (not bare `focus:`) to show rings only for keyboard navigation, reducing visual noise for mouse users? [Best Practice, Plan §AD-5]
- [X] CHK022 Are all interactive targets ≥ 24×24 CSS pixels with ≥ 24px spacing from adjacent targets, meeting WCAG 2.2 §2.5.8 Target Size Minimum? [Compliance, Research §REC-2.2]
- [X] CHK023 Is focus trapped within the slide-over panel and mobile sidebar when open, with focus returned to the trigger element on close? [Compliance, Spec §FR-022, Research §REC-6.6]
- [X] CHK024 Does the slide-over panel (and mobile sidebar) close on Escape key press? [Compliance, Spec §FR-022, Research §6]
- [X] CHK025 Does the device type dropdown retain the last-used selection when adding multiple devices in sequence (WCAG 2.2 §3.3.7 Redundant Entry)? [Compliance, Plan §AD-4]

## Performance & Bundle Size

- [X] CHK026 Is the main JS bundle < 150 KB gzipped, with total initial load (JS + CSS) < 250 KB gzipped? [Performance, Plan §AD-12]
- [X] CHK027 Do skeleton placeholder containers (stats row, device cards) have explicit dimensions matching loaded content, preventing CLS > 0.1 on data arrival? [Performance, Spec §FR-024, Plan §AD-8]
- [X] CHK028 Are non-landing routes (Activity Logs, Modules, Settings) lazy-loaded via `React.lazy` + `<Suspense>` to keep the initial bundle focused on the dashboard? [Performance, Plan §AD-6]
- [X] CHK029 Are all lucide-react imports using named/per-icon imports (`import { CheckCircle2 }`) — not namespace imports (`import * as Icons`) — to enable tree shaking? [Performance, Plan §AD-12]
- [X] CHK030 Is the production CSS bundle ≤ 15 KB gzipped, with no wildcard safelist patterns inflating it? [Performance, Plan §AD-12]
- [X] CHK031 Are no external fonts loaded via `@import` or `<link>` — system font stack only — eliminating a common SPA performance bottleneck? [Performance, Plan §AD-12]
- [X] CHK032 Are hashed static assets served with `Cache-Control: max-age=31536000, immutable` while `index.html` is served with `no-cache`? [Performance, Research §17, Plan §AD-10]

## Form UX & Error Handling

- [X] CHK033 Is `reset()` called on the slide-over panel close path (both cancel and successful submit) to prevent stale values on re-open? [Correctness, Plan §AD-4]
- [X] CHK034 Is `formState.isDirty` checked before allowing panel close, with a confirmation dialog shown when the user has unsaved changes? [Completeness, Spec §Edge Cases]
- [X] CHK035 Are edit forms populated via `reset(apiData)` inside a `useEffect` keyed to the fetched data — not via stale `defaultValues` from mount time? [Correctness, Spec §FR-013]
- [X] CHK036 Do non-field API errors (500s, network failures, unrecognized error codes) display as a root-level form error banner via `setError("root", ...)`, not silently swallowed? [Completeness, Spec §FR-017, Plan §AD-9]
- [X] CHK037 Are server-side field errors cleared (`clearErrors()`) at the start of each new form submission to prevent stale error messages persisting? [Correctness, Plan §AD-4]
- [X] CHK038 Does the cascade deletion dialog show the exact child device count (from `device_count` in DeviceTypeResponse) and require explicit confirmation before calling `DELETE ?confirm_cascade=true`? [Completeness, Spec §FR-015, Plan §AD-11]
- [X] CHK039 Are all form submit buttons and action buttons (Confirm, Delete, Refresh) disabled during pending API requests, with visible loading indicators, preventing duplicate submissions? [Completeness, Spec §FR-018]
- [X] CHK040 Do client-side validation rules (max-length, required, URL format) exactly mirror the backend constraints: names ≤ 200 chars, firmware versions ≤ 100 chars, URLs ≤ 2048 chars, notes ≤ 2000 chars? [Consistency, Spec §FR-016]
