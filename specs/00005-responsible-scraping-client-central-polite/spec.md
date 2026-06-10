---
feature_branch: "00005-responsible-scraping-client-central-polite"
created: "2026-06-10"
input: "E005 Responsible Scraping Client — central polite httpx client with robots.txt, rate limiting, backoff"
spec_type: "technical"
spec_maturity: "draft"
epic_id: "E005"
epic_sources: "{SAD:ADR-0006}"
---

# Feature Specification: Responsible Scraping Client

**Feature Branch**: `00005-responsible-scraping-client-central-polite`  
**Created**: 2026-06-10  
**Status**: Draft  
**Spec Type**: technical  
**Spec Maturity**: draft  
**Epic ID**: E005  
**Epic Sources**: {SAD:ADR-0006}  
**Product Document**: specs/prd.md

## Problem Statement

Binocular has no mechanism to fetch third-party website content yet, which is the foundational capability needed for all update-checking modules. To maintain a polite and responsible internet posture, all outbound scraping requests must strictly respect robots.txt files, identify themselves using a custom User-Agent, pace themselves using per-origin rate limits, and apply backoff on server errors. Implementing these policies in a single centralized client guarantees compliance and prevents ad-hoc, aggressive scraping from extension modules.

## Scope

### Included

- Async HTTP client wrapping `httpx.AsyncClient` in `backend/src/binocular/scraping/client.py`.
- Custom, identifiable default User-Agent header containing the application name and repository link.
- Asynchronous robots.txt checker that caches rules per origin.
- Per-origin rate limiter pacing outbound requests (minimum interval between requests to the same origin).
- Exponential backoff with jitter on 429 and 5xx responses.
- Typed exception hierarchy for explicit scrape error diagnostics.
- Lifespan-managed client lifecycle to reuse connections across check jobs.

### Excluded

- Authentication against target scraping sites — out of scope.
- Proxies and IP rotation — unnecessary for prosumer/homelab use cases.
- Javascript rendering (e.g. Playwright/Puppeteer) — out of scope; only static HTML pages are fetched.
- Captcha solving — out of scope.

### Edge Cases & Boundaries

- Target origin does not have a robots.txt file: client must treat this as allowed (standard robots.txt protocol fallback).
- Robots.txt request fails with 4xx: client must assume fetching is allowed (except 403, which is treated as disallowed).
- Robots.txt request fails with 5xx or times out: client must assume disallowed to err on the side of safety.
- Concurrency limit reached for an origin: client blocks subsequent requests until the rate-limit window clears.
- Multi-threaded or multi-worker concurrency: sqlite or local memory locks are sufficient for single-process monolith.

## Technical Objectives

### Objective 1 - Centralized ScrapeClient Core & Lifespan (Priority: P1)

Define a centralized `ScrapeClient` wrapping `httpx.AsyncClient` that applies a custom User-Agent and integrates into the FastAPI lifespan.

**Why this priority**: Outbound scraping is a core feature — all module checking depends on this client.

**Rationale**: A single client instance managed by the FastAPI lifespan ensures connection pool reuse, resource cleanup on shutdown, and consistent User-Agent identification.

**Deliverables**:
- `backend/src/binocular/scraping/client.py` — `ScrapeClient` class.
- Lifespan integration in `backend/src/binocular/app.py`.
- Custom exceptions: `ScrapeError`, `RobotsDisallowedError`, `HTTPStatusError`, `ConnectError`.

**Validation Criteria**:
1. **Given** a `ScrapeClient` instance, **When** a request is sent, **Then** it contains the header `User-Agent: Binocular/0.1.0 (+https://github.com/attilaszasz/Binocular)`.
2. **Given** the application starts, **When** the lifespan runs, **Then** a shared `ScrapeClient` is registered in `app.state.scrape_client`.
3. **Given** the application shuts down, **When** the lifespan exits, **Then** the client is closed cleanly.

### Objective 2 - Robots.txt Enforcement (Priority: P1)

Implement an async check that fetches and caches robots.txt rules per origin and validates URLs before requesting.

**Why this priority**: Required for compliance with Principle II (Polite by Default).

**Rationale**: Checking robots.txt prevents scraping forbidden paths. Caching rules locally prevents redundant network requests for robots.txt on every page scrape.

**Deliverables**:
- Robots parser wrapper in `backend/src/binocular/scraping/robots.py`.
- Thread-safe, async-compatible rule cache inside `ScrapeClient`.

**Validation Criteria**:
1. **Given** a path disallowed by robots.txt, **When** the client attempts to fetch, **Then** a `RobotsDisallowedError` is raised without fetching the path.
2. **Given** multiple fetches to the same origin, **When** checked, **Then** the robots.txt file is fetched only once.
3. **Given** a missing robots.txt (404), **When** a path is fetched, **Then** the fetch succeeds.

### Objective 3 - Per-Origin Rate Limiting & Backoff (Priority: P1)

