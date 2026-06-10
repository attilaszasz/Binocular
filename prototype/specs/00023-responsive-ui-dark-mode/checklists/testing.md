# Requirements Quality Checklist — Testing Domain

**Feature**: E016 Responsive UI & Dark Mode  
**Audit scope**: Testing requirements in [spec.md](../spec.md) and [plan.md](../plan.md)  
**Purpose**: Evaluate whether testing requirements are well-specified, complete, and traceable to functional/success-criteria requirements. Not a test-execution pass/fail checklist.

---

- [ ] CHK001 — Is the Playwright e2e tier formally included in the testing strategy tier table alongside Unit, Integration, and Coverage, rather than described only in prose below the table? [Completeness, Plan §Testing Strategy]
- [ ] CHK002 — Are Playwright dependencies (npm packages, `playwright.config`) and their installation status specified as prerequisites, given they are absent from `package.json` and no config exists in the repo? [Completeness, Plan §Testing Strategy]
- [ ] CHK003 — For SC-005's "zero pixel displacement" visual comparison, is the pixel-diff tolerance, comparison region, and screenshot-capture procedure (before/after toggle) defined? [Clarity, Plan §SC-005]
- [ ] CHK004 — Does the dark-mode e2e approach (`document.documentElement.classList.add('dark')`) verify the ThemeProvider toggle path and persistence, or only the CSS rendering outcome? [Coverage, Plan §Testing Strategy / Spec §FR-008]
- [ ] CHK005 — Where do Vitest snapshot tests fit in the testing strategy tier table? The risks section references running existing snapshots as mitigation, but no snapshot tier is declared in the table. [Completeness, Plan §Risk Mitigation / Testing Strategy]
- [ ] CHK006 — Is there a specified test methodology for verifying the 44×44px touch-target constraint (FR-003) at mobile viewports? [Completeness, Spec §FR-003]
- [ ] CHK007 — Is there an automated test methodology specified for verifying WCAG AA contrast ratios (4.5:1 body text, 3:1 large text / UI components) required by FR-001? [Completeness, Spec §FR-001]
- [ ] CHK008 — How is FOUC elimination (no white flash before first paint, FR-002) to be tested, given that e2e screenshots cannot reliably capture pre-paint timing? [Testability, Spec §FR-002]
- [ ] CHK009 — Does "≥80% on touched lines" define how "touched lines" are identified — git diff, files in the feature's change set, or lines flagged by coverage instrumentation? [Clarity, Plan §Testing Strategy / Coverage]
- [ ] CHK010 — Are test cases specified for the edge conditions enumerated in the spec: localStorage unavailable silent fallback, long device/module name truncation, and 50+ devices / 100+ log entries at 320px? [Completeness, Spec §Edge Cases & Boundaries]
- [ ] CHK011 — For SC-006, is the Playwright `prefers-reduced-motion` emulation method specified (e.g., `page.emulateMedia` vs. Chromium launch arg vs. CSS injection)? [Clarity, Plan §SC-006]
- [ ] CHK012 — SC-001 verification references "Manual audit + Playwright screenshots." Can the manual-audit portion be replaced with an automated contrast-ratio assertion to make the criterion fully machine-testable? [Traceability, Plan §Requirement Coverage Map / Spec §SC-001]
- [ ] CHK013 — Does "all routable view components" in the integration test scope explicitly enumerate which views (inventory/check UI, activity log, modules, settings) must render without errors in both light and dark modes? [Completeness, Plan §Testing Strategy]
