---
feature_branch: "00037-catalog-persistence-and-write-ownership"
created: "2026-10-29"
input: "E032 Catalog Persistence and Write Ownership"
spec_type: "technical"
spec_maturity: "clarified"
epic_id: "E032"
epic_sources: "{PRD:CAP-016}{SAD:ADR-0004}{SAD:ADR-0015}{SAD:ADR-0017}{DOD:DDR-003}"
---

# Feature Specification: Catalog Persistence and Write Ownership

**Feature Branch**: `00037-catalog-persistence-and-write-ownership`  
**Created**: 2026-10-29  
**Status**: Draft  
**Spec Type**: technical  
**Spec Maturity**: clarified  
**Epic ID**: E032  
**Epic Sources**: {PRD:CAP-016}{SAD:ADR-0004}{SAD:ADR-0015}{SAD:ADR-0017}{DOD:DDR-003}  
**Product Document**: [specs/prd.md](../prd.md)

## Problem Statement

Inventory currently stores source model text and per-device checks, with independently committing repositories sharing a lifespan connection. Maintainers need a persistent model/observation foundation and coherent write ownership before shared refresh and reliable local fan-out can be enabled. Without this prerequisite, compatibility variants can be conflated and concurrent writers can commit unrelated partial work.

## Scope

### Included
- Offline additive catalog/observation/work migration preserving existing V1 monitoring and all inventory/source/history data.
- Stable variant-safe model identity, aliases/source identifiers/links, safe explicit legacy linkage, installed-unknown representation, revisions and independent verification status.
- Dedicated caller-owned write units and transaction-aware repositories across every existing writer.
- Durable refresh, reevaluation, intent and attempt persistence primitives for later epics, with executable migration/rollback/restart/concurrency tests.

### Excluded
- V2 module negotiation and official-source enumeration: E033/E035 own these contracts.
- Enabled catalog refresh scheduling, fan-out/comparison/delivery workers: E034/E036 own lifecycle behavior.
- New catalog APIs or UI/onboarding: E037/E038 own these surfaces; retain existing V1 behavior.
- Full catalog release readiness: E039 owns integrated release validation.

### Edge Cases & Boundaries
- Empty and populated databases, failed backup/migration, concurrent writers, cancellation, busy timeout and restart.
- Renamed/duplicate display names, multiple compatibility variants, ambiguous/missing identity and cross-module links.
- Failed/partial enumeration or model verification retains last successful knowledge without freshening it; missing referenced models survive.
- Unknown installed firmware is not latest firmware and cannot imply current. Existing installed strings and delivered history remain intact.

## Technical Objectives

### Objective 1 - Persist compatible catalog identities (Priority: P1)
**Why this priority**: Stable independent model identity blocks every downstream catalog capability.
**Rationale**: Owned devices must not define the catalog or collapse firmware-incompatible variants.
**Deliverables**: Additive schema, typed persistence records/repositories, exact resolver and explicit legacy/unknown device state.
**Validation Criteria**:
1. **Given** empty or populated V1 storage, **When** startup migrates offline, **Then** identities, controls, endpoint metadata, installed values and notification history survive without invented models.
2. **Given** same source key with distinct variants or a renamed model, **When** persisted/reopened, **Then** variants remain distinct and the renamed model retains UUID.
3. **Given** ambiguous, unverified or foreign-module candidates, **When** linking, **Then** linkage is rejected or remains visibly unresolved.
4. **Given** a failed pre-migration backup or a failing migration statement, **When** startup attempts an upgrade, **Then** startup fails and no schema/data/version changes leak; a later reopen verifies the original state.
5. **Given** an incomplete or failed enumeration, **When** its attempt is saved, **Then** unseen models remain retained and are not marked missing.

### Objective 2 - Establish coherent write ownership (Priority: P1)
**Why this priority**: Atomic observation/work persistence is unsafe until all existing writers respect ownership.
**Rationale**: Per-operation commits on a shared connection cannot protect multi-repository transactions.
**Deliverables**: Dedicated bounded write unit, noncommitting participating repositories and migrated runtime writers.
**Validation Criteria**:
1. **Given** two independently scheduled writers, **When** one fails after a partial mutation, **Then** the other cannot commit its work and all of the failed unit rolls back.
2. **Given** existing V1 checks, cache updates, notification configuration, scheduler and device actions, **When** executed, **Then** behavior remains operational with network outside transactions.

