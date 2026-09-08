---
feature_branch: "00033-canon-endpoint-discovery-cache"
created: "2026-09-07"
input: "E031 Canon Endpoint Discovery Cache"
spec_type: "technical"
spec_maturity: "clarified"
epic_id: "E031"
epic_sources: "{PRD:CAP-015}{SAD:ADR-0012}{SAD:ADR-0014}"
---

# Feature Specification: Canon Endpoint Discovery Cache

**Feature Branch**: `00033-canon-endpoint-discovery-cache`
**Created**: 2026-09-07
**Status**: Draft
**Spec Type**: technical
**Spec Maturity**: clarified
**Epic ID**: E031
**Epic Sources**: {PRD:CAP-015}{SAD:ADR-0012}{SAD:ADR-0014}
**Product Document**: specs/prd.md

## Problem Statement

Canon checks rediscover endpoints for every request, causing repeated paced work. Durable discovery metadata must enable the 0-30 second warm path without returning stale endpoint or firmware data.

## Scope

### Included

- Durable Canon camera and lens model-to-firmware-endpoint discovery metadata with a strict 24-hour lifetime.
- Warm live validation, invalidation, one rediscovery fallback, and visible recovery failure across version search, manual, and scheduled checks.
- Same-model single-flight coordination and deterministic fixture-based validation.

### Excluded

- Caching firmware versions or serving cache content as a firmware result, because live source verification remains authoritative.
- Canon regions, product classes, or direct HTTP paths outside the existing Canon Asia English module flows.
- Changes to the central scraping policy or its default budgets, because this feature consumes that enforcement point.

### Edge Cases & Boundaries

- Freshness is decided at the linearized dispatch point after lease and pacing acquisition. A mapping exactly 24 hours old is expired; missing and expired mappings use full discovery.
- Cached-endpoint transport, status, parsing, model-identity, timeout, and cancellation failures invalidate before one recovery discovery. Recovery failure produces a visible failed check and preserves last-success state.
- Concurrent same-model callers share discovery, refresh, or the one warm live request through a SQLite-backed lease; distinct models retain shared Canon-origin pacing. A cancelled caller detaches; shared work stops only when no waiters remain.

## Technical Objectives

### Objective 1 - Persist Safe Discovery Metadata (Priority: P1)

Persist exact normalized model identity, catalogue family, endpoint URL, discovery time, validation metadata, and a SQLite-backed refresh lease without firmware versions.

**Why this priority**: Durable, safe metadata is required before any warm verification can be correct across restarts.

**Rationale**: The cache must survive restart within the SQLite migration contract.

**Deliverables**:
- Forward-only idempotent migration and cache repository.
- Mapping freshness and invalidation lifecycle contract.

**Validation Criteria**:
1. **Given** an empty database, **When** migrations run, **Then** the cache schema applies once and preserves existing migration safety behavior.
2. **Given** a stored mapping and a reopened database, **When** it is read before 24 hours, **Then** its discovery metadata is available without a stored firmware version.

### Objective 2 - Validate Through the Canonical Client (Priority: P1)

Use a fresh mapping for one centralized live request while retaining robots, retries, deadlines, cancellation, and Canon pacing.

**Why this priority**: A fast path that bypasses centralized enforcement or returns stale data would violate core correctness and politeness rules.

**Rationale**: Live parsing remains authoritative; the cache only avoids rediscovery.

**Deliverables**:
- Cache-aware Canon module integration for camera and lens flows.
- Entry-point coverage for version search, manual checks, and scheduled checks.

**Validation Criteria**:
1. **Given** a mapping younger than 24 hours, **When** each check entry point runs, **Then** it performs one paced centralized live request and returns a live-derived result.
2. **Given** injected virtual time, **When** a warm check acquires its shared Canon pacing slot, **Then** it completes in 0-30 seconds without bypassing robots or pacing.

