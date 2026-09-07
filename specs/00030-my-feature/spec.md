---
feature_branch: "00030-my-feature"
created: "2026-09-06"
input: "E027"
spec_type: "technical"
spec_maturity: "clarified"
epic_id: "E027"
epic_sources: "{PRD:CAP-008}{SAD:ADR-0012}"
---

# Feature Specification: Source-Aware HTTP Pacing

## Problem Statement

Retries, redirects, robots, and concurrency bypass pacing; timed-out workers may continue traffic. Operators get unreliable outcomes, authors lack one safe boundary, and sources get excess traffic. Without enforcement, checks violate source policy and trust.

## Scope

### Included
- Pace attempts; bound credit/late traffic; prove compatibility.

### Excluded
- User configuration/persistence: zero-config runtime policy is sufficient.
- Extension signatures/source scrapers: existing contracts stay compatible.
- Unbounded accommodation: bounded execution must fail visibly.

### Edge Cases & Boundaries
- Invalid/short delay retains default; specific User-Agent precedes wildcard; equivalent origins share state.

## Technical Objectives

### Objective 1 - Enforce Source-Aware Pacing (Priority: P1)
**Why this priority**: Core responsible-scraping guarantee.
**Rationale**: One gate coordinates policy/concurrency.
**Deliverables**: Robots delay selection and shared origin pacing/cooldown.
**Validation Criteria**: **Given** policy, retries, redirects, and concurrency, **when** transport starts, **then** TR-001–TR-005 and TR-014 hold.

### Objective 2 - Bound Check Lifecycles (Priority: P1)
**Why this priority**: Post-timeout traffic violates policy.
**Rationale**: Workers can outlive callers.
**Deliverables**: Deadline, capped credit, scope invalidation, and cleanup.
**Validation Criteria**: **Given** delayed or cancelled work, **when** its scope ends, **then** TR-006–TR-009 and TR-021–TR-022 hold.

### Objective 3 - Prove Compatibility Deterministically (Priority: P1)
**Why this priority**: Evidence must be deterministic.
**Rationale**: Controlled events prove behavior.
**Deliverables**: Deterministic test/security evidence.
**Validation Criteria**: **Given** controlled time/transport, **when** tests repeat, **then** TR-010–TR-013 and TR-015–TR-029 pass identically.

### Technical Constraints
- Python 3.13/httpx; 1s default; 30s baseline; unchanged signature.
- Budget: `baseline + min(300s, Σ excess_i)` for own delay, not contention.
- One deadline; active scope; existing gates; no migration/UI/service/config.

## Integration Points
- **IP-001**: E005 boundary.
- **IP-002**: E007 owns flow.
- **IP-003**: E012/E013/E023 share pacing, not deadlines.

## Requirements

### Technical Requirements
- **TR-001**: System MUST canonicalize scheme, IDNA/trailing-dot/IPv6 host, and effective port; reject malformed hosts; distinguish scheme/non-default port; reuse the key for pacing/credentials.
- **TR-002**: System MUST keep one policy/fetch per origin/root User-Agent; allow/403 TTL 24h, transient deny 5m, restart clears. Waiters collectively own fetch; deadlines detach, initiator has no privilege, and arrival/final-cancel linearize. The 1,024-state LRU preserves cooldowns or fails closed.
- **TR-003**: System MUST use `max(1s, applicable Crawl-delay)`.
- **TR-004**: System MUST reserve by stable arrival, move pending eligibility later for longer policy without reorder, cap origins at 100 pending/4 active, and fail overflow.
- **TR-005**: System MUST allow four exponentially-backed-off attempts; valid seconds/future-date `Retry-After` joins pacing by latest eligibility; invalid/negative is absent, past date zero.
- **TR-006**: System MUST apply one absolute deadline across all request phases.
- **TR-007**: System MUST credit only own reservations before authorization, exclude contention/cancellation, cap by formula, and roll back pre-start cancellation.
- **TR-008**: System MUST linearize invalidation/start with expiry winning; block starts, cancel/close, then at 5s force-close and registry-own non-network survivors.
- **TR-009**: System MUST propagate cancellation after cleanup, own all work, reject survivor sends, and may retain cooldown.
- **TR-010**: System MUST deny robots 403/5xx/fetch failure and allow other 4xx.
- **TR-011**: System MUST preserve User-Agent, typed failures, four attempts, signature, isolation, and no direct module HTTP.
- **TR-012**: System MUST test every quantified policy/concurrency/retry/expiry/survivor boundary without real sleep/live HTTP.
- **TR-013**: System MUST record outcome/last-success; changed/unparseable sources visibly fail, never disappear.
- **TR-014**: System MUST enforce redirect target policy, strip cross-origin credentials, preserve GET, detect loops, and cap at 10.
- **TR-015**: System MUST pass layout, Ruff, strict mypy, 80% coverage, and static/security gates.
- **TR-016**: System MUST control test time, cancellable sleep, jitter, transport, and barriers; virtual time yields fairly.
- **TR-017**: System MUST trace sequence, IDs, times, budget, lifecycle, outcome, and counts; three fresh runs match.
- **TR-018**: System MUST test rejection of each phase's eligibility/start at or beyond deadline.
- **TR-019**: System MUST test origin sharing, arrival, contention, scopes, policy updates, waiter exits, and start/invalidation races.
- **TR-020**: System MUST test limit boundaries and `Retry-After` forms; no fifth attempt/eleventh redirect.
- **TR-021**: System MUST test all terminal states and cancellation while queued, authorized, active, cleaning, and surviving, including release/rejection.
- **TR-022**: System MUST keep per origin one policy/fetch, <=100 pending, <=4 active, releasing terminal references except cooldown and tracing counts.
- **TR-023**: System MUST bar official extensions from alternate clients, sockets/APIs, and network subprocesses; host-client calls require active scope or fail pre-network. Malicious unsandboxed code is not contained.
- **TR-024**: System MUST document user-vetted extensions as unsandboxed, in-process, with full application privileges; no malicious-path containment; trusted-LAN/single-user only.
- **TR-025**: System MUST process redirects: canonicalize; validate scheme/no downgrade; compare origins; retain same-origin credentials or strip/never regenerate; resolve robots; reserve pacing; start. Retries inherit sanitation.
- **TR-026**: System MUST deny robots 403 for 24h; deny 5xx, network/TLS/timeout, malformed/empty/partial/>512KiB for 5m; cache no cancellation; allow other 4xx 24h.
- **TR-027**: System MUST re-reserve/enforce all rules for same-origin robots redirects and reject cross-origin before target start without recursion.
- **TR-028**: System MUST force-close at 5s; logical scope fails while registry owns non-network survivors to settlement; no kernel-I/O containment claim.
- **TR-029**: System MUST trace host attempts, policy/pacing/start, redirect/credentials, denial, TTL/outcome, retry/cleanup, plus static proof modules use no alternate path.