### Objective 3 - Persist dormant durable-work primitives (Priority: P1)
**Why this priority**: Later refresh/delivery increments need restart-safe shared contracts.
**Rationale**: Process-only work or version-only notification deduplication cannot support atomic recovery.
**Deliverables**: Refresh generations/cursors/budgets/leases, reevaluation generation/revision work, unique channel intents and attempts with fenced claims.
**Validation Criteria**:
1. **Given** the new atomic observation/device persistence contract, **When** its unit commits or rolls back, **Then** corresponding work is committed or rolled back with it and remains recoverable after restart; ordinary V1 mutations do not enqueue dormant work.
2. **Given** repeated concurrent intent insertion/claim, **When** executed, **Then** one identity and exclusive claim persist, stale tokens cannot finalize, and uncertain sends are not automatically replayable.
3. **Given** a delivered channel intent, **When** reevaluation or a competing claim repeats, **Then** the successful channel cannot be claimed or dispatched again; a failed channel retains independent retry state.

### Technical Constraints
- Raw parameterized SQLite/aiosqlite only, single backup-able volume, append-only migrations, fatal backup prerequisite, no migration network or new service.
- WAL and 5-second busy timeout on dedicated write connections; no lock layered over independently committing shared connections, no network inside a transaction.
- Preserve existing runtime contracts and IDs; runtime source stays under backend/src/. Strict typing, lint, security, coverage and applicable regression gates are real executions.

## Integration Points
- **IP-001**: E002 migration runner/backup gate and repository base supply storage and connection lifecycle.
- **IP-002**: E006 device repository and E014 notification configuration/history retain V1 behavior while gaining ownership/revision support.
- **IP-003**: E031 Canon endpoint repository/cache retains separate less-than-24-hour freshness and invalidation; firmware observations are separate.
- **IP-004**: Scheduler, checks, module lifecycle, seeding, settings, activity and notifier writers all consume the same write-ownership boundary.
- **IP-005**: E033–E039 consume stable persistence/unit-of-work contracts without enabling their unfinished behaviors here.

## Requirements

### Technical Requirements
- **TR-001**: System MUST apply append-only offline migrations to empty/populated databases only after a successful pre-migration backup; the entire pending startup upgrade MUST atomically roll back failed schema/data/version changes, including earlier pending scripts.
- **TR-002**: System MUST preserve module/device IDs, names, installed values, delivered history, intervals/pause, source guidance and endpoint metadata, without manufacturer requests or fabricated catalog entries during migration.
- **TR-003**: System MUST persist a stable model UUID unique by module/source key/canonical compatibility variant; display renames/aliases MUST NOT change identity or merge region/mount/hardware revisions.
- **TR-004**: System MUST persist names, aliases/source IDs and links, last-seen/active-missing status, enumeration attempt/outcome and separate enumeration last-success metadata across restart; partial/failed enumeration MUST NOT mark absent models missing.
  Only an authoritative complete module-scope scan may mark unseen models missing; a validated later sighting restores active status without changing UUID or observation history.
