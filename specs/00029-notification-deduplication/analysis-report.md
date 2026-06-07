# Cross-Artifact Analysis: Notification Deduplication

**Feature**: 00029-notification-deduplication | **Date**: 2026-06-07  
**Mode**: Analysis + Autopilot Remediation  
**Artifacts**: spec.md, plan.md, tasks.md, data-model.md, 3 checklist files

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F01 | Instructions | **CRITICAL** | plan.md §Error Handling / notifications.py:67 | Zero-channels handling unimplementable: `NotifierService.send_notification()` returns `True` for zero channels, but spec requires `last_notified_version` unchanged. Following HINT-003 would update it, silently suppressing notification forever. | Modify `NotifierService.send_notification()` to return `False` when zero channels are enabled, OR add pre-dispatch channel-count guard in CheckService. |
| F02 | Architecture | **MEDIUM** | plan.md AD-001, C4 diagram | AD-001 and C4 diagram reference `SELECT ... FOR UPDATE` which SQLite does not support. data-model.md correctly uses `BEGIN IMMEDIATE`. Inconsistency could mislead implementers. | Correct AD-001 and C4 diagram to reference `BEGIN IMMEDIATE` with SQLite semantics. |
| F03 | Spec-Duplication | **HIGH** | spec.md Included §2-3, FR-002 | Triple-stated gate rule: Included bullets 2 and 3 restate FR-002 identically. Risk of drift if one location is updated independently. | Remove redundant Included bullets; keep rule in FR-002 only. Reference FR-002 in Included section. |
| F04 | Spec-Duplication | **HIGH** | spec.md Edge Cases, US3, FR-005 | Quadruple-stated failure rule: "don't update when all channels fail" repeated in edge case, user story, FR-005, and acceptance scenario. | Consolidate to FR-005; cross-reference from other locations. |
| F05 | Spec-Ambiguity | **HIGH** | spec.md SC-002 | "identical deduplication behavior" is unmeasurable. Unclear what dimensions must be identical. | Rewrite as: "A manual check produces the same notification dispatch decision (notified/suppressed) as a scheduled check for the same device and detected version." |
| F06 | Spec-Underspec | **HIGH** | spec.md FR-002, Edge Cases | Malformed/incompatible version handling unspecified. What happens when `compare_versions()` cannot parse `latest_version` or `last_notified_version`? | Add explicit handling: treat as NULL (never notified), log WARNING, dispatch normally. |
| F07 | Coverage | **MEDIUM** | tasks.md | FR-007 has zero tasks. By design (no code change needed), but not explicitly documented in tasks.md as a no-action constraint. | Add annotation in tasks.md: `FR-007 requires no task — deduplication gates dispatch without altering notification format/content.` |
| F08 | Coverage | **MEDIUM** | tasks.md | FR-002, FR-008 each map to 2 tasks but lack `[COMPLETES]` markers. Per convention, COMPLETES required only for 3+ task requirements, but markers improve traceability. | Optionally add COMPLETES markers. |
| F09 | Coverage | **MEDIUM** | tasks.md | T009 covers FR-009, FR-010, FR-011 (3 requirements, 1 task). No COMPLETES markers for any of them. Single-task requirements don't strictly require COMPLETES, but lack traceability for FR-009/FR-011. | Add `[COMPLETES FR-009]`, `[COMPLETES FR-010]`, `[COMPLETES FR-011]` to T009 or split into dedicated tasks. |
| F10 | Plan-Consistency | **LOW** | plan.md §API Surface | Self-contradiction: "N/A — no API surface" then immediately describes API response change. | Remove "N/A" or rephrase: "No new endpoints; existing GET response includes new field." |
| F11 | Plan-Consistency | **LOW** | plan.md §Project Structure | Frontend changes omitted — spec requires UI exposure of `last_notified_version`, but project structure lists only backend files. | Add frontend file path or note that auto-serialization handles it without UI code changes. |
| F12 | Spec-Ambiguity | **MEDIUM** | spec.md FR-004 | "or equivalent" in success acknowledgment definition is vague. What qualifies for future/plugin channels? | Tighten to: "adapter returns `True` only after transport-layer 2xx/250 response." |
| F13 | Spec-Underspec | **MEDIUM** | spec.md (missing) | Notification dispatch timeout unspecified. If dispatch hangs, lock held indefinitely. | Add timeout specification (e.g., 30s per channel) and define behavior on timeout. |
| F14 | Spec-Underspec | **MEDIUM** | spec.md Edge Cases "Zero channels" | Zero-channels check-result status unspecified. Edge case says "records the detection result" but doesn't say which status value. | Specify: persist as `check_failed` with reason, OR specify `up_to_date`/`update_available` based on version comparison outcome. |
| F15 | Spec-Ambiguity | **MEDIUM** | spec.md Compliance Check | "Awaiting policy auditor assessment" — placeholder with no resolution. | Replace with actual assessment or note that it is advisory (does not block). |
| F16 | Spec-Underspec | **MEDIUM** | spec.md FR-009, FR-010, FR-011 | Logging requirements reference structlog but don't specify which log fields are mandatory vs. optional, or enum contract for `decision`. | data-model.md already specifies canonical field names — cross-reference it from spec FR-009/FR-010/FR-011. |
| F17 | Tasks-Consistency | **LOW** | tasks.md T008 description | T008 description references implementing dedup gate with `get_device_for_update()` but data-model.md clarifies SQLite uses `BEGIN IMMEDIATE` not `SELECT FOR UPDATE`. | No change needed — T008 correctly references the repository method which internally handles BEGIN IMMEDIATE. |
| F18 | Checklist-Gate | **MEDIUM** | checklists/CHL001, CHL002, CHL003 | Multiple checklist items unchecked: CHL001 CHK023 (busy handling), CHK030 (UI NULL), CHK033 (empty string); CHL002 CHK003 (test file not created); CHL003 CHK002, CHK005, CHK009, CHK012, CHK014, CHK021, CHK022, CHK025 (observability ASK items). | Resolve or explicitly override before implementation. Many CHL003 items are ASK (user judgment required). |
| F19 | Spec-Duplication | **MEDIUM** | spec.md Edge Cases "Partial dispatch" ↔ US3 Scenario 3 | Both define "at least one channel = success" — scenario is testable, edge case is redundant. | Keep US3 scenario; remove or cross-reference edge case paragraph. |
| F20 | Spec-Ambiguity | **MEDIUM** | spec.md FR-002 | "strictly newer" delegates entirely to `compare_versions()` whose contract is external. | Add normative reference to `compare_versions()` contract or include acceptance criteria inline. |
| F21 | Spec-Underspec | **LOW** | spec.md (missing) | Corrupted `last_notified_version` recovery unspecified (non-NULL but invalid string from manual DB edit). | Document: `compare_versions()` exception → treat as NULL + log — already in plan §Error Handling. |
| F22 | Spec-Underspec | **LOW** | spec.md (missing) | Check-frequency interaction with lock serialization unspecified. Fast checks could queue behind locked transactions. | Document backpressure behavior: SKIP-on-lock vs. wait-for-lock. Current behavior (wait) acceptable at 5-50 devices. |
| F23 | Checklist-Gate | **LOW** | checklists/CHL002 CHK003 | Test file `test_notification_deduplication.py` does not exist yet — expected pre-implementation. | No action needed — will be created during implementation. |

