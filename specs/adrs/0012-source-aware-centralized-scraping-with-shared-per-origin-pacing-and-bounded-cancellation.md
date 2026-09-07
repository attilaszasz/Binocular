---
adr_id: ADR-0012
status: accepted
date: 2026-09-06
tags: [scraping, http, reliability, concurrency, cancellation, governance]
supersedes: [ADR-0006]
superseded_by: ""
related_artifacts: [specs/prd.md#CAP-008, specs/project-plan.md]
---

# ADR-0012: Source-aware centralized scraping with shared per-origin pacing and bounded cancellation

## Status

Accepted. Supersedes ADR-0006.

## Context

Binocular's accepted ADR-0006 centralizes robots.txt enforcement, an identifiable User-Agent, fixed per-domain delay, timeouts, and exponential backoff. The fixed model does not resolve source-specific `Crawl-delay` declarations, concurrent checks racing within one origin, retry attempts bypassing aggregate pacing, or work continuing after a caller timeout or cancellation.

Multi-request modules can legitimately need longer when a source declares a larger delay, but the system must remain zero-config and bounded, preserve existing budgets for unaffected origins, and surface failure rather than weaken source policy. `Crawl-delay` is an optional, non-standard robots extension rather than an RFC 9309 requirement.

## Decision Drivers

- Preserve centralized robots enforcement and identifiable User-Agent behavior.
- Honor valid source-declared delays conservatively without reducing the default.
- Enforce one origin-wide schedule across concurrent checks, robots retrieval, redirects, and every retry.
- Keep multi-request checks automatically viable but bounded under longer effective delays.
- Guarantee timeout or cancellation stops pending waits, retries, and background request issuance.
- Preserve existing pacing and execution budgets for origins without a longer valid declaration.
- Enable deterministic validation without live network calls or real sleeps.

## Considered Options

### Option A: Shared adaptive per-origin limiter with source-aware end-to-end budgets

Normalize scheme, host, and effective port into shared pacing state; atomically reserve each network attempt; use the greater of the conservative default and a valid applicable `Crawl-delay`; route retries through the same limiter and bounded deadline; derive any multi-request budget accommodation from the effective source delay with a finite cap; propagate cancellation; and inject a monotonic clock, sleeper, and scripted transport for tests.

- **Pros**: Enforces policy across concurrency and retries; requires no user configuration; is cancellation-safe; preserves unaffected behavior; supports deterministic tests.
- **Cons**: Adds client state and deadline accounting; a cancelled reservation may conservatively leave a harmless unused slot.

### Option B: Retain fixed per-origin delay and per-request timeout

Keep ADR-0006's fixed pacing and rely on existing request timeouts and backoff.

- **Pros**: Minimal complexity; unchanged behavior.
- **Cons**: Ignores source-declared delays; races under concurrency; a network-only timeout excludes queue and backoff waits; cannot guarantee no post-timeout work.

### Option C: Let modules or users configure source pacing and budgets

Expose delay and timeout configuration to each module or operator.

- **Pros**: Flexible source-specific tuning.
- **Cons**: Violates zero-config and centralized enforcement; is inconsistent and error-prone; lets module authors undercut policy.

## Decision Outcome

Chosen option: **Shared adaptive per-origin limiter with source-aware end-to-end budgets** — the host `ScrapeClient` uses shared normalized-origin pacing that selects the greater of the conservative default and a valid applicable robots.txt `Crawl-delay`, re-enters pacing for every retry, and runs all waits and attempts within source-aware, bounded, cancellation-safe check budgets without changing budgets for unaffected origins.

## Consequences

### Positive

- Valid applicable `Crawl-delay` values become conservative politeness hints; missing, invalid, or shorter values leave the default unchanged.
- Concurrent checks and every retry share one pacing and cooldown timeline per normalized origin; cross-origin work remains independent.
- Multi-request checks automatically receive only the bounded source-specific accommodation they need, while unaffected origins retain existing budgets.
- Timeout and cancellation cover robots lookup, queueing, pacing, backoff, redirects, and HTTP attempts and prevent subsequent request issuance.
- Injected monotonic timing and scripted transports support deterministic delay-selection, pacing, retry, concurrency, deadline, and cancellation tests.

### Negative

- `ScrapeClient` must coordinate shared origin state and end-to-end deadline accounting.
- Very long or unsupported declarations can cause a visible bounded failure instead of completion; they must never be silently shortened to issue requests sooner.

### Neutral

- `Crawl-delay` remains explicitly a non-standard extension; RFC 9309 robots allow/disallow enforcement remains unchanged.
- Cancellation may waste a previously reserved pacing slot but cannot permit an earlier request.

## Links

- [PRD capability CAP-008](../prd.md#CAP-008)
- [Project plan](../project-plan.md)
- [ADR-0006: Centralized responsible-scraping HTTP client provided to modules](0006-centralized-responsible-scraping-http-client-provided-to-modules.md)
- [RFC 9309, section 2.2.4](https://www.rfc-editor.org/rfc/rfc9309#section-2.2.4)
- [RFC 9110, section 10.2.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3)
- [Python 3.13 asyncio task cancellation](https://docs.python.org/3.13/library/asyncio-task.html#task-cancellation)
- [HTTPX timeouts](https://www.python-httpx.org/advanced/timeouts/)
- [HTTPX mock transports](https://www.python-httpx.org/advanced/transports/#mock-transports)
