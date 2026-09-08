---
adr_id: ADR-0014
status: accepted
date: 2026-09-07
tags: [canon, cache, sqlite, scraping, reliability, concurrency]
supersedes: []
superseded_by: ""
related_artifacts: [specs/prd.md#CAP-015, specs/sad.md#architecture-decision-records, specs/project-plan.md, E028, E029, E031]
---

# ADR-0014: Persisted Canon firmware endpoint discovery cache

## Status

Accepted.

## Context

The Canon RF Cameras and Canon RF Lenses modules currently discover a model's firmware endpoint through Canon Asia catalogue, product, and firmware-action pages. Canon's shared source-declared crawl delay is 30 seconds and must remain centralized across both modules, requests, retries, manual checks, scheduled checks, and version search. Cold discovery therefore legitimately takes 90–120 seconds. Repeating discovery for known models adds avoidable requests and delay.

Firmware versions must remain live-discovered for every check. The cache may store only source-discovered lookup metadata, never an authoritative firmware result. An endpoint mapping is fresh only when `now - discovered_at < 24 hours`; at exactly 24 hours it is expired and bypassed. All state must remain in the existing SQLite file and survive restart. Expired discovery data may not be silently used. A failed cached endpoint must trigger invalidation and bypass followed by the existing catalogue-to-product-to-firmware flow; if that flow fails, the check must visibly fail while retaining last-success semantics.

## Decision Drivers

- Preserve Canon's 30-second shared centralized crawl delay, robots.txt checks, retries, deadline, and cancellation rules.
- Reduce warm check latency without caching authoritative firmware versions.
- Persist cache state in the existing SQLite database across restarts with forward-only numbered migrations.
- Prevent stale mappings from silently producing results.
- Provide deterministic tests for freshness, failure fallback, concurrency, and all check entry points.

## Considered Options

### Option A: Persisted fresh endpoint mapping cache

Store validated Canon model-to-firmware endpoint metadata with discovery timestamps in SQLite; a fresh mapping issues one normal `ScrapeClient` firmware request, while expired or failed mappings fall back to full discovery. Concurrent same-model callers, including warm-cache hits, coalesce to one centrally paced live firmware request and share that response; this is not an authoritative version cache.

- **Pros**: Reduces warm checks to one request; survives restarts; preserves centralized HTTP policy; has explicit stale and failure behavior.
- **Cons**: Adds schema, cache lifecycle, and concurrency coordination.

### Option B: Cache firmware versions

Store latest versions and return them without a live request.

- **Pros**: Fastest results.
- **Cons**: Can silently return stale version data and violates correctness requirements.

### Option C: In-memory endpoint cache

Keep mappings only inside module process memory.

- **Pros**: Simple implementation.
- **Cons**: Lost on restart and does not meet the persistent-state requirement.

### Option D: Always rediscover

Keep the full catalogue-to-product-to-firmware flow for every verification.

- **Pros**: No cache lifecycle.
- **Cons**: Causes repeated paced discovery and 90–120-second latency even when metadata is unchanged.

## Decision Outcome

Chosen option: **Persisted fresh endpoint mapping cache** — persist validated model-to-firmware-endpoint lookup metadata and its discovery timestamp in SQLite. Use a mapping only while `now - discovered_at < 24 hours`, then make one live, centrally paced firmware request; concurrent same-model callers coalesce and share that response without persisting it as an authoritative version. Invalidate and rediscover when the mapping is expired or its request fails.

## Consequences

### Positive

- Warm Canon verification needs one live firmware request and completes in 0–30 seconds, subject to shared pacing.
- Cached mappings survive process and container restart.
- Fresh mappings reduce source load while preserving robots checks and pacing.
- Cached-endpoint failures recover through one full discovery attempt.

### Negative

- Cold or expired lookup can still take 90–120 seconds.
- A migration and cache repository are required.
- Concurrent checks for the same model need single-flight or equivalent coordination to prevent duplicate discovery.

### Neutral

- Only endpoint metadata is cached; every successful version is parsed from a live firmware response.
- Manual checks, scheduled checks, and version search share the same cache rules.

## Links

- [PRD capability CAP-015](../prd.md#CAP-015)
- [Software Architecture Document — ADR-0012](../sad.md#architecture-decision-records)
- [Project plan](../project-plan.md)
- E028
- E029
- [E031: Canon Endpoint Discovery Cache](../plan/E031.md)
- [ADR-0012: Source-aware centralized scraping with shared per-origin pacing and bounded cancellation](0012-source-aware-centralized-scraping-with-shared-per-origin-pacing-and-bounded-cancellation.md)
