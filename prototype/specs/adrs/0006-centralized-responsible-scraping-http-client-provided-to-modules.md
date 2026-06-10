---
adr_id: ADR-0006
status: accepted
date: 2026-05-31
tags: [scraping, http, reliability, governance]
supersedes: []
superseded_by: ""
related_artifacts: [specs/prd.md#CAP-008]
---

# ADR-0006: Centralized responsible-scraping HTTP client provided to modules

## Status

Accepted.

## Context

Binocular fetches third-party manufacturer firmware pages. Responsible/polite scraping (robots.txt respect, identifiable User-Agent, per-domain rate limiting, exponential backoff on 429/5xx) is both a product principle and an operational necessity — aggressive scraping gets IPs banned and harms the project's reputation (CAP-008). Because scraping is performed inside user-authored extension modules, there must be a way to guarantee polite behavior regardless of what a given module author writes. A decision is needed on where scraping-policy enforcement lives.

## Decision Drivers

- Guarantee polite-scraping compliance independent of module author behavior
- Single, auditable enforcement point (robots.txt, User-Agent, rate limit, backoff)
- Identifiable User-Agent (tool name + info URL), not a spoofed browser string
- Reasonable timeouts and redirect handling for resilience
- Reusability by standalone tooling (a module dev/test kit)

## Considered Options

### Option A: Host-provided pre-configured HTTP client injected into modules

Host provides a pre-configured `httpx.Client` (via a `create_http_client()` factory) to every module through the contract's `http_client` parameter; the client centrally enforces User-Agent, timeouts, follow-redirects, robots.txt respect, a 2-second per-domain delay, and exponential backoff. Modules MUST use this client and bring no HTTP logic of their own.

- **Pros**: Single enforcement point; guaranteed compliance; consistent behavior; reusable factory for the dev kit.
- **Cons**: Relies on the contract forbidding modules from importing their own HTTP libraries (a convention, not a hard lock given no sandbox).

### Option B: Document scraping rules and trust each module to implement them

- **Pros**: Zero host plumbing.
- **Cons**: Unenforceable; inconsistent; high risk of bans — unacceptable for a longevity-critical concern.

### Option C: Post-hoc enforcement via an egress proxy

A proxy intercepts all outbound traffic and applies scraping policy regardless of client used.

- **Pros**: Enforces regardless of client used.
- **Cons**: Heavy infrastructure; conflicts with single-container minimal footprint; robots.txt/rate-limit semantics awkward at the proxy layer.

## Decision Outcome

Chosen option: **Option A: a host-provided, pre-configured HTTP client passed into modules** — centralizing all scraping policy in one client the host injects through the module contract is the only practical way to make polite-scraping behavior a guarantee rather than a hope. The contract mandates that modules use the provided client; the same `create_http_client()` factory backs the standalone module dev/test kit so local testing exercises identical enforcement. This is the canonical enforcement model for the project's responsible-scraping principle.

## Consequences

### Positive

- robots.txt, identifiable User-Agent, per-domain rate limiting, and backoff are enforced uniformly for all modules; consistent, ban-resistant behavior; reusable for standalone tooling.

### Negative

- Enforcement is by convention (no sandbox prevents a determined module from importing its own HTTP library); acceptable under the trusted-operator model.

### Neutral

- Timeouts and redirect policy standardized at the client; scraping failures surface as visible "scrape failed" status rather than silent misses.

## Links

- [specs/prd.md](../prd.md) — CAP-008 (Responsible Scraping Enforcement)
- Related: unsandboxed extension module engine ADR ([ADR-0005](0005-unsandboxed-extension-module-engine-with-two-phase-validation.md)) — modules receive this client
- Related: trusted-LAN security model ADR