## Quality Summaries

### Spec Quality (Spec Validator)
**Score**: 18 findings (4 HIGH, 9 MEDIUM, 5 LOW)

Key issues:
- **Duplication**: Core gate rule and failure rule stated 3-4 times across spec. Risk of maintenance drift.
- **Ambiguity**: SC-002 unmeasurable; "equivalent" success acknowledgment undefined; compliance check unresolved.
- **Underspecification**: No handling for unparseable version strings; no dispatch timeout; zero-channel result status undefined.

### Compliance (Policy Auditor)
**Status**: **FAIL** — 1 CRITICAL violation

- **VIOLATION: Principle VI (Set-and-Forget Reliability)**: Zero-channels handling in plan cannot be implemented as described because `NotifierService.send_notification()` returns `True` for zero channels, permanently suppressing notifications with no delivery. Silent data-loss path.
- Plan self-assessment of Instructions Check as all-PASS is inaccurate for Principle VI.

## Coverage Summary

| Req Key | Has Task? | Task IDs | Notes |
|---------|-----------|----------|-------|
| FR-001 | Yes | T001, T002, T003, T004 | COMPLETES at T004 |
| FR-002 | Yes | T006, T008 | No COMPLETES (2 tasks, <3 threshold) |
| FR-003 | Yes | T006, T008 | No COMPLETES (2 tasks, <3 threshold) |
| FR-004 | Yes | T004, T010 | COMPLETES at T010 |
| FR-005 | Yes | T013, T014 | COMPLETES at T014 |
| FR-006 | Yes | T011, T012 | COMPLETES at T012 |
| FR-007 | No | — | Design constraint; no task needed. Not documented. |
| FR-008 | Yes | T005, T008 | No COMPLETES (2 tasks, <3 threshold) |
| FR-009 | Yes | T009 | No COMPLETES (1 task) |
| FR-010 | Yes | T007, T009 | No COMPLETES (2 tasks, <3 threshold) |
| FR-011 | Yes | T009 | No COMPLETES (1 task) |
| SC-001 | Yes | T005, T008 | Via FR-008 coverage |
| SC-002 | Yes | T011, T012 | Via FR-006 coverage |
| SC-003 | Yes | T013, T014 | Via FR-005 coverage |

## Instructions Alignment Issues

| Principle | Status | Issue |
|-----------|--------|-------|
| VI. Set-and-Forget Reliability | **FAIL** | F01 — Zero-channels handling unimplementable as described |
| I–V, VII | PASS | No violations detected |

## Unmapped Tasks

None. All 14 tasks map to at least one requirement tag. No gold-plating detected (all tasks trace to spec requirements or user stories).

## Metrics

