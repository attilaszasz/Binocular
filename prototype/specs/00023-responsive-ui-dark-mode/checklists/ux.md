# UX Requirements Quality Checklist: Responsive UI & Dark Mode
**Created**: 2026-06-04 | **Feature**: [spec.md](../spec.md)

## Completeness

- [ ] CHK001 Are CSS custom property tokens fully enumerated for all UI element states? FR-005 defines 5 tokens (--color-surface, --color-panel, --color-ink, --color-muted, --color-accent) — do these cover borders, input backgrounds, badge colors, hover states, disabled states, and focus rings? [Completeness, Spec §FR-005]
- [ ] CHK002 Is the localStorage-unavailable fallback behavior captured in the requirements? The clarifications and edge cases describe a silent, session-only fallback — but FR-008 does not incorporate this behavior. [Completeness, Spec §FR-008 / Edge Cases]
- [ ] CHK003 Are responsive breakpoints between 640px and 1280px defined? The spec mandates single-column below 640px (FR-003) and consistency at 1280px (US3) but leaves intermediate viewport behavior unspecified. [Completeness, Spec §FR-003 / US3]
- [ ] CHK004 Are all animatable UI properties covered by the prefers-reduced-motion requirement? FR-006 targets "sidebar/theme animations" — does this include button hover transitions, loading spinners, or focus-ring animations if they exist? [Completeness, Spec §FR-006]

## Clarity

- [ ] CHK005 What constitutes a "color-related" dark: variant subject to replacement under FR-005? The clarification permits retaining dark: for non-color concerns (e.g., shadows) but is ambiguous for border-color, outline-color, and ring-color utilities. [Clarity, Spec §FR-005 / Clarifications Q3]
- [ ] CHK006 What viewport threshold defines "narrow widths" for text truncation in FR-007? The requirement mandates CSS text-overflow at "narrow widths" without specifying whether this means below 640px, below 320px, or any width where content overflows its container. [Clarity, Spec §FR-007]
- [ ] CHK007 Which interactive elements are subject to the 44×44px touch-target mandate? US2 scenario 1 lists buttons, inputs, toggles — are sidebar nav links, module action buttons, and check-ui controls also in scope? [Clarity, Spec §FR-003 / US2 Scenario 1]

## Consistency

- [ ] CHK008 Does the "single-column below 640px" guardrail in FR-003 conflict with AD-003's per-component responsive decision? The spec mandates a single-column layout; the plan delegates breakpoint choices to individual components. Are components permitted to deviate from single-column below 640px? [Consistency, Spec §FR-003 / Plan AD-003]
- [ ] CHK009 Should the scrollable-table touch-target exemption in SC-002 also appear in FR-003? SC-002 exempts scrollable table rows from the 44px width requirement (height ≥44px required), but FR-003 states touch targets ≥44×44px without qualification. [Consistency, Spec §FR-003 / SC-002]

## Testability

- [ ] CHK010 How is "zero instances of unreadable text" in SC-001 objectively verified? The criterion is subjective; it references WCAG AA contrast ratios only indirectly through FR-001 — can it be operationalized as an automated contrast-ratio check? [Testability, Spec §SC-001]
- [ ] CHK011 Is the shared theme-resolution logic requirement in FR-002 testable as written? The requirement mandates identical logic between an inline script and a React component — a structural constraint. Is there a behavioral acceptance criterion (e.g., identical class applied for identical inputs)? [Testability, Spec §FR-002]
- [ ] CHK012 Are the specific CSS properties to be transitioned on theme toggle specified? SC-005 mandates <200ms with zero layout shift, but does not enumerate which properties (color, background-color, border-color, all) should animate — making visual-diff test scope ambiguous. [Testability, Spec §SC-005]

## Coverage

- [ ] CHK013 Are visible focus indicators specified for keyboard navigation in dark mode? The spec addresses focus return for the mobile sidebar (FR-009) but does not define focus-ring visibility or contrast requirements in either theme. [Coverage, Spec §FR-001 / FR-009]
- [ ] CHK014 Is the theme toggle button UI specified? US4 mentions "immediate icon update" but the toggle's placement, appearance, accessible label, and behavior during theme transition are undefined. [Coverage, Spec §US4]
