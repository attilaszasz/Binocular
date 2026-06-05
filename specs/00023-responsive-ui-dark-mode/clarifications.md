# Clarifications & Stress-Test Findings

> Created 2026-06-04 during `/sddp-clarify`. All resolutions are integrated into [spec.md](spec.md).

## Clarifications

### Session 2026-06-04

- Q: Settings view in scope? → A: Explicitly in scope — all routable views receive polish (inventory, activity log, modules, settings). FR-001 "every route" takes precedence over the original four-view enumeration.
- Q: Binary vs tri-state theme toggle? → A: Binary toggle only (Light/Dark). `prefers-color-scheme` used solely as initial default when no stored preference exists; explicit user choice always wins.
- Q: CSS tokens vs Tailwind dark: coexistence? → A: Replace all color-related Tailwind `dark:` variants with CSS custom property tokens. Retain `dark:` only for non-color concerns (e.g., shadows).
- Q: Dark mode contrast ratio target? → A: WCAG AA (4.5:1 normal text, 3:1 large text/UI components). Verified via automated token-value checking.
- Q: Cross-tab theme synchronization? → A: Out of scope. Each tab operates independently. Theme changes apply on next navigation or refresh in other tabs.
- Q: OS preference override behavior? → A: Explicit user preference always wins over `prefers-color-scheme` changes. No dynamic OS-preference listener when a stored preference exists.
- Q: localStorage unavailable UX? → A: Silent fallback. Theme toggle remains functional but changes are session-only. No warning or indicator shown.
- Q: Responsive breakpoint strategy? → A: Tailwind default breakpoints (`sm:`, `md:`, `lg:`, `xl:`) with per-component decisions. Only outer guardrail mandated: single-column below 640px.

## Stress-Test Findings

### Session 2026-06-04

- **STF-001**: Scope Gap (HIGH) — Settings view (/settings) not enumerated in original view list. **Resolved**: Settings explicitly included as routable view; all SCs updated to reference "all routable views."
- **STF-002**: Cross-Reference Error (HIGH) — "Checks" listed as separate fourth view but no /checks route exists. **Resolved**: View list corrected to inventory (including check UI), activity log, modules, settings — matching actual route table.
- **STF-003**: Cross-Requirement Contradiction (MEDIUM) — FOUC inline script and ThemeProvider duplicate theme-resolution logic creating sync risk. **Resolved**: FR-002 updated to require shared source-of-truth between inline script and ThemeProvider.
- **STF-004**: Impossible Constraint (MEDIUM) — "≤640px" single-column conflicts with Tailwind `sm:` breakpoint activating at exactly 640px. **Resolved**: FR-003 changed to "below 640px (max-width: 639px or equivalent)."
- **STF-005**: Cross-Requirement Contradiction (MEDIUM) — Overlay "does not block page scrolling" vs. tap-to-dismiss are mutually exclusive. **Resolved**: FR-009 clarified — sidebar itself is scrollable when overflowed; underlying page scrolling behavior removed from requirement.
- **STF-006**: Untestable Requirement (MEDIUM) — CLS score of 0 without measurement methodology. **Resolved**: SC-005 replaced with Playwright visual comparison (screenshot diff before/after toggle).
- **STF-007**: Impossible Constraint (LOW) — 44×44px touch targets on horizontally-scrolled 6-column table at 320px. **Resolved**: SC-002 adds carve-out — scrollable table rows exempt from width requirement; height ≥44px.
- **STF-008**: Untestable Requirement (LOW) — "all UI elements" is unbounded. **Resolved**: FR-001 tightened with concrete scope (text, controls, tables, forms, badges, indicators) and WCAG AA contrast metric.
- **STF-009**: Scope Creep (LOW) — Container-queries plugin prescribed but component extraction excluded. **Resolved**: Container-queries plugin removed from Implementation Signals; existing Tailwind breakpoints sufficient for monolithic structure.