## Assumptions & Risks
### Assumptions
- One root client/User-Agent exists; official extensions cooperate.

### Risks
- **Surviving traffic** *(likelihood: high, impact: high)*: Reject expired sends.
- **Origin races** *(likelihood: medium, impact: high)*: Prove one schedule.
- **Budget inflation** *(likelihood: medium, impact: medium)*: Prove capped credit.

## Implementation Signals
- `NEW-ENTITY` — Ephemeral origin and check state.

## Success Criteria
### Measurable Outcomes
- **SC-001** [OBJ1]: Same-origin starts are spaced; distinct origins remain independent.
- **SC-002** [OBJ1]: 100% of origin, TR-026 robots, four-attempt, ten-redirect, and stated-limit cases pass.
- **SC-003** [OBJ2]: Default checks retain baseline; delay credit matches TR-007 within 300s.
- **SC-004** [OBJ2]: Expiry ends network authority, leaves no unowned work, rejects survivor sends, and propagates cancellation.
- **SC-005** [OBJ3]: Existing regressions pass 100%; docs assert unchanged signatures and unsandboxed trust.
- **SC-006** [OBJ3]: Three no-live-HTTP/no-real-sleep runs record identical events/budgets.
- **SC-007** [OBJ3]: Source layout, Ruff, `mypy --strict`, 80% coverage, static-analysis, and security gates pass.
- **SC-008** [OBJ3]: Tests show retention, zero leakage, and all unscoped host-client calls rejected; static checks find zero alternate paths in official modules.

## Glossary
| Term | Definition |
|------|------------|
| Effective delay | Max default/source delay. |
| Normalized origin | Canonical scheme/host/port. |
| Check scope | Request authority. |
| Cross-origin | Different normalized origin. |
| Credentials | URL userinfo; auth/proxy/cookie/API-key/token headers; cookie jar; HTTP, certificate, and proxy auth. |
| Own reservation | Reservation whose `scope_id` is the current check scope. |
| Prospective credit | Credit computed atomically before authorization. |
| Terminal state | Completed, failed, expired, cancelled, or cleanup-failed. |

## Stress-Test Findings
- STF-001: Concurrent-Trigger Ambiguity (HIGH) — Affected: TR-002, TR-006, TR-008, TR-009, SC-004 — RESOLVED: collective ownership.
- STF-002: Constraint Impossibility (HIGH) — Affected: TR-005, TR-006, TR-007, SC-003 — RESOLVED: prospective credit.
- STF-003: Concurrent-Trigger Ambiguity (HIGH) — Affected: TR-006, TR-008, TR-009, SC-004 — RESOLVED: expiry/start linearization.
- STF-004: Boundary-Scale Stress (MEDIUM) — Affected: TR-002, TR-003, TR-005, TR-007, TR-012, TR-014, SC-002, SC-003 — RESOLVED: tests.
- STF-005: Boundary-Scale Stress (MEDIUM) — Affected: TR-002, TR-004, TR-012, SC-001 — RESOLVED: fail-closed cap.
- STF-006: Cross-Requirement Contradiction (CRITICAL) — Affected: TR-023, TR-024, SC-008 — RESOLVED: cooperative paths only.
- STF-007: Boundary-Scale Stress (HIGH) — Affected: TR-001, TR-014, TR-025, SC-001, SC-008 — RESOLVED: canonicalization.
- STF-008: Concurrent-Trigger Ambiguity (HIGH) — Affected: TR-008, TR-009, TR-028, SC-004 — RESOLVED: close vs settlement.