- **TR-005**: System MUST persist matching verified firmware or authoritative no-firmware with provenance/time/generation separately from model verification attempt/outcome/error; failure MUST NOT advance successful verification or erase last-known results.
- **TR-006**: System MUST support nullable catalog linkage only with explicit legacy/unresolved state, retain referenced missing models, reject cross-module model links, and resolve legacy inventory only against one exact uniquely verified compatible identity: same module, authoritative stable source key and complete canonical variant with explicit identity-verification evidence. Absent variant components are exact unspecified values, not wildcards; firmware success or display-name/alias matching alone MUST NOT prove identity.
- **TR-007**: System MUST persist explicit installed-unknown state and device revisions without replacing preserved installed strings with latest firmware. Blank installed strings migrate as unknown while original text is retained; setting a nonblank installed value clears unknown, while explicit unknown takes precedence over retained text. Existing check/status surfaces MUST label unknown/incomparable rather than current and MUST NOT notify from unproven comparison. Comparison-relevant installed/identity/confirmation changes advance revision; check timestamps/watermarks do not. V1 results MUST be revision/identity-fenced after network work.
- **TR-008**: System MUST expose caller-controlled dedicated-connection write units with short WAL transactions, foreign-key enforcement, bounded busy timeout and close on every exit; participating repositories MUST NOT commit independently. Exceptions/cancellation before commit submission MUST roll back. Once commit is submitted its completion MUST be drained and the durable outcome established before closing; cancellation may coincide with a committed unit and MUST NOT be reported as rollback.
- **TR-009**: System MUST migrate all existing write participants coherently, including devices, modules, scheduler/checks, Canon cache, seeding/settings, activity, notifier and notification configuration; network/dispatch MUST occur outside transactions and another writer MUST NOT commit a failed unit's work.
- **TR-010**: System MUST persist refresh scope/config generations, finite budgets/consumption/deadlines, cursor/completeness/progress and fenced leases, plus bounded reevaluation work keyed by model observation generation or device revision; new persistence contracts MUST commit mutations and queued work atomically. Bounded chunk effects/cursor updates MUST share ownership and generation fencing; restart MUST NOT replenish budgets. Separate device-revision work prevents concurrent additions being skipped.
- **TR-011**: System MUST persist unique device/canonical-target-version/stable-channel-ID intents and immutable attempt evidence with exclusive token/generation claims and pending/sending/delivered/failed/uncertain/superseded states. Canonical version equality MUST match supported version-comparison equality; opaque versions remain conservative and display text is retained. Token-checked transition to sending authorizes dispatch; sending expiry/interruption MUST become uncertain, never automatic takeover. Stale tokens MUST NOT finalize current intent state but MAY append evidence to their original attempt. Delivered channels MUST NOT be reclaimed. Explicit uncertain retry MUST persist duplicate-risk acknowledgement and a new fenced attempt; legacy aggregate watermark MUST remain separate, without invented per-channel evidence.
  Claim acquisition MUST atomically install the next exclusive token/generation; authorization and finalization MUST enforce current token/generation/unexpired lease and applicable device revision, linked observation and channel/module configuration fences. An obsolete or expired completion MAY append original-attempt evidence but MUST NOT mutate current intent/watermark state. Explicit uncertain retry additionally requires durable evidence that the original dispatcher stopped; lease expiry, restart assertion or acknowledgement alone is insufficient.
  Accepted stoppage evidence is a host-observed completion/join of the exact original dispatch task, or host-observed exit of its exact process instance (process identity includes a nonreusable start/instance identifier), bound to the original attempt/token/owner. A generic restart assertion or caller-provided stopped boolean is not proof. Without this evidence retry fails closed. Dormant persistence accepts a typed host attestation, not a new process supervisor.
- **TR-012**: System MUST keep new refresh/fan-out/delivery behavior dormant, preserve V1 check/cache/scheduler/notification regressions, and supply migration, rollback, restart, preserved-history, variant, atomic-work and deterministic writer-concurrency validation.
- **TR-013**: All new and migrated SQL paths MUST bind external/source-derived values, including identifiers used as data, variants, aliases, URLs, cursors and error/evidence text. SQL identifiers/order/fragments that cannot be bound MUST come exclusively from fixed code-owned allowlist mappings; unknown options MUST be rejected before execution. No caller/source text may become SQL syntax.
- **TR-014**: Authoritative identity evidence MUST attest a successful source response validated by the trusted source adapter against its authoritative source rules and parsed listing/detail identity, bound to the exact module/source-key/canonical-variant tuple. A caller URL, digest, firmware success or alias alone MUST NOT establish authority. E032 validates/persists the typed attestation using fixture-fed evidence; new source-specific parsers, V2 interfaces and live enumeration remain E033/E035 scope. SQL ownership guards MUST cover inserts and updates of device links, refresh items, verification attempts and observation-backed intents, including direct writes bypassing the resolver, and MUST reject parent identity/evidence changes that invalidate established references.
- **TR-015**: Before persistence or diagnostic emission, system MUST exclude credentials from attempt/verification/enumeration errors, immutable evidence, receipts, provenance/source URLs and logs. Exclude notification configuration, passwords, API/access/refresh tokens, bearer/basic credentials, cookies, authorization headers, webhook secrets and signed-URL credentials. Remove URL userinfo and query/fragment values; use allowlisted error codes/context rather than raw provider exception/response text, and retain only known credential-free bounded receipt identifiers (otherwise redact). Sanitization MUST precede append-only insertion, formatting/logging and length truncation; failed sanitization MUST yield a generic safe failure, never raw fallback. Configuration secrets remain only in their existing configuration store.

