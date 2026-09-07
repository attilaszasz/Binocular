# Research: Source-Aware HTTP Pacing
> E027 | 2026-09-06 | Technical decisions and validation

## Robots Policy Selection
- **Decision**: Treat applicable valid `Crawl-delay` as a non-standard hint and select the greater of it and the default.
- **Rationale**: RFC 9309 allows extensions; matching the request User-Agent preserves intent without weakening defaults.
- **Rejected**: Treating the field as mandatory RFC behavior or allowing shorter declarations to reduce pacing.
- **Pitfalls**: Preserve allow/disallow and specific-group precedence.
- **Sources**: https://www.rfc-editor.org/rfc/rfc9309#section-2.2, https://docs.python.org/3.13/library/urllib.robotparser.html

## Origin Pacing and Retries
- **Decision**: Atomically schedule every attempt by normalized scheme, lowercase host, and effective port; retries share the timeline.
- **Rationale**: Shared scheduling covers concurrency, robots, redirects, and retries while origins remain independent.
- **Rejected**: Raw netloc keys, per-check limiters, and one pacing acquisition outside the retry loop.
- **Pitfalls**: Avoid duplicate sleeps, lock-held I/O, hidden redirects, and task-local cooldowns.
- **Sources**: https://www.rfc-editor.org/rfc/rfc6454#section-4, https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3

## Deadlines and Cancellation
- **Decision**: Use a check-scoped absolute monotonic deadline whose unchanged baseline gains only capped credit for required pacing above the default; invalidation cancels active requests and rejects future attempts.
- **Rationale**: HTTPX timeouts omit queues/backoff and worker threads survive cancellation, requiring scope-bound authorization.
- **Rejected**: Resetting timeouts per attempt, shielding waits, or granting every check the maximum source-aware budget up front.
- **Pitfalls**: Swallowed cancellation, detached tasks, or unbounded credit permit late traffic or budget changes.
- **Sources**: https://docs.python.org/3.13/library/asyncio-task.html#timeouts, https://www.python-httpx.org/advanced/timeouts/

## Deterministic Validation
- **Decision**: Inject monotonic time, cancellable sleep, and jitter, and use scripted HTTPX transports plus synchronization barriers to record attempt order and timestamps.
- **Rationale**: Virtual timing makes concurrency, retries, deadline exhaustion, and zero-post-cancel assertions fast and repeatable.
- **Rejected**: Real sleeps, live sources, and wall-clock tolerance assertions.
- **Pitfalls**: Fake sleepers must yield control; tests must synchronize concurrent starts instead of assuming scheduler ordering.
- **Sources**: https://www.python-httpx.org/advanced/transports/#mock-transports, https://docs.python.org/3.13/library/asyncio-eventloop.html#asyncio.loop.time

## Summary
| Topic | Decision | Rationale |
|-------|----------|-----------|
| Robots | Maximum of default and valid applicable delay | Never weaken defaults |
| Pacing | Shared normalized-origin attempt timeline | Covers concurrency and retries |
| Deadlines | Baseline plus capped excess-delay credit | Accommodates sources without unbounded work |
| Tests | Injected time and scripted transport | Deterministic timing assertions |

## Sources Index
| URL | Topic | Fetched |
|-----|-------|---------|
| https://www.rfc-editor.org/rfc/rfc9309#section-2.2 | Robots | 2026-09-06 |
| https://docs.python.org/3.13/library/urllib.robotparser.html | Robots | 2026-09-06 |
| https://www.rfc-editor.org/rfc/rfc6454#section-4 | Origin | 2026-09-06 |
| https://www.rfc-editor.org/rfc/rfc9110.html#section-10.2.3 | Retry | 2026-09-06 |
| https://docs.python.org/3.13/library/asyncio-task.html#timeouts | Cancellation | 2026-09-06 |
| https://www.python-httpx.org/advanced/timeouts/ | Timeout | 2026-09-06 |
| https://www.python-httpx.org/advanced/transports/#mock-transports | Testing | 2026-09-06 |
| https://docs.python.org/3.13/library/asyncio-eventloop.html#asyncio.loop.time | Testing | 2026-09-06 |
