---
spec_type: technical
epic_id: E007
epic_sources: [PRD:CAP-008, SAD:ADR-0006]
spec_maturity: draft
---

# Feature Specification: Responsible Scraping Client

## Problem Statement

Binocular modules will fetch manufacturer firmware pages whose owners expect polite automated access. If each module creates its own HTTP client, robots.txt, User-Agent, rate limits, and retry behavior can drift or be bypassed, creating legal, reliability, and reputation risk. The core system needs one host-owned outbound path that modules can use without owning scraping policy.

## Scope

### Included

- Central async HTTP client wrapper for manufacturer page requests.
- Robots.txt fetching, caching, and allow/deny decisions per origin.
- Identifiable default User-Agent with configuration override.
- Per-domain rate limiting and retry/backoff for transient failures.
- Typed outcomes/errors that later module execution can record visibly.
- Deterministic tests using local fake transports, not live vendor calls.

### Excluded

- Module loader integration; E006 owns injecting the client into modules.
- Device checks and version comparison; E009 owns detection semantics.
- UI or operator controls for scraping settings; later product epics own UI.
- Full crawler behavior such as sitemap traversal; Binocular fetches explicit URLs.

### Edge Cases & Boundaries

- A disallowed robots rule must block the request with a visible typed error.
- Missing robots.txt may allow requests using conservative defaults.
- Unreachable robots.txt, malformed policies, DNS failures, and timeouts must not crash the core process.
- Rate limiting is scoped by request origin so one slow domain does not block all others.
- Retry attempts must have bounded maximum attempts and bounded delay.

## Technical Objectives

### OBJ1 [P1] Centralize outbound HTTP policy

**Why this priority**: P1 because project instructions require all scraping through a centralized host client.

**Rationale**: A single wrapper around `httpx.AsyncClient` gives modules a stable interface while keeping policy enforcement inside the trusted core.

**Deliverables**: Scrape client module, typed request/result errors, settings for User-Agent, timeout, backoff, and rate-limit defaults.

**Validation Criteria**: Given a module-facing request, when the client performs it, then configured headers, timeout, and policy checks are applied before any response is returned.

### OBJ2 [P1] Enforce robots.txt decisions

**Why this priority**: P1 because robots.txt respect is a non-negotiable responsible-scraping requirement.

**Rationale**: Robots decisions must be automatic and testable so modules cannot silently ignore source-owner policy.

**Deliverables**: Robots policy resolver, per-origin policy cache, allow/deny checks using the configured User-Agent.

**Validation Criteria**: Given a disallowing robots.txt fixture, when a matching URL is requested, then the client blocks the request and returns a typed policy error.

### OBJ3 [P1] Apply per-domain pacing and backoff

**Why this priority**: P1 because conservative rate limiting and transient-failure backoff protect vendor sites and improve reliability.

**Rationale**: Manufacturer sites differ; throttling and retries must be origin-specific and deterministic under test.

**Deliverables**: Per-origin limiter, retry policy for 429 and 5xx, Retry-After handling where present.

**Validation Criteria**: Given repeated requests to the same origin, when requests exceed the configured pace or receive retryable status codes, then the client delays/retries according to bounded policy.

### OBJ4 [P2] Expose diagnostics for later activity logging

**Why this priority**: P2 because observability improves operator trust, but the P1 client can function without the final activity-log integration.

**Rationale**: Later epics need enough structured context to explain scrape failures without duplicating HTTP policy logic.

**Deliverables**: Structured metadata for status, attempt count, final URL, robots decision, and retry reason.

**Validation Criteria**: Given success, policy block, and retry exhaustion cases, when the client returns or raises, then callers can inspect structured diagnostic fields.

## Integration Points

- App settings provide scraping defaults without requiring configuration.
- Future module engine receives only this client interface for outbound HTTP.
- Structured logging records policy, retry, and failure events without response body leakage.
- No repository or migration is required for this feature; persistent activity logging is deferred.

## Requirements

TR-001: System MUST provide a single async scrape client interface for all manufacturer-page HTTP requests.
TR-002: System MUST send an identifiable User-Agent by default and allow environment override.
TR-003: System MUST honor robots.txt decisions for the configured User-Agent before fetching a target URL.
TR-004: System MUST cache robots.txt policies per origin to avoid refetching on every request.
TR-005: System MUST enforce per-origin rate limiting with conservative zero-config defaults.
TR-006: System MUST retry 429 and transient 5xx responses with bounded exponential backoff.
TR-007: System MUST honor Retry-After for retryable responses when present and valid.
TR-008: System MUST expose typed errors for robots denial, transport failure, timeout, and retry exhaustion.
TR-009: System MUST allow deterministic unit tests through injectable transports and clocks.
TR-010: System MUST NOT require live external network calls for validation.

## Assumptions & Risks

### Assumptions

- Manufacturer checks fetch explicit known URLs rather than crawling sites.
- Modules can accept an injected async client interface in a later epic.
- Conservative defaults are acceptable until operator-facing tuning exists.
- Python standard robots parsing is sufficient for the project’s initial allow/deny needs.

### Risks

- Robots parsing edge cases may differ from a vendor’s expectation (likelihood: medium, impact: medium).
- Overly conservative default pacing may slow bulk checks (likelihood: medium, impact: low).
- Retry behavior can hide repeated source instability if diagnostics are too thin (likelihood: low, impact: medium).

## Implementation Signals

- `NEW-ENTITY`: Scrape client, robots policy cache, retry policy, and rate limiter types.
- `NEW-CONFIG`: User-Agent, request timeout, rate-limit interval, retry attempts, and backoff settings.
- `EXTERNAL-SERVICE`: Manufacturer web pages accessed through `httpx`.
- `NEW-WORKER`: No background worker in this epic; async delays occur inside request execution only.
- `BREAKING-CHANGE`: None; no existing scraping API exists.

## Success Criteria

SC-001 [OBJ1]: All scrape requests made through the new interface include the configured User-Agent and timeout policy.
SC-002 [OBJ2]: A robots.txt disallow fixture prevents the target request and produces a typed robots-denied outcome.
SC-003 [OBJ3]: Same-origin requests and retryable responses follow bounded per-origin pacing/backoff in deterministic tests.
SC-004 [OBJ4]: Success and failure paths expose structured diagnostics covering status, attempts, origin, and policy outcome.
SC-005 [OBJ1]: Backend lint, strict typing, and tests pass without live network dependency.

## Glossary

| Term | Definition |
|------|------------|
| Scrape Client | Host-owned async HTTP interface modules must use for outbound manufacturer-page requests. |
| Origin | URL scheme, host, and port used as the unit for robots caching and rate limiting. |
| Robots Policy | Parsed robots.txt rules used to decide whether the configured User-Agent may fetch a URL. |
| Retry-After | HTTP response guidance indicating how long a client should wait before retrying. |

## Compliance Check

PASS — The spec preserves centralized polite scraping, zero-config operation, self-contained execution, no telemetry, and visible typed failures required by project instructions.