### Key Entities
- **CatalogModel**: Module-owned UUID and source/variant identity independent of physical ownership, with metadata, last-seen and enumeration status.
- **FirmwareObservation**: Verified matching result/provenance/time/generation, distinct from verification-attempt status.
- **Device**: Existing physical inventory with nullable stable model linkage, explicit legacy/unresolved label, independent installed/unknown and revision.
- **Refresh/Reevaluation work**: Durable scope/generation/cursor/budget/claim records, not enabled workers.
- **NotificationIntent/Attempt**: Durable per-device/version/channel uniqueness, state and fenced dispatch evidence; historical V1 watermark retained without invented channel evidence.
- **SourceEndpointMapping**: Existing separately expiring/invalidation-aware endpoint metadata, not firmware storage.

## Assumptions & Risks
### Assumptions
- Trusted-LAN single-user, one application instance and one SQLite volume remain authoritative.
- Exposure to untrusted networks is unsupported. Container execution remains non-root; modules are user-vetted, unsandboxed and in-process with full application privileges. SQL ownership/evidence guards and claim tokens are application-integrity/concurrency constraints, not authentication, module isolation or protection against fully privileged extensions; no new account service or security boundary is introduced.
- Existing V1 checker capability is retained; migration does not imply catalog capability.
- Explicit catalog workers and mutation APIs will consume these foundations in their owning epics.
### Risks
- **Hidden write participant** (likelihood: high, impact: high): Audit all commit/execute paths and test deterministic interleavings.
- **Unsafe identity backfill** (likelihood: medium, impact: high): Require exact verified variant evidence; default unresolved.
- **Interrupted transaction/delivery** (likelihood: medium, impact: high): Rollback on cancellation, durable fenced work and uncertain evidence; no automatic ambiguous resend.

## Implementation Signals
- `NEW-ENTITY` — Catalog identities/observations and durable work/intent/attempt records.
- `MIGRATION` — Additive offline schema and explicit legacy/unknown/revision state.
- `BREAKING-CHANGE` — Internal write-ownership refactor; preserve external V1 contracts.

## Success Criteria
- **SC-001** [OBJ1]: Empty and populated upgrade/reopen tests preserve 100% of seeded legacy identity/history/control/endpoint fields; migration makes zero outbound requests.
- **SC-002** [OBJ1]: Rename, variant, ambiguous/unverified linkage, cross-module rejection, missing retention, independent attempt/success and unknown-version cases all pass.
- **SC-003** [OBJ2]: Deterministic independent-writer failure/cancellation tests show zero leaked mutations or cross-owner commits; existing V1 regression suite passes.
- **SC-004** [OBJ3]: Commit/rollback/restart tests prove mutation/work atomicity, cursor/generation fencing, unique intents and exclusive claims; no new workers are enabled.
- **SC-005** [OBJ2]: Backend strict typing/lint and automated tests pass with at least 80% coverage; applicable frontend, security and performance gates are recorded with real results.
- **SC-006** [OBJ2]: Security fixtures prove hostile SQL-shaped values remain literal or are rejected, unsupported dynamic query options execute no SQL, and no unrelated schema/data changes occur; credential-bearing URL/provider-error/receipt fixtures leave zero seeded secrets in persisted evidence or emitted diagnostics while retaining safe failure code/context.
- **SC-007** [OBJ1]: Exact-identity fixtures reject forged/mismatched/unvalidated evidence and foreign-module candidates; duplicate aliases never resolve identity, and explicit unspecified variant components match only unspecified components. A uniquely source-validated exact tuple links successfully; direct SQL ownership violations and reference-invalidating updates fail without durable residue.
- **SC-008** [OBJ3]: Deterministic concurrent-claim/authorization, lease expiry, stale token/revision/configuration, interrupted send, late acceptance and acknowledged retry fixtures allow at most one authorization per attempt, no automatic ambiguous redispatch and no stale intent/watermark mutation; explicit retry fails until original-owner stoppage is evidenced.