Pace requests per origin (scheme + host + port) and apply exponential backoff on rate-limited or server-error responses.

**Why this priority**: Required for compliance with Principle II (Polite by Default) to prevent overloading target sites.

**Rationale**: Scoped rate limits pace requests without choking requests to other hosts. Exponential backoff handles transient server errors gracefully.

**Deliverables**:
- Rate limiter in `backend/src/binocular/scraping/rate_limit.py`.
- Backoff wrapper/decorator.

**Validation Criteria**:
1. **Given** requests to the same origin, **When** executed sequentially, **Then** each request is delayed by at least 1.0 second (default).
2. **Given** target returns 429 or 5xx, **When** a request is sent, **Then** the client retries with backoff up to 3 times before raising `HTTPStatusError`.

## Technical Constraints

- Must use `httpx.AsyncClient` under the hood.
- Core package is `binocular.scraping`.
- Must pass `mypy --strict` and `ruff`.
- All requests must be asynchronous.

## Integration Points

- **IP-001**: E001 (App Skeleton) lifespan is modified to register and close the client.
- **IP-002**: Subsequent epics (E007 module engine, E010 detection) inject the client into module executions.

## Requirements

### Technical Requirements

- **TR-001**: System MUST provide `ScrapeClient` wrapping `httpx.AsyncClient`.
- **TR-002**: `ScrapeClient` MUST set the header `User-Agent: Binocular/0.1.0 (+https://github.com/attilaszasz/Binocular)` by default.
- **TR-003**: System MUST load robots.txt rules asynchronously using `httpx` and parse via `urllib.robotparser.RobotFileParser`.
- **TR-004**: System MUST cache robots.txt parsed rules in memory per origin.
- **TR-005**: `ScrapeClient` MUST check robots.txt before making any request, raising `RobotsDisallowedError` on failure.
- **TR-006**: System MUST enforce a minimum delay (default 1.0s) between requests to the same origin.
- **TR-007**: System MUST perform exponential backoff with jitter on HTTP 429 and 5xx responses (up to 3 retries).
- **TR-008**: System MUST raise custom typed exceptions for distinct failure reasons.
- **TR-009**: Client lifecycle MUST be integrated into FastAPI lifespan.

### Key Entities

- **ScrapeClient**: Async HTTP client that enforces politeness rules.
- **RobotsChecker**: Component that fetches, parses, and caches robots.txt rules.
- **RateLimiter**: Component that manages per-origin timestamps to enforce pacing.

## Assumptions & Risks

### Assumptions

- Targets support standard HTTP status codes (e.g. 429, 5xx) for rate limiting.
- The standard library `urllib.robotparser` matches standard robots.txt specs sufficiently.

### Risks

- **Target Site Changes Robots Rules** *(likelihood: low, impact: high)*: If a site updates robots.txt to disallow all user agents, Binocular will stop checking that site. This is correct behavior but might confuse users. Mitigation: error status in logs.
- **Backoff Event Loop Delays** *(likelihood: low, impact: low)*: Long backoff periods could tie up connection pools. Mitigation: cap max backoff to 30 seconds.

## Implementation Signals

- `NEW-ENTITY` — `ScrapeClient`, `RobotsChecker`, `RateLimiter`.
- `NEW-API` — Dependency injection provider for `ScrapeClient`.
- `NEW-CONFIG` — Rate limiting defaults in settings.

## Success Criteria

### Measurable Outcomes

- **SC-001** [OBJ1]: Outbound HTTP requests from `ScrapeClient` carry the custom User-Agent header.
- **SC-002** [OBJ2]: If robots.txt forbids `/private`, fetching it raises `RobotsDisallowedError`.
- **SC-003** [OBJ3]: Consecutive requests to a domain are spaced by at least 1.0 second.

## Glossary

| Term | Definition |
|------|------------|
| robots.txt | A text file published by web servers indicating which parts of the site can be visited by web crawlers. |
| Per-Origin pacing | Restricting request speed based on scheme, host, and port of the target URL to avoid overloading it. |
| Exponential backoff | An algorithm that increases the waiting time between retries exponentially after each failure. |
| Jitter | Random variation added to backoff delays to prevent synchronized retries from multiple sources. |

## Compliance Check

### Instructions Check Report
**Target**: spec.md
**Status**: PASS

| Principle | Verdict | Notes |
|-----------|---------|-------|
| I. Honest Failure | PASS | TR-008 requires custom typed exceptions |
| II. Polite by Default | PASS | TR-002, TR-005, TR-006, TR-007 enforce User-Agent, robots.txt, rate limits, backoff |
| III. Data Ownership | N/A | No database state changes in scraping client |
| IV. Least-Privilege | N/A | No host access changes |
| V. Type Safety | PASS | Mypy strict compliance required |
| VI. Set-and-Forget | PASS | Retries and backoff handle transient errors unattended |
| VII. Agent Output Style | N/A | Spec document |
