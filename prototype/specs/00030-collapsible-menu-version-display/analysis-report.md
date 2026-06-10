# Analysis Report: Collapsible Menu & Version Display (E029)

**Feature**: specs/00030-collapsible-menu-version-display/
**Date**: 2026-06-08
**Analyzed by**: SDD Pilot — Analyze Compliance (Phase 6)
**AUTOPILOT**: true

---

## Executive Summary

**Spec Quality Score**: 76/100 (Spec Validator)
**Policy Compliance**: PASS (Policy Auditor — 0 violations)
**Implementation Ready**: YES (scale risks mitigated, all P1 stories have tasks, no NEEDS CLARIFICATION markers, all checklists passed)

**Total Findings**: 9 (0 CRITICAL, 1 HIGH, 4 MEDIUM, 4 LOW)

---

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-001 | Contradiction | HIGH | spec.md §FR-006 (line 126), §Stress-Test Findings STF-003 (line 186) | FR-006 states "on write failure, the in-memory state remains collapsed for the current session" but STF-003 resolution says "on write failure revert in-memory state". These are contradictory — one preserves the toggle action, the other undoes it. Task E029-T010 follows FR-006's interpretation. | Reconcile FR-006 with STF-003 resolution. Choose consistent behavior: either (a) toggle stays in memory on write failure (as in current FR-006/T010), or (b) toggle reverts on write failure (as in STF-003 resolution). Update whichever artifact is wrong. |
| F-002 | Missing completion-point markers | MEDIUM | tasks.md — E029-T014, E029-T015, E029-T017 | FR-001 (7 tasks), FR-003 (5 tasks), FR-004 (3 tasks), FR-006 (3 tasks), FR-007 (3 tasks) each map to 3+ tasks but no task carries a `[COMPLETES FR-###]` marker on the last task carrying that requirement tag. | Add `[COMPLETES FR-001]` to T017, `[COMPLETES FR-003]` to T017, `[COMPLETES FR-004]` to T015, `[COMPLETES FR-006]` to T014, `[COMPLETES FR-007]` to T017. |
| F-003 | Underspecification | MEDIUM | spec.md §FR-001 (line 121) vs §SC-001 (line 160) | FR-001 does not specify transition duration or timing function; SC-001 introduces `duration-300 ease-in-out`. A success criterion should derive from the requirement, not add new specification. | Add transition specification (`motion-safe:duration-300 ease-in-out`) to FR-001 to make it self-contained; SC-001 should reference FR-001 rather than redefine. |
| F-004 | Ambiguity | MEDIUM | spec.md §FR-004 (line 124) | FR-004 says version tooltip follows "the same show/dismiss behavior as nav-item tooltips (per FR-003)" but does not clarify whether the ARIA attributes (`role="tooltip"`, `aria-describedby`) from FR-003 also apply to the version tooltip. | Explicitly state whether the version tooltip requires `role="tooltip"` and `aria-describedby` matching FR-003, or only the timing/dismiss behavior. |
| F-005 | Format deviation | MEDIUM | tasks.md (all 17 tasks) | Tasks use `**E029-T###**: description` format instead of the required structural contract: `- [ ] T### [P?] [US#|OBJ#?] {(FR|TR|OR|RR)-###?} [COMPLETES req?] Description`. Priority, user story, and requirement tags are in prose body not in the format line. | Update task format per structural contract — add inline priority `[P1]`, requirement tags `{FR-###}`, and completion markers `[COMPLETES FR-###]`. |
| F-006 | Documentation gap | LOW | spec.md §Clarifications (lines 177-178) | Clarification numbering jumps from Q007 (line 177) to Q009 (line 178). Q008 is missing, indicating incomplete traceability in the clarification record. | Restore missing Q008 entry or renumber sequentially (Q007→Q008→Q009). |
| F-007 | Subjective term | LOW | spec.md §Scope/Excluded (line 45) | "sensible default transitions consistent with the existing UI" uses subjective "sensible" — not testable or measurable. | Replace "sensible" with concrete reference (e.g., "uses the existing `duration-150` transition timing") or remove the qualifier. |
| F-008 | Pipeline gap | LOW | spec.md §Edge Cases (line 59), §FR-005 (line 125) | Dev mode (`npm run dev`) version fallback is described but no FR specifies how `VITE_APP_VERSION` is set in dev-mode. FR-005 covers only Docker build-arg mechanism. | Extend FR-005 or add FR-009 specifying how `VITE_APP_VERSION` is provided in dev-mode (e.g., `.env.local` file, `vite.config.ts` define, or predev script). |
| F-009 | Inconsistency | LOW | spec.md §FR-005 (line 125) vs §Edge Cases (line 59) | FR-005 specifies full command `git describe --tags --first-parent --always --dirty`; Edge Cases (line 59) says just "git describe output" without flags. This could cause confusion if someone wires up dev mode separately. | Use the same full command consistently everywhere `git describe` is referenced. |

