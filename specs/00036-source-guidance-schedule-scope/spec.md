---
feature_branch: "00036-source-guidance-schedule-scope"
created: "2026-10-07"
input: "Issue #12, entire scope"
spec_type: "product"
spec_maturity: "clarified"
epic_id: ""
epic_sources: ""
---
# Feature Specification: Sources
**Product Document**: `specs/prd.md`

## Problem Statement
Filenames obscure source choice. Incorrect guidance/scope risks wrong models or unintended pauses. Operators need verified guidance without identity or coverage changes.

## Scope
### Included
- Entire #12: guidance/scope/compatibility/disclosure/workflows/regressions.
- `research.md` defines eight official labels/types/coverage/examples/matching/regions/exclusions; examples are not exhaustive firmware guarantees.
- Canon: Asia English exact EOS R/RF/RF-S names only; exclude Cinema EOS/EOS R5 C, adapters/extenders, cinema lenses, unrelated mounts; no positive RF-S release verified.
### Excluded
- Coverage/matching expansion: evidence only.
- Crawling/new requests/dependencies/marketplace/pickers: local help suffices.
- Per-device scheduling/UI redesign: coordinate #4/#5/#7/#8.
- Flashing/cloud/telemetry/sandbox claims: excluded by product.
### Edge Cases & Boundaries
- Test zero/one/many/changed links, collisions, invalid/absent metadata/URLs, stale searches, near-match/no-firmware failures.
- Unknown counts/writes are not zero/saved; pause blocks pending starts.

## User Scenarios & Testing
### User Story 1 - Choose a Firmware Source (Priority: P1)
Operators choose verified sources.
**Why this priority**: Core source-choice value.
**Independent Test**: Compare eight sources with evidence.
**Acceptance Scenarios**:
1. **Given** eight sources, **When** displayed, **Then** names/types/coverage match research/Canon exclusions.

### User Story 2 - Enter a Source-Specific Model (Priority: P1)
Operators read source-specific help.
**Why this priority**: Prevent wrong input.
**Independent Test**: Switch sources in both forms.
**Acceptance Scenarios**:
1. **Given** either form, **When** selection changes, **Then** help/search reset.
2. **Given** Nikon XML/unsafe/absent URLs, **When** rendered, **Then** consumer help differs; unsafe/absent links cannot act; opener is prevented.
3. **Given** invalid/no-firmware models, **When** searched, **Then** failure appears.

### User Story 3 - Understand Monitoring Scope (Priority: P1)
Operators understand affected devices.
**Why this priority**: Hidden scope risks unintended pauses.
**Independent Test**: Test counts/pause/edits/restart/manual.
**Acceptance Scenarios**:
1. **Given** changing links, **When** refreshed, **Then** counts/inspection/scope agree or fail visibly.
2. **Given** pause, **When** selected, **Then** automatic-off warning/manual semantics appear.
3. **Given** successful pause, **When** pending execution/edits/restart/refresh occur, **Then** new starts stop; running work may finish.

### User Story 4 - Maintain Custom Sources (Priority: P2)
Authors retain compatibility/workflows.
**Why this priority**: Extensibility enhances P1 MVP.
**Independent Test**: Upload/upgrade; inspect keyboard/mobile disclosure.
**Acceptance Scenarios**:
1. **Given** custom filename replacements, **When** uploaded/upgraded, **Then** compatibility/state survive without official claims.
2. **Given** disclosure, **When** keyboard/mobile operated, **Then** Details/Create a Module/kit/upload/validation/AI copying/sharing/trust warning work.
3. **Given** excessive metadata, **When** validated, **Then** rejection explains limits; omissions work.

