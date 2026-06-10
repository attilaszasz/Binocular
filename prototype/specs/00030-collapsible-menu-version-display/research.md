# Research: Collapsible Menu & Version Display
> Feature E029 | 2026-06-08 | Topics: sidebar UX, env injection, git tags, tooltips, a11y, theming

## WCAG 2.1/2.2 for Collapsible Sidebar
- **SC 2.4.1 Bypass Blocks (A):** The sidebar `<aside>` must be a landmark (`complementary` or `<nav>`) so screen reader users can skip repeated navigation. Technique SCR28 (expandable/collapsible menu to bypass blocks) applies.
- **SC 2.4.3 Focus Order (A):** DOM order must match visual order; toggle button (bottom) must appear after nav items in DOM. No `tabindex` reordering.
- **SC 2.4.7 Focus Visible (AA):** All focusable elements (toggle, nav links) need a visible focus indicator. Use `:focus-visible` (C45). Icon-only items need ≥3:1 contrast focus ring in both modes.
- **SC 4.1.2 Name/Role/Value (A):** Toggle must be `<button>` with `aria-label` ("Collapse sidebar"/"Expand sidebar") and `aria-expanded`. Each collapsed nav link must have `aria-label` (ARIA14).
- **Sources:** W3C/WAI Understanding WCAG 2.2 SC 2.4.1, SC 4.1.2.

## ARIA APG Patterns (Disclosure + Tooltip)
- **Disclosure pattern:** Sidebar toggle = disclosure button. Uses `aria-expanded="true"` when sidebar is expanded (labels visible). Enter + Space toggle state. `aria-controls` may reference the sidebar content container.
- **Tooltip pattern:** Collapsed nav items use `role="tooltip"` on tooltip container, `aria-describedby` on trigger. Show on hover (200-300ms delay) or immediate keyboard focus. Escape dismisses. Focus stays on trigger. Tooltip does NOT receive focus.
- **Sources:** W3C/ARIA APG "Disclosure (Show/Hide) Pattern"; "Tooltip Pattern".

## localStorage Persistence UX
- **Graceful degradation:** Read-failure try-catch defaults to expanded state silently (FR-006). Write-failure try-catch keeps in-memory state but loses persistence. No user-visible error needed — impact is preference non-persistence only.
- **SecurityError handling:** Catch `SecurityError` (blocked cookies, `file://` origin, incognito mode). Use `'storage' in window` check then try-catch actual read.
- **Sources:** MDN Web Docs `Window: localStorage`; spec FR-006/STF-003.

## Dark/Light Mode Compatibility
- **CSS custom property theming:** All sidebar elements use existing `--color-*` tokens (FR-008). Toggle icon, version text, tooltip, focus ring must use token system, not raw hex.
- **Contrast minima:** AA 4.5:1 for version string, tooltip text against background in BOTH modes. SC 1.4.11 Non-Text Contrast (3:1) for toggle icon. Theme toggle must NOT change collapse state (orthogonal state).
- **Sources:** W3C/WAI Understanding SC 1.4.3, SC 1.4.6; spec FR-008.

## Toggle Button Design Patterns
- **Icon convention:** `PanelLeftClose` when expanded, `PanelLeftOpen` when collapsed (communicates action). `aria-expanded` reflects visibility of controlled content — true when sidebar IS expanded.
- **Keyboard:** Native `<button>` gives Enter + Space for free. Toggle must be Tab-reachable in both states. Use functional updater `setIsCollapsed(prev => !prev)` for rapid-click safety.
- **Sources:** W3C/ARIA APG Disclosure Pattern; spec HINT-003/HINT-004.

## React Collapsible Sidebar with Tailwind (Implementation)
- **Pattern**: `useState` lazy initializer reading localStorage. Width classes `w-16` (collapsed) / `w-64` (expanded) with `transition-[width] duration-300 ease-in-out`. Hide labels via conditional class.
- **Pitfalls**: Avoid `transition-all` — use `transition-[width]`. Persist state in `useState` initializer, not `useEffect` (prevents flash of wrong state).
- **Sources**: Tailwind CSS transition docs; spec plan.md HINT-003.