---

## Quality Summaries

### Spec Quality (Spec Validator)
- **Score**: 76/100
- **Key strength**: Comprehensive spec with clear scope, edge cases, user stories, stress-test findings, and compliance audit.
- **Key defect**: Contradiction between FR-006 and STF-003 (F-001 — HIGH).
- **Minor issues**: Clarification Q008 gap, subjective terms, dev-mode pipeline gap.

### Compliance (Policy Auditor)
- **Status**: PASS
- **Violations**: 0
- **Advisory**: The plan's Testing Strategy table omits the Playwright E2E smoke test, but the existing `e2e/` suite is implicitly preserved by FR-007 regression coverage. Not a violation.

### Artifact Convention Compliance

| Artifact | Status | Issues |
|----------|--------|--------|
| spec.md | PASS with notes | Missing transition spec in FR-001 (F-003); ARIA ambiguity in FR-004 (F-004); minor documentation nits (F-006, F-007, F-008, F-009) |
| plan.md | PASS | All required sections present; <10KB; Instructions Check passed |
| tasks.md | PASS with notes | Missing `[COMPLETES ...]` markers (F-002); format deviation from structural contract (F-005) |
| checklists/ | PASS | All 3 checklists (UX, Testing, Performance) fully passed; all CHK### references in tasks.md resolve to existing checklist items |

---

## Coverage Summary

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| FR-001 | YES | T002, T003, T004, T011, T013, T014, T017 | 7 tasks — no COMPLETES marker on T017 |
| FR-002 | YES | T007, T016 | 2 tasks |
| FR-003 | YES | T005, T006, T011, T016, T017 | 5 tasks — no COMPLETES marker on T017 |
| FR-004 | YES | T008, T009, T015 | 3 tasks — no COMPLETES marker on T015 |
| FR-005 | YES | T001, T015 | 2 tasks |
| FR-006 | YES | T002, T010, T014 | 3 tasks — no COMPLETES marker on T014 |
| FR-007 | YES | T011, T013, T017 | 3 tasks — no COMPLETES marker on T017 |
| FR-008 | YES | T012, T017 | 2 tasks |

**Coverage**: 8/8 requirements (100%) — zero uncovered requirements.

### Unmapped Tasks
None — all 17 tasks have at least one requirement tag.

### Cross-Phase Dependency Edges
No `← T###:Symbol` or `→ exports: Symbol` annotations found. Nothing to verify.

---

## Instructions Alignment Issues

None found. Plan.md's Instructions Check self-assessment is accurate. All policy areas:

| Policy Area | Status |
|-------------|--------|
| Core Principles (I–VII) | PASS |
| Source Code Layout (ENFORCE_SRC_ROOT) | PASS — all files under `frontend/src/` |
| Technology Stack | PASS — React, Vite, Tailwind, TypeScript |
| Testing & Quality Policy | PASS — Vitest + RTL, ≥80% coverage |
| Governance | PASS — no amendments needed |

---

## Metrics

| Metric | Value |
|--------|-------|
| Total Requirements | 8 (FR-001 through FR-008) |
| Total Tasks | 17 |
| Coverage % | 100% (8/8) |
| Critical Issues | 0 |
| High Issues | 1 |
| Medium Issues | 4 |
| Low Issues | 4 |

---

## Definition of Done Check

| Implementation Ready Criterion | Status |
|-------------------------------|--------|
| Scale/Complexity risks mitigated in plan.md? | ✓ (Risk Mitigation table covers all 4 risks) |
| All P1 stories have tasks? | ✓ (US1→T003/T004, US2→T005/T006/T007) |
| No NEEDS CLARIFICATION markers? | ✓ |
| All checklists passed? | ✓ (UX, Testing, Performance — all `[X]`) |

**Verdict**: Implementation Ready (all gates passed).

---

## Next Actions

1. **RESOLVE F-001** (HIGH) — Reconcile FR-006/STF-003 contradiction before `/sddp-implement`. This is a blocking issue.
2. **Address F-002 through F-005** (MEDIUM) — Add COMPLETES markers, update FR-001/FR-004, fix task format.
3. **Consider F-006 through F-009** (LOW) — Minor documentation improvements.
4. **Proceed to**: `/sddp-implement` after resolution of F-001. Suggested prompt: "Implement E029 Collapsible Menu & Version Display. Tasks are defined in `tasks.md`. Resolve the FR-006/STF-003 contradiction by choosing behavior (a): on localStorage write failure, the toggle state stays collapsed in memory (per current FR-006 and T010). Apply all MEDIUM/LOW improvements as guidance."