### Objective 3 - Recover and Coordinate Deterministically (Priority: P2)

Coalesce same-model work, invalidate unsafe endpoints, retry full discovery once, and surface unrecoverable failure.

**Why this priority**: This protects correctness and source load after the essential durable warm path exists.

**Rationale**: Changed endpoints cannot yield stale success or multiply discovery traffic.

**Deliverables**:
- Same-model single-flight coordination with cancellation-safe cleanup.
- Captured-fixture, injected-clock integration tests for failure and concurrency matrices.

**Validation Criteria**:
1. **Given** concurrent same-model callers, **When** discovery or warm validation begins, **Then** they share one operation and receive its live result or visible failure.
2. **Given** a cached endpoint failure, **When** rediscovery also fails, **Then** the mapping is invalidated and no stale result is returned.

### Technical Constraints

- Use the existing SQLite volume, raw parameterized SQL, append-only migrations, and centralized host-provided HTTP client only.
- Freshness is strictly less than 24 hours; cached metadata never stores or supplies an authoritative firmware version.
- Retain Canon Asia English EOS R/RF/RF-S boundaries, shared 30-second pacing, bounded execution, and cancellation behavior.

## Integration Points

- **IP-001**: E002 migration runner and SQLite WAL access persist the cache and lease state.
- **IP-002**: E027 ScrapeClient remains mandatory for live requests and enforcement.
- **IP-003**: E028/E029 provide discovery and parsing; E012, E013, and E023 use the module runner.

## Requirements

### Technical Requirements

- **TR-001**: System MUST persist only the existing normalized Canon model identity plus catalogue family, firmware endpoint URL, discovery timestamp, invalidation timestamp/reason, optional last live-validation timestamp, and a SQLite-backed refresh lease using a forward-only idempotent migration.
- **TR-002**: System MUST decide freshness after lease and pacing acquisition, reuse a mapping only when then younger than 24 hours, and never persist or return a firmware version from cached metadata.
- **TR-003**: System MUST make exactly one mapped firmware-endpoint request through the centralized client for a fresh mapping in version search, manual, and scheduled paths; ScrapeClient-controlled robots refreshes remain separate.
- **TR-004**: System MUST bypass missing or expired mappings and perform the complete catalogue-to-product-to-firmware discovery flow.
- **TR-005**: System MUST invalidate after cached-endpoint transport, status, parsing, model-identity, timeout, or cancellation failure and attempt one full rediscovery fallback before surfacing failure.
- **TR-006**: System MUST coalesce same-model work through a SQLite-backed lease with owner token, expiry, heartbeat, compare-and-swap stale takeover, and fencing. Enrollment/decrement and close/cancel are atomic: post-close arrivals join one successor, and a cancelled waiter detaches while shared work stops only when no waiters remain.
- **TR-007**: System MUST preserve visible check failure and last-success state when fallback cannot produce a live result.
- **TR-008**: System MUST validate migration, restart, freshness at 0, 24h-epsilon, 24h, and 24h+epsilon, invalidation, fallback, entry points, lease takeover, concurrency, retry, timeout, and cancellation with fixtures, injected time, and no real sleeps or live requests.

### Key Entities

- **CanonFirmwareEndpointMapping**: Durable normalized model and catalogue-family discovery metadata for one endpoint, with discovery and validation state but no firmware version.
- **Refresh Lease**: SQLite-backed coordination state ensuring same-model callers share discovery, refresh, or warm validation.
- **Live Firmware Result**: The authoritative version parsed from the current centralized live endpoint response.

## Assumptions & Risks

### Assumptions

- Canon fixtures and paced HTTP test seams can be extended without live discovery.
- Check paths continue to invoke Canon modules through the module runner.

### Risks

- **Module execution model limits async coordination** *(likelihood: medium, impact: high)*: Integration must preserve runner behavior and cancellation.
- **Endpoint response drift** *(likelihood: medium, impact: high)*: Fixture coverage must prove invalidation and visible fallback failure rather than stale success.
- **Migration contention** *(likelihood: low, impact: medium)*: New schema writes must remain short and use the established migration/repository conventions.