## Vite Env Injection at Docker Build Time
- **Pattern**: `ARG VITE_APP_VERSION` then `ENV VITE_APP_VERSION=$VITE_APP_VERSION` before Vite build. Pass `--build-arg VITE_APP_VERSION="$(git describe --tags --always --dirty)"`. Vite statically replaces `import.meta.env.VITE_APP_VERSION` at compile time.
- **Pitfalls**: `ARG` before `ENV` in Dockerfile. Ensure .git/ is in build context.
- **Sources**: Vite Env Variables guide; Docker ARG/ENV best practices.

## Git Describe for SemVer Extraction
- **Pattern**: `git describe --tags --always --match "v*" --dirty`. `--always` falls back to SHA. For shallow CI clones: `git fetch --unshallow --tags` before build.
- **Sources**: Git `git-describe` docs; spec FR-005.

## Tooltip UX for Icon-Only Navigation (UI)
- **Pattern**: Tailwind `group` + absolutely positioned tooltip (`invisible group-hover:visible`, `focus-visible` for keyboard). 200-300ms delay on hover, immediate on focus. Instant dismissal on mouseleave.
- **Content**: Brief — repeat nav item label exactly. No actionable content inside tooltip.
- **Sources**: NN/G Tooltip Guidelines; Tailwind CSS `group-hover` docs.

## Performance Clarifications (Checklist-Evaluation 2026-06-08)

- **CHK082**: `transition-[width]` triggers the full Layout → Paint → Composite pipeline (not just Composite like `transform`). This is an accepted performance characteristic because the sidebar width change inherently requires layout recalculation; using `transform: translateX()` for visual-only collapse would break actual layout and interactive area. The browser's style coalescing within a single animation frame mitigates the per-frame cost. This tradeoff is explicitly accepted for this feature.

- **CHK083**: The two simultaneous layout-triggering transitions (sidebar width + content margin-left) rely on the browser's style-recalc coalescing within the same animation frame. Because both transitions are triggered by the same state change (`isCollapsed` toggle) and applied in the same frame, the browser batches the style recalculation into a single layout pass per frame, not two sequential passes. No additional mitigation is required.

- **CHK085**: The `motion-safe:` Tailwind variant MUST be applied to all transition classes (`motion-safe:transition-[width]`, `motion-safe:duration-300`, `motion-safe:ease-in-out`) to respect the user's `prefers-reduced-motion` OS setting. This follows the existing pattern noted in Plan §Brownfield Notes and ensures WCAG SC 2.3.3 (Animation from Interactions) compliance.

- **CHK087**: `will-change: width` is NOT recommended for the sidebar `<aside>` because it creates a new compositing layer in GPU memory, which can cause performance degradation on memory-constrained devices and is unnecessary for simple width transitions. `contain: layout style` is also NOT recommended because the sidebar content (nav items, tooltips) must be fully rendered and interactive during the animation — containment would clip or suppress repaints of tooltips that extend beyond the sidebar boundaries. The browser's built-in style-recalc coalescing is sufficient for this transition.

- **CHK088**: "Rapid repeated toggle clicks" is defined as inter-click interval shorter than the transition duration (300ms), i.e., ≥2 clicks within 300ms. The browser's CSS transition interruption mechanism handles this natively — each new click interrupts the in-flight transition and reverses direction from the current animated width, not from the start or end value. No JavaScript debounce is required.

- **CHK091**: The minimum acceptable frame rate for the toggle animation is ≥55fps (≤18ms per frame). This is measured on Chrome 120+/Firefox 120+ at 1920×1080 on a mid-range desktop (Intel i5-12400, 16GB RAM). The `duration-300` transition at 55fps produces ∼16 intermediate frames (300ms × 55fps), which is visually smooth. Frame drops below 55fps during the 300ms window are acceptable only if caused by external main-thread load (not by the transition itself).

- **CHK092**: Tooltip show/hide logic (200-300ms delay, DOM state changes) is NOT suspended during an active collapse/expand transition. However, because tooltips use CSS visibility/opacity (Tailwind `group-hover`/`focus-visible` with `transition-opacity`) rather than imperative DOM insertion/removal, no timer callbacks or re-renders are triggered — the tooltip state is purely CSS-driven and does not cause mid-animation frame drops. React re-renders from tooltip state are avoided because no JS state tracks tooltip visibility.

