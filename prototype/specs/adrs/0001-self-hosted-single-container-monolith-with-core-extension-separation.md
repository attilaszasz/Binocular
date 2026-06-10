---
adr_id: ADR-0001
status: accepted
date: 2026-05-31
tags: [architecture, deployment, monolith]
supersedes: []
superseded_by: ""
related_artifacts: [specs/prd.md#CAP-002, specs/prd.md#CAP-009]
---

# ADR-0001: Self-hosted single-container monolith with core/extension separation

## Status

Accepted.

## Context

Binocular is a self-hosted, single-user web application for homelab/prosumer users that must be low-maintenance, resource-efficient, and trivially deployable on a private LAN. Users expect a single container, one data volume to back up, zero-config startup, and "set-and-forget" reliability (PRD principles: data ownership, set-and-forget). The product must remain extensible by users without modifying core code (CAP-002), while keeping operational footprint minimal (CAP-009). A decision on overall architecture style and process/deployment topology is needed up front because it constrains every downstream component.

## Decision Drivers

- Minimal operational footprint for self-hosters (single container, single volume)
- Zero external infrastructure dependencies (no separate DB server, broker, or cache)
- User-extensibility without core code changes
- Resource efficiency on modest homelab hardware
- Simplicity of backup, upgrade, and restart

## Considered Options

### Option A: Single-container modular monolith

Core system (inventory, scheduling, alerting, API, static frontend) in one process; extension modules loaded dynamically.

- **Pros**: Minimal footprint, single port, single volume, trivial deploy/backup, easy concurrency for single user.
- **Cons**: No horizontal scaling, all concerns share one process lifecycle.

### Option B: Microservices / multi-container

Separate scheduler, scraper, API, frontend orchestrated via compose.

- **Pros**: Independent scaling and isolation.
- **Cons**: Massive operational overhead for a single-user tool, conflicts with "set-and-forget" and single-volume expectations, requires a broker/network between services.

### Option C: Serverless / managed cloud functions

- **Pros**: No server management.
- **Cons**: Violates self-hosted, data-ownership, offline-LAN, and no-cloud constraints entirely.

## Decision Outcome

Chosen option: **A: Single-container modular monolith** — it is the only option that satisfies the self-hosted, zero-infrastructure, single-volume, set-and-forget product constraints while still allowing a clean internal separation between the stable "Core System" (inventory, scheduler, alerting, API, UI) and pluggable "Intelligence" (extension modules). The monolith is internally modular (layered: API → services → repositories) so the extension boundary is explicit even though everything runs in one process.

## Consequences

### Positive

- Trivial deployment and backup; no inter-service networking; low resource use; single port exposure; aligns with all operability principles.
- Clear internal core/extension seam enables user extensibility without core changes.

### Negative

- No independent scaling or process isolation; a runaway extension shares the host process (mitigated by error boundaries and timeouts, addressed in a separate extension-engine ADR).

### Neutral

- All source organized as `backend/` (Python) + `frontend/` (React) within one image.

## Links

- [specs/prd.md](../prd.md) — CAP-002 (Extension Module Engine)
- [specs/prd.md](../prd.md) — CAP-009 (Self-Hosted Operability)