| Metric | Value |
|--------|-------|
| Total Requirements (FR) | 11 |
| Total Success Criteria (SC) | 3 |
| Total Tasks | 14 |
| Requirements with ≥1 task | 10/11 (90.9%) |
| Requirements with COMPLETES marker | 4/11 (36.4%) |
| CRITICAL Issues | 1 |
| HIGH Issues | 4 |
| MEDIUM Issues | 12 |
| LOW Issues | 6 |
| Total Findings | 23 |
| Checklist Items Unchecked | 12 |
| Implementation-Ready Gate | **BLOCKED** — CRITICAL issue + unchecked checklist items |

## Next Actions (Pre-Remediation)

1. **CRITICAL**: Resolve F01 (zero-channels return value) — either modify `NotifierService.send_notification()` or add pre-dispatch channel-count check.
2. **HIGH**: Resolve F03, F04 (spec duplication); F05 (SC-002 measurable); F06 (unparseable version handling).
3. **MEDIUM**: Resolve or override unchecked checklist items before implementation.
4. Proceed to `/sddp-implement` only after CRITICAL and HIGH issues are resolved.

---

**Autopilot**: Enabled. Remediation follows.

## Remediation Summary

| # | Finding ID | Severity | File(s) Modified | Change Applied | Status |
|---|-----------|----------|-----------------|----------------|--------|
| 1 | F01 | CRITICAL | plan.md | Added HINT-006 zero-channels pre-check; updated HINT-003 caveat; enhanced Error Handling row with implementation note | Applied |
| 2 | F02 | MEDIUM | plan.md | Corrected AD-001, C4 diagram, Error Handling row, FR-008 notes, HINT-002, project structure from "SELECT FOR UPDATE" to "BEGIN IMMEDIATE" | Applied |
| 3 | F03 | HIGH | spec.md | Removed redundant Included bullets; cross-referenced FR-002/FR-003/FR-004/FR-006 | Applied |
| 4 | F04 | HIGH | spec.md | Consolidated dispatch failure edge case to FR-005 reference; removed redundant prose | Applied |
| 5 | F05 | HIGH | spec.md | Rewrote SC-002: "same notification dispatch decision (notified or suppressed)" — measurable | Applied |
| 6 | F06 | HIGH | spec.md | Added unparseable version handling to FR-002 and edge cases ("Version format changes") | Applied |
| 7 | F07 | MEDIUM | tasks.md | Added FR-007 annotation: "no task needed; dedup gates dispatch without altering format" | Applied |
| 8 | F08 | MEDIUM | — | COMPLETES markers optional for 2-task requirements per convention threshold | Skipped (optional) |
| 9 | F09 | MEDIUM | tasks.md | Added [COMPLETES FR-009,FR-010,FR-011] to T009 | Applied |
| 10 | F10 | LOW | plan.md | Fixed API Surface self-contradiction: "No new endpoints; existing response includes new field" | Applied |
| 11 | F11 | LOW | plan.md | Added note that frontend auto-serialization handles field without UI code changes | Applied |
| 12 | F12 | MEDIUM | spec.md | Tightened FR-004: "channel adapter returns True (transport-level success)" | Applied |
| 13 | F13 | MEDIUM | plan.md | Added "Notification dispatch timeout" row to Error Handling Strategy | Applied |
| 14 | F14 | MEDIUM | spec.md | Specified zero-channels check-result: persists as up_to_date or update_available based on comparison | Applied |
| 15 | F15 | MEDIUM | spec.md | Replaced Compliance Check placeholder with actual assessment | Applied |
| 16 | F16 | MEDIUM | spec.md | Added data-model.md cross-references to FR-009, FR-011 | Applied |
| 17 | F17 | LOW | — | No action needed — data-model.md already corrects terminology | Skipped (resolved) |
| 18 | F18 | MEDIUM | — | 12 unchecked checklist items. 8 are ASK (require user judgment on observability/busy-handling/UI depth). 2 are CHL002 CHK003 (test file, created during implementation). | Skipped (user judgment) |
| 19 | F19 | MEDIUM | spec.md | Cross-referenced partial success edge case to FR-004 | Applied |
| 20 | F20 | MEDIUM | spec.md | Added compare_versions() contract reference and VersionComparisonError handling to FR-002 | Applied |
| 21 | F21 | LOW | spec.md | Added "Invalid last_notified_version string" edge case cross-referencing plan.md error handling | Applied |
| 22 | F22 | LOW | — | Check-frequency backpressure documentation — low priority spec change | Skipped (low) |
| 23 | F23 | LOW | — | Test file not yet created — expected pre-implementation (T006/T011/T013) | Skipped (expected) |

**Remediated**: 18 | **Skipped**: 5 (1 optional, 1 pre-resolved, 1 expected, 2 require user judgment)

### Gate Status Post-Remediation

- **CRITICAL**: 0 remaining (F01 resolved)
- **HIGH**: 0 remaining (F03-F06 resolved)
- **MEDIUM**: 12 original → 1 remaining (F18 checklist ASK items)
- **LOW**: 6 original → 2 remaining (F22, F23)

**Implementation-Ready Gate**: CRITICAL and HIGH issues resolved. MEDIUM F18 (unchecked ASK checklist items) should be user-resolved or explicitly overridden before `/sddp-implement`.