- **CHK093**: Nav-item label visibility toggling (FR-002) uses Tailwind conditional class switching (e.g., `invisible`/`visible`). Because the class toggle and the width transition are both triggered by the same `isCollapsed` state change, React batches both DOM updates into the same commit, and the browser coalesces them into a single layout/paint frame. No extra forced layout pass occurs.

- **CHK094**: Each rapid toggle triggers one synchronous `localStorage.setItem` call (~1-5ms blocking). On each click within the 300ms transition window, the write is executed immediately. This is acceptable because: (1) the ~1-5ms blocking cost fits within the 10ms RAIL frame budget; (2) the localStorage write does not block the CSS transition (which runs on the compositor thread once initial layout is computed); (3) the try-catch guard prevents write failures from interrupting the animation. The in-memory `isCollapsed` state is always updated before the localStorage write, so the UI is never blocked waiting for the write to complete.

- **CHK097**: `localStorage.getItem` and `localStorage.setItem` are synchronous and block the main thread per the HTML Standard §Storage API. The measured blocking cost is ∼1-5ms per operation on modern browsers. This is explicitly accepted because: (1) reads occur exactly once (lazy `useState` initializer) at component mount; (2) writes occur at most once per user interaction (≤1 toggle per ∼300ms); (3) the cost fits within the 10ms RAIL frame budget. No mitigation is required.

- **CHK098**: The try-catch wrapper for localStorage access SHOULD be scoped narrowly around only the `getItem`/`setItem` call itself, not the entire toggle handler or component function. This avoids V8 JIT deoptimization of the hot path. The recommended pattern:
  ```typescript
  // Read
  let stored: string | null = null;
  try { stored = localStorage.getItem('binocular-nav-collapsed'); } catch {}
  // Write
  try { localStorage.setItem('binocular-nav-collapsed', String(isCollapsed)); } catch {}
  ```

- **CHK099**: The localStorage value MUST be stored as a raw string — `"true"` when collapsed, `"false"` when expanded — not as a JSON-stringified boolean. This avoids unnecessary `JSON.parse`/`JSON.stringify` overhead on every read/write. The raw string comparison (`stored === 'true'`) is faster and simpler.

- **CHK100**: No cooldown interval for localStorage writes is required because: (1) each toggle writes exactly one key-value pair (~20 bytes), well within the ∼5MB quota; (2) writes are user-initiated (not automation), occurring at human interaction speed (≥300ms apart); (3) the try-catch guard handles `QuotaExceededError` gracefully. If automation scripts or test frameworks toggle the sidebar programmatically, they should batch writes or accept the last-write-wins behavior.

- **CHK101**: The collapse state change (`isCollapsed`) is a single `useState` in the `CollapsibleSidebar` component. React's default re-render behavior re-renders only the component subtree whose state changed — i.e., `CollapsibleSidebar` and its children (NavItem, ToggleButton, VersionDisplay). The parent layout (`App` component shell) is NOT re-rendered because the state is local to the sidebar subtree. No `React.memo` or `useCallback` is required at the App level.

- **CHK103**: `React.memo` is NOT required for the nav-item list because: (1) the only prop that changes on toggle is `isCollapsed`, which is a primitive boolean — React's default memoization for the parent component's render output already skips child reconciliation when props haven't changed in practice; (2) the nav-item list is small (≤5 items from E003), so the re-render cost is negligible (∼0.1ms per item). If profiling reveals excessive re-render cost, `React.memo` can be added later as a targeted optimization.

- **CHK104**: The 200-300ms `setTimeout` for tooltip appearance (mouse hover) MUST be cancelled on toggle to prevent stale-state callbacks and memory pressure. Use a `useRef` to store the timer ID and `clearTimeout` in a cleanup function triggered by state change. This is especially important because the tooltip timer could fire during an in-flight transition, attempting to read DOM state that is mid-animation. The `setTimeout` on hover is managed per-nav-item and should be cleared on mouse leave, blur, and toggle.