## Requirements
### Functional Requirements
- **FR-001**: System MUST separate readable labels from stable names/files/DB IDs.
- **FR-002**: System MUST provide eight sources' verified guidance per Scope/research.
- **FR-003**: System MUST correct Panasonic lens type/show Sony/Viltrox mixed coverage, not misleading inventory badges.
- **FR-004**: System MUST preserve Scope's Canon boundaries/exclusions/RF-S caveat.
- **FR-005**: System MUST place source before model in both forms; associate help; preserve free text/matching.
- **FR-006**: System MUST reset guidance/stale search feedback, including in-flight results, on source/model changes.
- **FR-007**: System MUST preserve canonical metadata/distinct human help; only absolute HTTP(S) links act; absent/unsafe links omitted; opener prevented.
- **FR-008**: System MUST render local help without new vendor requests/crawling/dependencies.
- **FR-009**: System MUST keep V1 omissions compatible with readable-name/existing-type fallbacks, no invented claims; excessive optional lengths/counts get clear rejection.
- **FR-010**: System MUST show consistent lifecycle/UI guidance; official claims require shipped verified provenance, not filename/custom inheritance.
- **FR-011**: System MUST preserve names/files/IDs/links/intervals/pause/protected replacements across additive migrations/seeding/refresh/upgrades, without false claims.
- **FR-012**: System MUST refresh linked counts/exact-member accessible lists or working filter links after membership changes.
- **FR-013**: System MUST explain beside controls: frequency/pause affects all N currently linked devices, including later membership; no mandatory reinspection.
- **FR-014**: System MUST label/warn paused selections: automatic off; manual single/bulk/search available without resuming.
- **FR-015**: System MUST block pending/new starts after successful pause across edits/restart/seeding/refresh; recheck active before execution; running checks may finish; explicit resume only.
- **FR-016**: System MUST prioritize guidance/scope; disclose internal name/path/version/author/contract/kit details in advanced controls; retain failures/last-success.
- **FR-017**: System MUST retain authoring/kit/upload/validation/AI copying/sharing; warn beforehand: user-vetted unsandboxed in-process code, full application privileges.
- **FR-018**: System MUST support keyboard/screen-reader/375px/mobile/desktop without color-only warnings/clipping.
- **FR-019**: System MUST distinguish loading/empty/failure/failed writes; unknown counts not zero, failed writes not saved.
- **FR-020**: System MUST preserve fixture correctness/failures; verify all scope/edge cases offline with isolated SQLite/browser, no real alerts.
### Key Entities
- **Source guidance**: Optional display/help metadata.
- **Linked device**: Association defining scope.
- **Module schedule**: Source-wide interval/pause.

## Assumptions & Risks
### Assumptions
- Research/manual semantics remain current; local help/free text suffice.
### Risks
- **Drift** *(likelihood: medium, impact: high)*: Verify fixtures.
- **State regression** *(likelihood: high, impact: high)*: Test pause/upgrades.
- **Overlap** *(likelihood: medium, impact: medium)*: Coordinate UI.

## Implementation Signals
- `NEW-UI` — Guidance/scope/disclosure.
- `NEW-API` — Compatible additions if needed.
- `MIGRATION` — Additive numbered SQLite changes.
- `NEW-CONFIG` — Optional bounded metadata.

## Success Criteria
### Measurable Outcomes
- **SC-001** [US1]: All eight sources match evidence/Canon exclusions and correct types.
- **SC-002** [US2]: Both forms show correct help; tested switches discard stale feedback; unsafe links never act.
- **SC-003** [US3]: Zero/one/many counts/inspection match current membership/scope.
- **SC-004** [US3]: Paused edits/restart/refresh start zero pending/new automatic checks; manual remains.
- **SC-005** [US4]: Custom/legacy upload/selection work; 100% tested upgrade state survives without false claims.
- **SC-006** [US4]: Keyboard/375px reaches workflows/warnings; invalid metadata feedback and omission compatibility work.

## Glossary
| Term | Definition |
|---|---|
| Source | Module-backed monitoring choice. |
| Canonical source | Existing scrape endpoint. |
| Human help | Consumer help, not new scrape target. |
| Paused | Automatic off; manual possible. |

## Clarifications
### 2026-10-07 — Autopilot defaults
- FR-007: Absolute HTTP(S)/omission/opener protection.
- FR-010/011: Verified shipped provenance/preserved replacements.
- FR-015: Successful pause blocks pending starts; running may finish.
- FR-012/013: Current membership/refreshed counts; no reinspection.
- FR-009: Recommend name 120/notes 1000/URL 2048 characters, 10 examples of 120; Plan owns limits/validation. Omissions compatible.

## Stress-Test Findings
STF-001: Security Boundary (HIGH) — Affected: FR-007 — Resolved requirements: HTTP(S)/omission/opener; verification pending.
STF-002: Cross-Requirement Contradiction (HIGH) — Affected: FR-010, FR-011 — Resolved requirements: verified provenance/replacements; verification pending.
STF-003: Concurrent Trigger Ambiguity (MEDIUM) — Affected: FR-015 — Resolved requirements: pending blocked/active recheck/running finish; verification pending.

## Compliance Check
Prior auditor FAIL: VII CRITICAL, 13,399 bytes pre-appendix; validator: 14,743 bytes/FR-010 leakage. I–VI artifact-compliant only. Mechanisms removed; revalidation/audit pending, no implementation/QC pass.

### Policy Auditor Compliance Check — 2026-10-07 rerun
**Status**: PASS — artifact only; no implementation/QC validation.
| Principle | Verdict | Evidence |
|---|---|---|
| I | PASS | FR-016/019/020: visible failures/last-success. |
| II | PASS | FR-008: no added requests; scraping policy unchanged. |
| III | PASS | FR-008/011/020: local state/no dependencies. |
| IV | PASS | FR-017: explicit unsandboxed/full-privilege warning. |
| V | PASS | FR-020: fixture correctness; typing policy unchanged. |
| VI | PASS | FR-011/015: state/pause preserved. |
| VII | PASS | Concise required sections; under 10 KB including audit. |
**Violations**: None against project instructions. Spec Validator separately flags invalid STF severity/category values. Planning and release gates remain pending.
