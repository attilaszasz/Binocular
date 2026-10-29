---
adr_id: ADR-0015
status: accepted
date: 2026-10-29
tags: [catalog, sqlite, firmware, discovery, compatibility]
supersedes: [ADR-0014]
superseded_by: ""
related_artifacts: [specs/prd.md#CAP-001, specs/prd.md#CAP-004, specs/prd.md#CAP-005, specs/prd.md#CAP-015, specs/prd.md#CAP-016, specs/prd.md#CAP-017, specs/project-plan.md, E032, E034, E036, E037, E038]
---

# ADR-0015: Instance-local model catalog and verified firmware observations

## Status

Accepted. Supersedes [ADR-0014](0014-persisted-canon-firmware-endpoint-discovery-cache.md).

## Context

Manufacturer discovery and owned-device monitoring are different concerns. Inventory-driven live checking repeats discovery for identical physical devices, cannot expose unowned supported models, and makes onboarding depend on manufacturer availability. The accepted catalog-first PRD and project instructions require a persistent, instance-local catalog that refreshes independently of ownership and serves both Add Device and Modules browsing without outbound manufacturer requests.

Catalog models represent module-scoped firmware-compatible variants, not owned devices. Region, mount, and hardware revision can change firmware compatibility and must remain distinct. Each model needs stable identity, source keys, searchable aliases, display names, source links, a latest verified firmware or authoritative no-firmware observation, provenance, attempt outcomes, and verification timestamps. Multiple physical devices may reference the same model while retaining independent names, installed versions or explicit unknown state, history, and notifications.

ADR-0014 permits persistent endpoint-discovery metadata but prohibits storing firmware results. Explicitly timestamped firmware observations now need to survive restart for offline local browsing and shared comparison. Persisting an observation must not be confused with performing a live manufacturer verification or relaxing endpoint validity. Large catalogs and slow sources also require shared discovery, bounded work, fair scheduling, and visible partial progress rather than whole-catalog latency promises.

All state remains in the existing SQLite database and backup volume. “Shared” means inside this self-hosted instance only. No cloud catalog, external database, broker, or new service is introduced. The in-process, unsandboxed module trust boundary and centralized responsible-scraping policy remain unchanged.

## Decision Drivers

- Preserve local self-hosted data ownership without cloud dependencies.
- Represent freshness honestly and preserve firmware compatibility identity.
- Eliminate duplicated inventory-driven manufacturer discovery.
- Bound and pace source load while keeping large local catalogs usable.
- Migrate safely without losing inventory state or stable identity continuity.

## Considered Options

### Option A: Instance-local catalog observations

Persist module-scoped compatible models and verified firmware observations in SQLite; refresh them independently of ownership and serve catalog interaction locally.

- **Pros**: Shares reusable results across devices; permits offline browsing and unowned-model discovery; preserves stable compatible identity.
- **Cons**: Requires catalog schemas and migrations, explicit freshness semantics, and coordinated refresh work.

### Option B: Per-device live checking with endpoint-only cache

Retain inventory-driven checks and persist only reusable endpoint-discovery metadata.

- **Pros**: Preserves existing behavior and performs a live lookup on each check.
- **Cons**: Repeats discovery; provides no model enumeration or zero-inventory coverage; leaves onboarding and UI lookup slow and source-dependent.

### Option C: Central hosted catalog

Use a hosted catalog shared across separate Binocular instances.

- **Pros**: Reuses discovery across installations.
- **Cons**: Violates the no-cloud and data-ownership constraints and adds operational dependencies.

## Decision Outcome

Chosen option: **A Instance-local catalog observations** — persist module-scoped compatible models and firmware observations in SQLite, refresh independently of ownership, and serve all catalog interaction locally while retaining separate endpoint-cache rules.

**Identity and persistence.** Give each catalog model an internal UUID stable across display-name changes. Enforce uniqueness on `(module_id, source_model_key, canonical compatibility variant)`, preserving distinct region, mount, and hardware-revision variants. Persist source identifiers, aliases, display names, source links, provenance, enumeration and verification attempt outcomes, last-success timestamps, and the latest verified firmware/no-firmware observation. Exact aliases support search only; aliases and display-name equality do not establish identity. Compatible module updates preserve keys, UUIDs, device associations, and module controls; variants must never be merged automatically.

Devices retain their `module_id` foreign key and gain a nullable `catalog_model_id` during migration. A linked model must belong to the device's module; device type remains module-derived under ADR-0009. Backfill only an exact, uniquely verified compatible identity. Ambiguous or unresolved inventory is explicitly labeled rather than guessed, and no catalog rows are fabricated from old free-text inventory. Preserve device IDs, names, installed versions, history and notification state, module identity, refresh frequency, and pause state. Legacy per-model checks remain available only where a V1 checker exists. Explicit V2/V1 capability negotiation and contract migration belong to the successor to ADR-0005; this ADR does not invent enumeration support for V1 modules.

Failed or partial enumeration cannot delete models or imply a complete catalog. Mark a model missing only after a complete authoritative scan establishes its absence, retaining referenced rows and identity continuity. Enumeration attempts and successes are separate from per-model firmware attempts and successes; an index discovery alone is not a firmware verification unless that authoritative response actually verifies the matching model's firmware outcome.

**Verified observations and freshness.** Only a successful, authoritative, identity-matching live response advances a model's `verified_at`. A verified firmware version, explicit authoritative no-firmware outcome, unsupported model, and parsing failure are distinct outcomes. Unsupported/error responses must not fabricate success. Failed attempts retain the previous observation and its original provenance and verification time, alongside a visible failed status. In a partial module run, failed or unverified units do not advance their firmware `verified_at`; successfully verified models advance their own timestamps and remain eligible for normal fresh comparison and alerts independently of other models' failures. A partial module outcome must not block those successful units or imply that unverified units succeeded.

Observation age is fresh only while `now - verified_at < module refresh interval`, defaulting to daily; at exactly the interval it is stale. Stale observations or failed model verifications remain browseable but are not presented as fresh/current. Pause is a separately displayed scheduling status: it disables automatic refresh but does not itself invalidate a successfully verified, still-fresh observation or change shared comparison and alert semantics. Successful explicit manual verification while paused may restore normal fresh, eligible comparison and alerts under the same rules as any successful verification. Persisted firmware is explicitly labeled latest known, not a claim that the current UI interaction performed a live check. Latest available firmware never automatically fills installed firmware. Unknown installed versions and incomparable versions must never be labeled current.

Only a fresh successful observation is eligible to create a new update alert; stale comparisons are informational. Successful verification reevaluates every linked physical device, and device addition, installed-version edits, and update confirmation reevaluate locally through the same comparison logic. Shared fan-out, atomic notification intents/outbox work, concurrent deduplication, and per-channel retry/delivery semantics belong to the successor to ADR-0007; catalog persistence does not merge per-device notification state.

**Inventory-independent refresh.** Refresh every active, unpaused catalog-capable module, including modules with zero owned devices. Frequency and pause are module-wide; pausing automatic work does not disable explicit manual refresh. Explicit source/model/single-device/bulk checks operate as background refresh jobs, coalescing work by unique catalog model instead of repeating discovery per owned copy. Reuse shared manufacturer index responses where possible, including across per-model work in the same refresh, while supporting sources that require model-detail requests.

Execute fair, bounded batches with per-model deadlines and a finite run budget, honoring source-specific delays through the centralized host-provided HTTP client. ADR-0012's robots.txt, identifiable User-Agent, shared per-origin pacing, retry backoff, and cancellation rules apply to every outbound attempt; modules must not make direct requests. Successful units commit individually, partial progress and failure remain visible, and resumable cursors preserve progress between runs. Resumption must not produce indefinite no-completion loops: bounded exhausted work must surface a terminal partial/failed outcome rather than silently restart forever. No refresh may continue outbound work after timeout or cancellation.

**Separate endpoint-discovery validity.** Preserve ADR-0014's endpoint policy independently of firmware-observation age. A source-discovered endpoint mapping is usable only while `now - discovered_at < 24 hours`; at exactly 24 hours it expires and is bypassed. Cached-endpoint transport, HTTP status, parsing, or model-identity failure invalidates the mapping and permits one full-discovery fallback. If recovery cannot authoritatively verify the model, record visible failure without advancing firmware verification time. Persisted endpoint metadata survives restart; same-model live work remains coalesced. A shared index response avoids repeating index discovery per model in the same refresh, but does not bypass endpoint expiry, identity validation, or centralized pacing.

Persisting firmware as a provenance-bearing, explicitly timed local observation supersedes ADR-0014's prohibition on version storage, not its requirement that a new successful verification derive from an authoritative live response. Observation freshness follows the module interval; endpoint freshness remains strictly less than 24 hours. Neither validity period grants permission to bypass robots.txt, pacing, or live identity validation. Canon's 0–30-second uncontended warm single-model verification and 90–120-second cold discovery figures are model-level expectations, not whole-catalog deadlines or guarantees under contention.

**Local API and shared onboarding.** All UI GETs read the database only. Opening forms, typing, browsing, searching, and selecting models must never invoke modules or make manufacturer requests, including when catalog data is empty, stale, or failed. Explicit refresh/retry requests enqueue background jobs with HTTP `202 Accepted`; local status reads expose their loading, progress, partial completion, and failure. There is no automatic source request on browsing.

Add Device uses an accessible searchable local model combobox. Modules browsing/search uses the same local catalog API and stable selected model identity; aliases assist finding a model but do not replace its UUID. Query/result and rendered windows are bounded to at most 100 models, default 50, with pagination and scalable alias lookup rather than loading or rendering the whole catalog. Validate bounded local behavior against a 10,000-model fixture.

Modules shows inventory presence/count without preventing another physical copy. “Add to inventory” opens the same creation form with module and model preselected, requests the device's independent name and installed version/explicit unknown, and shares validation, comparison, and notification behavior with Add Device. Both entry points distinguish loading, no discovered models, no search matches, stale observations, failed/partial refresh, and unsupported legacy catalog capability. Capability controls, source guidance, canonical source links, and consumer-help links are local metadata; rendering them requires no source access. Preserve ADR-0013's optional source-link behavior for legacy modules and its distinction from scraping execution.

## Consequences

### Positive

- Shared discovery and model verification reduce duplicate work across owned copies and make unowned supported models discoverable.
- SQLite-backed local browsing and onboarding remain usable without manufacturer availability and preserve instance ownership of all catalog state.
- Stable compatibility identities and independent device state support multiple physical copies without conflating firmware or alerts.
- Explicit provenance, freshness, attempt outcomes, and partial progress distinguish verified knowledge from retained or uncertain results.

### Negative

- Observations can lag manufacturer changes until the next successful refresh; UI and alert eligibility must enforce freshness honestly.
- Refreshing unowned catalogs increases source load compared with inventory-only checking, requiring shared indexes, pacing, bounded work, frequency, and pause controls.
- Identity-safe migration, scalable local queries, fair batching, resumable progress, and refresh coordination add schema and lifecycle complexity.
- Ambiguous legacy mappings require visible resolution instead of automatic linking, and V1 modules remain limited until explicitly migrated.

### Neutral

- SQLite/raw SQL, the single-container deployment, backup boundary, and unsandboxed user-vetted module trust boundary are unchanged; no new service is required.
- ADR-0012 remains authoritative for outbound pacing, bounded budgets, and cancellation; local observations never authorize a network-policy bypass.
- Canon coverage remains the verified Canon Asia English EOS R and RF/RF-S catalogs. Cinema EOS/EOS R5 C, cinema lenses, adapters, extenders, unrelated mounts, regional fallback, and firmware-binary retrieval remain excluded; RF-S catalog support does not claim a verified positive firmware release.
- Module contract migration and durable shared comparison/notification coordination are separate decisions in the successors to ADR-0005 and ADR-0007.

## Links

- [PRD capabilities CAP-001, CAP-004, CAP-005, CAP-015, CAP-016, and CAP-017](../prd.md#product-capability-map)
- [Project instructions v2.0.0](../../project-instructions.md)
- [Project plan](../project-plan.md) — future E032, E034, E036, E037, and E038.
- [ADR-0014: Persisted Canon firmware endpoint discovery cache](0014-persisted-canon-firmware-endpoint-discovery-cache.md) — superseded; endpoint validity and live-validation safeguards retained above.
- [ADR-0004: SQLite file storage with aiosqlite and raw SQL](0004-sqlite-file-storage-with-aiosqlite-and-raw-sql-no-orm.md)
- [ADR-0005: Unsandboxed extension module engine with two-phase validation](0005-unsandboxed-extension-module-engine-with-two-phase-validation.md) — V2/V1 contract migration is assigned to its successor.
- [ADR-0007: In-process scheduling with APScheduler and Apprise notifications](0007-in-process-scheduling-with-apscheduler-and-apprise-notifications.md) — shared fan-out/outbox coordination is assigned to its successor.
- [ADR-0009: Module-Derived Device Type](0009-module-derived-device-type-remove-standalone-device-type-field.md)
- [ADR-0012: Source-aware centralized scraping](0012-source-aware-centralized-scraping-with-shared-per-origin-pacing-and-bounded-cancellation.md)
- [ADR-0013: Module-Declared Source URL for Device-Creation Lookup](0013-module-declared-source-url-for-device-creation-lookup.md)
- [RFC 9111: HTTP Caching](https://www.rfc-editor.org/rfc/rfc9111.html) — HTTP cache semantics are distinct from application observation freshness and endpoint-discovery lifetime.
- [WAI-ARIA APG: Combobox Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/combobox/)