- **CHK105**: The `VersionDisplay` component SHOULD be wrapped in `React.memo` because its content (`VITE_APP_VERSION`) is a compile-time constant with no reactive dependencies — it never changes after mount. Without `React.memo`, the component re-renders on every collapse/expand toggle despite rendering the same output. As an alternative, the version string can be rendered as static markup (outside the reactive React tree) or as a constant string literal in the JSX.

- **CHK107**: The maximum expected nav-item count is **5** (matching E003: `/inventory`, `/logs`, `/modules`, `/settings`, plus any future addition not exceeding 7). The tooltip system must support at most 7 nav items without degradation. Each item has one tooltip DOM node (always present, visibility-toggled via CSS) and no JS timer while not hovered. At 7 items, the total tooltip overhead is ∼7 DOM nodes + 0 active timers at rest, which is negligible.

- **CHK108**: The "transitioning" state listed in the Key Entities state machine (`{expanded, collapsed, transitioning}`) is a **CSS-class concern only** — it describes the phase during which CSS transitions are active. It MUST NOT be implemented as a JavaScript state variable. The transition is handled entirely by Tailwind's `transition-[width] duration-300 ease-in-out` classes on the `<aside>` element. No additional JS state or re-render is needed for the transitioning phase.

- **CHK109**: The toggle interaction targets an Interaction to Next Paint (INP) of ≤200ms measured on the 75th percentile of lab tests (Chrome 120+, mid-range desktop). The main-thread blocking budget is ≤50ms per toggle (covering: state update + React commit + localStorage write). The 300ms CSS transition runs on the compositor thread and is not counted toward the INP budget. This aligns with the Web Performance Working Group's INP recommendations (≤200ms for good responsiveness).

- **CHK110**: Nav-item label visibility toggling MUST use CSS class-based visibility control (e.g., Tailwind `invisible`/`visible` or `opacity-0`/`opacity-100`) rather than `display: none`/`display: block`. Using `display: none` triggers forced layout recalculation (Layout → Paint → Composite) on every toggle, while `visibility: hidden` only triggers repaint (Paint → Composite). Alternatively, `opacity` toggling triggers only Composite when used with `will-change: opacity`. The recommended approach is Tailwind `invisible`/`visible` classes, which use `visibility: hidden`/`visible` and avoid the forced layout cost of `display` changes.

- **CHK111**: The maximum acceptable DOM-node count increase between expanded and collapsed states is **7** (one tooltip container per nav item, up to 7 items). In the expanded state, tooltips are present but hidden via CSS (visibility/opacity). In the collapsed state, the same tooltip nodes remain but become visible on hover/focus. No DOM nodes are created or destroyed on toggle — only CSS classes change. The 7-node increase is negligible for modern browsers (<0.1ms DOM cost).

- **CHK112**: The performance validation criterion for the toggle animation is: **≥55fps on Chrome 120+/Firefox 120+ at 1920×1080 on a mid-range desktop (Intel i5-12400, 16GB RAM)**. Measured via the `requestAnimationFrame` callback delta or Chrome DevTools Performance panel. The test sequence: 10 rapid toggles with 200ms interval, capturing frame timestamps. No single frame may exceed 18ms (55fps threshold) during the 300ms transition window.

- **CHK113**: `contain: layout style` is NOT recommended for the sidebar `<aside>`. While `contain: layout style` would limit the reflow/repaint scope to the sidebar subtree, it would also clip any overflow content (including tooltips that extend beyond the sidebar boundary) and prevent the tooltip from rendering outside the sidebar. The browser's standard style-recalc coalescing is sufficient for this single-subtree transition.

- **CHK114**: The version-display tooltip is a **separate instance** of the tooltip component, not shared with nav-item tooltips. This is because: (1) the version tooltip has different content (full version string vs nav-item label); (2) it is positioned at the sidebar bottom, not inline with nav items; (3) it uses the same show/dismiss timing as nav-item tooltips (per FR-004) but is triggered on a different element. The overhead of one additional tooltip instance (one extra DOM node + one timer) is negligible.
