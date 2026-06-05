# Research: Responsive UI & Dark Mode

**Feature**: E016 — Cross-view responsive and dark-mode polish
**Stack**: React 18, Tailwind CSS v3.4, Vite, TypeScript

## Responsive Layouts (Tailwind)

Binocular uses mobile-first breakpoints (`sm`/`md`/`lg`/`xl`). The `@tailwindcss/container-queries` plugin enables component-level responsive adaptation independent of viewport — useful for card grids and data tables that may sit inside containers of variable width. For existing tables (Activity Log), `overflow-x-auto` is basic; stacked-card transforms below `sm` improve mobile readability for dense data. Mobile minimum test width: 320px. Unprefixed utilities target mobile, with larger breakpoint overrides.

Sources: [Tailwind responsive design](https://tailwindcss.com/docs/responsive-design), [MDN container queries](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_containment/Container_queries)

## Dark Mode (Tailwind + React)

Current implementation uses `class` strategy with localStorage persistence and `prefers-color-scheme` fallback — the recommended approach. An inline `<script>` in `index.html` `<head>` reading localStorage before first paint eliminates sub-50ms FOUC. Existing CSS custom properties (`:root` / `:root.dark`) provide theme tokens (surface, panel, ink, muted, accent) but are unused in JSX — replace `bg-slate-*`/`dark:bg-slate-*` pairs with semantic tokens for single-source theming. Keep `class` strategy; `media` removes user choice.

Sources: [Tailwind dark mode docs](https://tailwindcss.com/docs/dark-mode), (existing `index.css` custom properties)

## Cross-View Theming Consistency

ThemeProvider wraps the entire route tree in `main.tsx` — correct placement. All routes inherit theme context automatically. Create a shared `test-utils.tsx` wrapping `render()` with ThemeProvider so component tests get theme context without per-test setup. CSS custom properties on `:root`/`:root.dark` apply globally regardless of route.

Sources: [Testing Library custom render](https://testing-library.com/docs/react-testing-library/setup#custom-render), (existing `main.tsx` provider placement)

## Testing Responsive + Dark Mode

Playwright for viewport emulation at 320px/768px/1280px and dark mode via `page.evaluate(() => document.documentElement.classList.add('dark'))` (class strategy, not `colorScheme` emulation). Vitest+RTL for render verification — each major view component wrapped in ThemeProvider, assert no errors in both light and dark states. jsdom has no viewport — responsive layout tests require Playwright.

Sources: [Playwright emulation](https://playwright.dev/docs/emulation), [Vitest browser mode](https://vitest.dev/guide/browser.html)

## Performance

Dark mode toggling via `classList.toggle` is CSS-only — no React re-render needed. Use `will-change: transform` on sidebar animations only, remove after transition ends to free GPU memory. `content-visibility: auto` on below-fold sections (activity log rows) defers rendering. `transition-colors` already in place; avoid `transition: all`. Target minimum touch size 44×44px for mobile accessibility.

Sources: [Tailwind dark mode](https://tailwindcss.com/docs/dark-mode), (existing `App.tsx` transition-colors pattern)
