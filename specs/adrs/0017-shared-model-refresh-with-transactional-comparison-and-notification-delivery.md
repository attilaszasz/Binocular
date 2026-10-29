---
adr_id: ADR-0017
status: accepted
date: 2026-10-29
tags: [scheduling, comparison, notifications, sqlite, concurrency]
supersedes: [ADR-0007]
superseded_by: ""
related_artifacts: [specs/prd.md#CAP-004, specs/prd.md#CAP-005, specs/prd.md#CAP-006, specs/prd.md#CAP-007, specs/prd.md#CAP-009, specs/prd.md#CAP-010, specs/prd.md#CAP-014, specs/prd.md#CAP-016, specs/project-plan.md, E032, E034, E036, E038, ADR-0012, ADR-0015, ADR-0016]
---

# ADR-0017: Shared model refresh with transactional comparison and notification delivery

## Status

Accepted. Supersedes [ADR-0007](0007-in-process-scheduling-with-apscheduler-and-apprise-notifications.md).

## Context

ADR-0015 separates stable, module-scoped firmware-compatible catalog models from physical devices. All active catalog-capable sources must refresh even with zero owned devices. Multiple copies of one model retain independent names, installed versions or explicit unknown state, and notification history. ADR-0016 supplies explicit V2 catalog negotiation and a labeled V1 manual-entry/per-model-check fallback, not inferred enumeration.

Previous per-device live checks and a single `last_notified_version` field cannot safely coordinate shared-result fan-out, concurrent device actions, channel-specific failures, retries, and restarts. A successful model observation must reach every linked device; adding a device, editing its installed version, and confirming an update must invoke the same comparison locally. A notifier failure must not erase successful source verification or trigger duplicate successful-channel sends.

The current repository uses one lifespan SQLite connection with per-operation commits, including scheduler/check/cache writers. It cannot safely host a multi-await transaction: another operation can interleave or commit work it does not own. Transactional snapshot, reevaluation, and outbox guarantees therefore require a coherent write-ownership refactor, not another lock or transaction wrapped around the existing shared connection.

Local accessible Add Device search and bounded Modules browsing/direct preselected creation remain database-only under ADR-0015. Opening, typing, browsing, or selecting never triggers manufacturer requests, and latest available firmware is never assumed installed. This decision governs their shared background comparison/notification effects, not a separate onboarding flow.

All durable state remains in the existing backup-able SQLite volume and all execution remains in the single container. No external broker, database, cloud catalog, or module sandbox is introduced. SMTP and Gotify do not universally provide idempotent external delivery; application deduplication cannot honestly promise end-to-end exactly-once receipt.

## Decision Drivers

- Prevent duplicate enqueue and concurrent dispatch from repeated, concurrent, or restarted actions.
- Make delivery outcomes, failures, and ambiguity observable without hiding missed alerts.
- Keep shared catalog scheduling restart-safe and independent of inventory count.
- Preserve reliable comparison, explicit update confirmation, freshness, and independent physical-device state.
- Retain the small, single-container footprint and existing channels/configuration.

## Considered Options

### Option A: APScheduler shared refresh plus transactional SQLite outbox/claims

Retain in-process scheduling and channels, replacing write ownership and persisting shared refresh progress, local reevaluation, notification intents, and exclusive delivery claims in SQLite.

- **Pros**: Atomic durable work, restart recovery, per-channel deduplication/retry, and no new infrastructure.
- **Cons**: Requires connection/transaction ownership refactoring and outbox/claim lifecycle complexity; external delivery can remain ambiguous.

### Option B: Retain per-device live checks and last-notified field

Keep inventory-driven source checks and suppress notifications using only each device's `last_notified_version`.

- **Pros**: Small change to existing scheduling and notification code.
- **Cons**: Repeats source work, omits zero-inventory refresh, permits concurrent duplicates, and cannot safely recover partial fan-out or channel failures.

### Option C: External queue/broker

Move refresh and delivery coordination to an external queue and worker infrastructure.

- **Pros**: Established distributed scheduling and delivery tooling.
- **Cons**: Violates self-contained, no-broker constraints and increases deployment/backup complexity; does not itself eliminate external delivery ambiguity.

## Decision Outcome

Chosen option: **A APScheduler shared refresh plus transactional SQLite outbox/claims** — use in-process inventory-independent catalog refresh and transactional local reevaluation/outbox with durable per-device deduplication and exclusive channel delivery claims.

**Scheduling and refresh ownership.** Retain APScheduler 3 in the application process and Apprise for responsive HTML Email/SMTP and Gotify, including existing environment-variable initialization/sync. Catalog jobs are keyed by module identity and negotiated catalog capability, not device count. Every active, unpaused catalog-capable module refreshes at its module-wide frequency, including zero-inventory modules. Pause disables automatic monitoring, not explicit manual refresh. Reconstruct scheduling from durable module controls and run state after restart; coalesce missed windows rather than replaying a request/alert storm.

Explicit module/model refresh and single/bulk inventory checks enqueue background work. Normalize inventory requests to unique compatible catalog model identities and coalesce overlapping manual and scheduled work. Reuse shared indexes within the refresh scope, performing model details only where needed; owned-copy count must not multiply source work. Legacy V1 modules transparently retain labeled owned-device/per-model checking under ADR-0016 when no catalog capability exists; do not claim zero-inventory enumeration or invent a checker for unresolved inventory.

Use bounded per-module batches, per-model deadlines, finite end-to-end run budgets, and fair scheduling between modules. Persist run progress, continuation cursors, work generations, and bounded execution leases. Resume valid unfinished work after restart without indefinitely resetting exhausted budgets; exhausted runs terminate visibly as partial/failed. Module identity/configuration generations fence obsolete completions after incompatible updates. A broken module must not crash other jobs or the core. ADR-0012 governs centralized robots.txt enforcement, identifiable User-Agent, shared per-origin pacing on every attempt/retry, source-specific delay accommodation, backoff, and cancellation. Timeout/cancellation stops pending waits, retries, and further outbound requests; no direct module networking is permitted.

**Transaction ownership is a prerequisite.** Replace per-operation commits on the shared lifespan connection with caller-controlled units of work on a dedicated connection for each atomic write. Use SQLite WAL, its single-writer semantics, bounded `busy_timeout`, and bounded transactions. Repository methods participating in a unit of work must not independently commit. All write participants—including scheduler, checks, catalog/cache, devices, reevaluation, and notifier—must obey that ownership or use explicit autocommit outside the unit of work. A separate transaction lock on the existing shared connection is not an acceptable substitute. The old baseline restriction on multi-await lifecycle transactions is superseded only when this coherent ownership refactor is shipped. SQLite/raw parameterized SQL and the single database file remain unchanged.

Never hold a database transaction across manufacturer or notification network I/O. Fetch/validate outside the transaction, then persist only if its captured identity/work generation is still valid. Persist a successful matching live `FirmwareResult` observation and a durable model-reevaluation intent for **all** linked devices in one commit. Persist each device addition, installed-version edit, or update confirmation together with its new device revision and local reevaluation work in one commit. Notification failure cannot roll back successful source verification.

**Bounded, lossless local fan-out.** Drain durable model-reevaluation work in bounded chunks. In each chunk, atomically evaluate current device revisions against the applicable observation generation, insert/deduplicate eligible delivery intents, and advance the durable cursor. No unbounded transaction may cover an entire model's inventory. Leases, generations, and cursors make repeated or restarted chunk processing idempotent. A device added or changed concurrently with refresh queues its own reevaluation in its mutation commit, so cursor timing cannot lose a linked device. Obsolete jobs must not overwrite a newer device revision or model observation. Rebase obsolete evaluation onto current valid state or retain successor work; fencing must not silently discard the required reevaluation.

**One shared comparison path.** Successful model verification reevaluates every linked device independently. Device add/edit/confirmation reevaluates saved installed firmware against trustworthy fresh local observations without making a vendor request. Unknown installed firmware yields `unknown`; incomparable versions yield `comparison_unknown`, never current. Authoritative no-firmware, unavailable firmware, failed attempts, and stale observations remain distinct. Retained versions are labeled last-known with provenance, freshness, and failure status; unavailable/failed/stale knowledge cannot establish a new current or alert claim. A successful fresh verification is required to restore that eligibility. Freshness follows ADR-0015's module interval and remains separate from its less-than-24-hour endpoint-discovery validity.

Use the same source-aware version comparator for installed/latest comparison, newer-than-notified checks, and canonical deduplication keys. Never order versions lexically or guess an ordering when a source version is incomparable. Preserve a durable per-device, per-channel delivered watermark/history. Only a fresh verified version newer than both installed and that channel's delivered watermark can create a new notification intent; repeated equivalent canonical versions cannot create another intent. Multiple owned copies retain independent evaluation and delivery state.

**Explicit update confirmation and ordering.** One-click confirmation submits the displayed target version and observation ID with an optimistic expected device revision. Confirm exactly that displayed target, never an unseen newer observation that arrives before submission. Reject revision conflicts for visible reconciliation. Commit the installed-version/revision change and local reevaluation together, superseding obsolete unsent alerts without erasing delivered history. Installed-version edits follow the same revision discipline. Refresh/evaluation completions carry observation generations and device revisions so stale work cannot overwrite newer user actions. Latest available firmware never autofills the installed field at creation.

**Durable notification intents and claims.** Enforce unique delivery intent identity `(device_id, canonical_target_version, channel_id)`. An intent transitions through `pending`, `sending`, `delivered`, `failed`, `uncertain`, or `superseded`, with durable attempt/outcome history. Retrying a known failed channel reuses the same intent; a new attempt gets a distinct claim token/generation. Exclusive claims bind the unique work generation to a bounded lease, with compare-and-set state transitions against the claim and expected device revision. Stale workers cannot reclaim, finalize, or advance device watermarks using an obsolete token/revision.

Claim acquisition and outcome recording are short transactions; send outside them. Immediately before starting an outbound send, recheck installed version, observation eligibility, device revision, and whether the intent is obsolete. Supersede obsolete unsent work rather than dispatch it. Lease expiry alone is not permission to steal a claim while its old live dispatcher could still send: retain exclusive ownership until the old worker is known stopped. Fencing database updates is necessary but does not cancel an external send. On process restart, interrupted `sending` work is `uncertain`, not automatically returned to `pending`. Preserve any accepted-send evidence/history even when concurrent device changes prevent its obsolete revision from advancing current comparison state.

**Honest per-channel outcomes and retries.** Mark `delivered` only when the channel confirms acceptance, recording its channel-specific delivered state/watermark. SMTP acceptance or Gotify confirmation is not proof of final human receipt. Any aggregate `last_notified_version` retained for compatibility is only a projection; it must not suppress a failed/undelivered channel because another channel succeeded. Confirmation never resets delivered history. Successful channels are not resent when another channel fails.

Known definite failures remain visible and retryable with bounded automatic backoff or explicit retry through the same intent and claim path. A timeout or crash after possible acceptance is `uncertain`; do not automatically retry it. Operator-requested retry must explicitly warn of potential duplicate external delivery. Stable message IDs/idempotency mechanisms where supported may reduce risk but cannot eliminate it. The application prevents duplicate enqueue and concurrent dispatch; it does **not** promise external exactly-once delivery. An accepted message cannot be retracted if a device is updated during the in-flight send. Log and expose this boundary rather than disguising it as successful suppression or guaranteed delivery.

**Observability, health, and recovery.** Keep scraping/verification outcomes independent of notification outcomes. Structured activity includes run, module, model, device, delivery/attempt, and claim identifiers, bounded progress, terminal partial/failure status, and explicit retry/uncertain outcomes. Record catalog-enumeration attempts/last successes separately from per-model firmware attempts/last successes; neither notification success nor index enumeration manufactures firmware success. Official module health aggregates refresh failures even with zero inventory, distinguishing authoritative per-model no-firmware from scrape failure.

Persist catalog identity/observations, device revisions, schedules/controls, refresh cursors/leases, reevaluation, outbox, and delivery history in the same backup volume. Restore unknown in-flight deliveries as `uncertain`, fence old work generations, and resume durable unfinished local work without blindly replaying alerts. Preserve migrated device identities, independent installed versions, module controls, and known delivered history rather than resetting deduplication. This bootstrap amendment records the required future architecture; it does not claim that the transaction retrofit or feature implementation is complete.

## Consequences

### Positive

- Inventory-independent shared refresh and coalesced indexes/model work reduce repeated manufacturer requests across owned copies.
- Atomic observation/mutation plus reevaluation commits and bounded durable fan-out prevent lost device work across concurrency and restart.
- Per-device/version/channel uniqueness and exclusive claims prevent duplicate application enqueue/concurrent dispatch while preserving independent physical-device state.
- Channel-specific outcome history makes failed deliveries retryable without resending successful channels; verification remains valid when notification fails.
- Explicit freshness, revisions, and displayed-target confirmation preserve trustworthy comparisons and observable uncertainty.

### Negative

- Coherent repository connection/commit ownership refactoring is required before the transactional guarantees are safe.
- Durable run/fan-out cursors, outbox states, claims, fencing, and per-channel watermarks increase schema, lifecycle, migration, and concurrency-test complexity.
- Catalog knowledge can lag source changes until the next successful refresh; larger unowned catalogs require bounded fair pacing and visible partial work.
- SMTP/Gotify acceptance can be ambiguous after timeout or crash, requiring visible uncertain states and operator decisions; externally accepted messages cannot be recalled.

### Neutral

- APScheduler 3, Apprise, responsive HTML Email/SMTP, Gotify, and existing environment configuration remain; no new service or deployment infrastructure is required.
- Centralized pacing and the unsandboxed, user-vetted module trust boundary remain unchanged.
- Accepted architecture guides future delivery; this amendment neither implements it nor marks it release-ready.

## Links

- [PRD capabilities CAP-004, CAP-005, CAP-006, CAP-007, CAP-009, CAP-010, CAP-014, and CAP-016](../prd.md#product-capability-map)
- [Project instructions v2.0.0](../../project-instructions.md)
- [Project plan](../project-plan.md) — future E032, E034, E036, and E038.
- [ADR-0007: In-process scheduling with APScheduler and Apprise notifications](0007-in-process-scheduling-with-apscheduler-and-apprise-notifications.md) — superseded; in-process scheduler and channels retained.
- [ADR-0004: SQLite file storage with aiosqlite and raw SQL](0004-sqlite-file-storage-with-aiosqlite-and-raw-sql-no-orm.md)
- [ADR-0012: Source-aware centralized scraping](0012-source-aware-centralized-scraping-with-shared-per-origin-pacing-and-bounded-cancellation.md)
- [ADR-0015: Instance-local model catalog and verified firmware observations](0015-instance-local-model-catalog-and-verified-firmware-observations.md)
- [ADR-0016: Versioned catalog-capable module contract with V1 compatibility](0016-versioned-catalog-capable-module-contract-with-v1-compatibility.md)
- [SQLite transactions](https://www.sqlite.org/lang_transaction.html)
- [RFC 5321: Simple Mail Transfer Protocol](https://www.rfc-editor.org/rfc/rfc5321.html)
