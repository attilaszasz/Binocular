# Checklist: Testing — Collapsible Menu & Version Display

## localStorage Mock Patterns

- [X] CHK036 Is the localStorage key (`binocular-nav-collapsed`) specified unambiguously, enabling exact-string mock assertions? [Clarity, Spec §FR-006]
- [X] CHK037 Are all localStorage failure modes (quota exceeded, SecurityError in private browsing/file://, blocked cookies) enumerated in the spec for mock coverage? [Completeness, Spec §FR-006, STF-003]
- [X] CHK038 Is the read-failure fallback (default to expanded, no crash) specified with enough precision — including what happens when `localStorage.getItem` returns `null` (first visit) versus when it throws — for comprehensive mock coverage? [Testability, Spec §FR-006, §Edge Cases]
- [X] CHK039 Is the write-failure behavior (in-memory state retained, persistence lost silently) specified as a distinct test scenario from read-failure? [Completeness, Spec §FR-006, STF-003]
- [X] CHK040 Is the cross-tab last-write-wins acceptance documented such that no test expects `storage` event synchronization? [Clarity, Spec §FR-006, STF-005]
- [X] CHK041 Is the lazy `useState` initializer pattern (synchronous localStorage read, no flash-of-wrong-state) specified for deterministic mock sequencing? [Testability, Plan §AD-001]

## Vite Env Var Injection Testability

- [X] CHK043 Is the env var name `VITE_APP_VERSION` specified consistently across FR-005, Key Entities, and Dockerfile hints for uniform mock setup? [Consistency, Spec §FR-005, §Key Entities]
- [X] CHK044 Are all three version-string formats (SemVer tag, abbreviated SHA, `"dev"`) defined with testable string patterns for rendered-text assertions? [Testability, Spec §FR-004, §FR-005, STF-004]
- [X] CHK045 Is the `--dirty` flag behavior specified so tests can assert whether uncommitted-changes suffix appears in the version string? [Completeness, Spec §FR-005, §Edge Cases]
- [X] CHK046 Is the fallback chain for `import.meta.env.VITE_APP_VERSION` (git describe → abbreviated SHA → "dev") specified for tests across build/dev/env scenarios? [Completeness, Spec §FR-005, §Assumptions]
- [X] CHK047 Does the spec define how Vitest should mock `import.meta.env` (e.g., `vi.stubEnv`) to avoid test pollution between cases? [Testability, Spec §FR-005]
- [X] CHK048 Is the `git describe` command string (`--tags --first-parent --always --dirty`) specified to allow deterministic tokenisation of the expected output format? [Clarity, Spec §FR-005]

## Tooltip Timing Tests

- [X] CHK049 Is the 200-300ms hover delay vs immediate keyboard-focus distinction specified with sufficient precision for timer-based test design (fake timers, `vi.advanceTimersByTime`)? [Testability, Spec §FR-003, STF-002]
- [X] CHK050 Are all tooltip dismissal triggers (mouse leave, blur, Escape) enumerated as a complete set for test-case coverage? [Completeness, Spec §FR-003]
- [X] CHK051 Is the "no auto-dismiss timeout while hovering" behaviour specified to prevent unnecessary wait-based test assertions? [Completeness, Spec §FR-003, Q003]
- [X] CHK052 Is the relationship between ARIA attributes (`role="tooltip"` on container, `aria-describedby` on trigger, `aria-label` on NavLink) specified for DOM-query test assertions? [Clarity, Spec §FR-003]
- [ ] CHK053 Is tooltip behaviour during collapse/expand transitions specified — including whether tooltips dismiss on toggle, persist across re-renders, and what happens when the sidebar transitions while a tooltip is visible? [Completeness, Spec §FR-003, §Edge Cases] **[ASK — spec does not address tooltip lifecycle during collapse/expand transitions; requires design decision]**
- [X] CHK054 Are keyboard-focus tooltip requirements (immediate show, focus stays on trigger, Escape dismisses) specified independently of mouse-event implementation for testability? [Testability, Spec §FR-003, §Edge Cases, Q004]

## Theme Compatibility Tests

- [X] CHK056 Are the specific CSS custom property tokens (`--color-*` names) that must be used for toggle icon, version text, tooltip, and focus ring enumerated for computed-style assertions? [Clarity, Spec §FR-008]
- [X] CHK057 Are the minimum contrast ratios (AA 4.5:1 text, SC 1.4.11 3:1 non-text) specified with both numeric values and WCAG references for automated contrast-check assertions? [Verifiability, Spec §FR-008]
- [X] CHK058 Is the orthogonality constraint (theme toggle MUST NOT change collapse state) specified as a distinct testable invariant for integration tests? [Testability, Spec §Edge Cases]
- [X] CHK059 Do the acceptance scenarios for dark/light modes require both visual mode renderings to be tested, and is it specified whether test assertions should use computed CSS property values or class-name presence? [Completeness, Spec §SC-006, §FR-008]

## React Component Testing Approach

- [X] CHK061 Are the width-class values (`md:w-64` expanded, `md:w-16` collapsed) specified consistently across all requirements and success criteria for class-list assertions? [Consistency, Spec §FR-001, §SC-001]
- [X] CHK062 Is the main-content margin-left transition (`md:ml-64` ↔ `md:ml-16`) specified as a synchronous pair with sidebar width for coordinated test assertions? [Clarity, Spec §FR-001, Q009]
- [X] CHK063 Is the desktop-only breakpoint (viewport ≥768px, `md:` prefix) specified on every requirement to prevent false-negative tests on small viewports? [Consistency, Spec §FR-001, §SC-001, STF-001]
- [X] CHK064 Is the toggle icon convention (PanelLeftClose when expanded, PanelLeftOpen when collapsed) specified for DOM element queries by icon name? [Clarity, Spec §FR-001, Q001]
- [X] CHK065 Are the toggle button `aria-label` values ("Collapse sidebar" / "Expand sidebar") specified for screen-reader-focused test assertions? [Clarity, Spec §FR-001]
- [X] CHK066 Is the `aria-expanded` semantics (true when sidebar IS expanded) specified correctly to avoid inverted-state test assertions? [Unambiguousness, Spec §FR-001, HINT-004, Research §WCAG SC 4.1.2]
- [X] CHK067 Is the version-display abbreviation strategy specified with testable truncation rules (character-count or pixel-width limits, ellipsis for SHA, untruncated "dev") for rendered-text comparisons? [Testability, Spec §FR-004, STF-004]
- [X] CHK068 Is the sticky-positioning of the version display (outside scrollable `<nav>`) specified for DOM-structure assertions in component tests? [Testability, Spec §FR-004, Q005]
- [X] CHK069 Are the DOM ordering requirements (toggle button after nav items, no tabindex reorder) specified for tab-order test assertions? [Testability, Spec §Edge Cases, Research §WCAG SC 2.4.3]
- [X] CHK070 Is the `:focus-visible` focus-indicator requirement specified in a way that integration tests can verify (CSS selector or class rather than browser-event-dependent assertion)? [Testability, Spec §Edge Cases, Research §WCAG SC 2.4.7]

## Cross-Cutting Testability

- [X] CHK071 Are all six success criteria (SC-001 through SC-006) independently verifiable with objective pass/fail conditions and no subjective terms? [Verifiability, Spec §Success Criteria]
- [X] CHK072 Do all acceptance scenarios follow the Given/When/Then structure with concrete values for automated test translation? [Testability, Spec §User Scenarios]
- [X] CHK073 Is the ≥80% test-coverage target specified with a defined measurement boundary (all new component code, excluding which files)? [Completeness, Plan §Testing Strategy]
- [X] CHK074 Is the dependency on E003 nav structure (array of `{ label, path, icon }` objects) specified so test fixtures can accurately mock nav items? [Testability, Spec §Assumptions]
- [X] CHK075 Is rapid-click debounce specified as CSS-transition-only (no JavaScript debounce) to guide timer-free test assertions? [Clarity, Spec §Edge Cases]
- [X] CHK076 Does the spec define how regression tests (FR-007) should verify no console errors or route breakage across all existing routes? [Completeness, Spec §FR-007, §SC-005]
- [X] CHK077 Is the "no breakage to existing mobile sidebar" requirement scoped with a viewport boundary (<640px) for responsive test configuration? [Testability, Spec §Scope, FR-007]
- [X] CHK078 Is the `aria-describedby` dynamic ID generation pattern specified so tests can set up the ID reference correctly? [Clarity, Spec §FR-003]
- [X] CHK079 Does the spec distinguish between unit-test boundaries (component isolated, localStorage mocked, env var mocked) and integration-test boundaries (Router + ThemeProvider wrapper) for test-suite organisation? [Testability, Plan §Testing Strategy]