## Implementation Signals

- `MIGRATION` - Add durable cache and lease metadata using the established append-only SQLite migration sequence.
- `NEW-ENTITY` - Introduce mapping and refresh-lease repository/domain contracts without firmware-result persistence.
- `NEW-WORKER` - Coordinate same-model live work without detached tasks after timeout or cancellation.
- `BREAKING-CHANGE` - Extend Canon module execution seams and check-path integration while retaining current public outcomes.

## Success Criteria

### Measurable Outcomes

- **SC-001** [OBJ1]: A mapping survives restart and deterministic tests prove reuse at 0 and 24h-epsilon and rejection at 24h and 24h+epsilon.
- **SC-002** [OBJ2]: Each of version search, manual check, and scheduled check makes exactly one centralized live firmware request for a fresh mapping and completes in 0-30 seconds under injected virtual time.
- **SC-003** [OBJ3]: Deterministic fixtures prove same-model callers share one fenced lease operation, including takeover and cancellation races, and every cached-endpoint failure recovers once or visibly fails without stale data.

## Glossary

| Term | Definition |
|------|------------|
| Endpoint mapping | Cached source-discovered metadata linking one exact Canon model and catalogue family to its firmware action URL. |
| Warm verification | A live firmware check using a fresh endpoint mapping, without catalogue and product rediscovery. |
| Refresh lease | Coordination state that coalesces same-model discovery or live verification work. |

## Compliance Check

**Status**: PASS

TR-003/TR-006 preserve centralized robots and shared pacing. TR-001/TR-002 retain SQLite-only metadata, strict freshness, and no cached result. TR-005/TR-007 require visible recovery failure; TR-008 requires deterministic correctness validation. No violations found.

## Clarifications

### Session 2026-09-07

- Q: Does the 0-30 second warm bound include queueing? -> A: It applies after the shared pacing slot is acquired; queued work may exceed 30 seconds.
- Q: Is refresh coordination process-local or persisted? -> A: Use a SQLite-backed cross-process lease with owner identity, expiry, and stale-lease recovery.
- Q: Which failures invalidate a mapping? -> A: Cached-endpoint transport, status, parsing, model-identity, timeout, and cancellation failures invalidate it before recovery.
- Q: Does successful rediscovery need an extra validation request? -> A: Its live firmware response is authoritative; no extra validation request is made.
- Q: How does a cancelled waiter affect shared work? -> A: It detaches; shared work is cancelled only when no waiters remain, with cleanup guaranteed.
- Q: What is the cache key? -> A: Use the existing normalized canonical model ID plus catalogue family; do not introduce aliases.
- Q: What does one live request count? -> A: The mapped firmware endpoint request only; ScrapeClient robots refreshes are separate.
- Q: Which validation metadata persists? -> A: Discovery time, invalidation time/reason, and optional last successful live-validation time; the active lease is SQLite-backed.

## Stress-Test Findings

### Session 2026-09-07

STF-001: Boundary-Scale Stress (HIGH) — Affected: TR-002, TR-003, TR-004, SC-002 — Freshness is rechecked at dispatch; expiry transitions shared work to full discovery.

STF-002: Concurrent-Trigger Ambiguity (HIGH) — Affected: TR-006, TR-008, SC-003, OBJ3 — Lease ownership, expiry, takeover, and fencing are specified.

STF-003: Concurrent-Trigger Ambiguity (HIGH) — Affected: TR-006, TR-008, SC-003 — Enrollment and close/cancel linearization are specified.

STF-004: Boundary-Scale Stress (MEDIUM) — Affected: TR-002, TR-004, TR-008, SC-001 — Tests cover zero, pre-expiry, boundary, and post-expiry ages.