## Glossary
| Term | Definition |
|------|------------|
| Canonical variant | Stable normalized compatibility identity including region, mount and hardware revision, not a display label. |
| Unit of work | Caller-owned connection/transaction spanning participating repository mutations and exactly one commit or rollback. |
| Observation | Timestamped local verified source knowledge, not a fresh manufacturer check when read. |
| Fenced claim | Token/generation ownership checked on every completion to reject obsolete workers; a concurrency fence, not an authentication credential or module sandbox. |

## Compliance Check
- Specification size exception: explicitly authorized by the user on 2026-10-29 for E032. This exception does not waive behavioral, lifecycle, implementation or QC requirements, nor size limits on other artifacts.
- Spec Validator: PASS, 25/25 criteria. Policy Auditor: PASS with the authorized size exception; no remaining policy violations.

## Clarifications
### Session 2026-10-29
- Q: What is the failed-upgrade rollback boundary? -> A: The entire pending startup upgrade, including schema, data and version; historical SQL remains unchanged.
- Q: What does dormant mean for V1 mutations? -> A: Expose callable atomic persistence contracts, maintain revisions in existing writers, but do not enqueue new work or route V1 notifications through intents.
- Q: What establishes exact identity? -> A: Same module, authoritative source key and exact canonical variant with trusted-source attestation; current TR-006/TR-014 are authoritative. Missing dimensions are not wildcards; display text remains unresolved.
- Q: How does V1 represent unknown/incomparable installed firmware? -> A: Preserve installed text, classify blank as unknown, let explicit unknown win, clear unknown on nonblank entry, expose honest comparison status and suppress unproven alerts; only minimal existing-surface changes are in scope.
- Q: Which changes advance revisions? -> A: Comparison-relevant installed/unknown, module/model linkage and confirmation mutations; not check timestamps or notification bookkeeping. Reject stale V1 results after edits.
- Q: Which bounds are required now? -> A: Finite persisted budget/consumption/deadline, bounded chunks and generation-fenced progress; restart cannot reset exhaustion. Numeric source defaults remain in later epics.
- Q: What defines unique intent equality? -> A: One tested canonical-version key consistent with supported comparison equality plus stable persisted channel identity; preserve raw text and legacy aggregate history separately.
- Q: How do interrupted sends and late evidence behave? -> A: Current TR-011 is authoritative: uncertain quarantine, acknowledged explicit retry only with exact original-owner stoppage evidence, immutable original-attempt evidence and fenced state finalization.

### Activation Matrix
| Path | E032 activation |
|------|-----------------|
| Existing V1 device/check/cache/config writes | New ownership boundary and revision fences; no new work queues or intents. |
| Existing V1 notification path | Retained direct dispatch outside transactions and preserved legacy watermark. |
| New observation/device-plus-work persistence | Callable and integration-tested atomic contracts; not connected to production refresh/onboarding. |
| Refresh, reevaluation and delivery claims/transitions | Callable persistence primitives tested without source or notification network calls. |
| New schedulers/workers/dispatchers | Disabled; owned by E034/E036. |

## Stress-Test Findings
### Session 2026-10-29
- STF-001: Cross-Requirement Contradiction (HIGH) — Affected: TR-002, TR-007, TR-009, TR-012, SC-002 — Installed-unknown state has no defined V1 compatibility mapping. Resolved by explicit classification, state precedence/transitions and honest existing status surfaces in TR-007.
- STF-002: Cross-Requirement Contradiction (HIGH) — Affected: TR-009, TR-010, TR-012, OBJ3, SC-004 — Dormancy does not distinguish runtime enqueueing from dormant persistence capability. Resolved by the activation matrix and Objective 3/TR-010 boundary.
- STF-003: Concurrent Trigger Ambiguity (HIGH) — Affected: TR-008, TR-009, TR-011, OBJ3, SC-004 — Fenced finalization does not define exclusive dispatch authorization. Resolved by token-checked sending transition, uncertain quarantine and explicit acknowledged retry in TR-011.
- STF-004: Constraint Impossibility (HIGH) — Affected: TR-003, TR-005, TR-006, SC-002 — Exact verified identity lacks a defined evidence predicate. Resolved by exact source/variant identity evidence independent of firmware success in TR-006.
- STF-005: Concurrent Trigger Ambiguity (HIGH) — Affected: TR-008, TR-009, SC-003 — Cancellation rollback guarantee has no commit boundary. Resolved by pre-submission rollback and drained committed-outcome semantics in TR-008; cancellation tests cover before/during/after submission.
