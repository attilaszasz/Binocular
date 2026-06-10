# Research: Responsible Scraping Client
> E007 | 2026-05-31 | Inform plan decisions for polite HTTP access

## HTTP Client
- **Decision**: Use `httpx.AsyncClient` behind a host-owned wrapper.
- **Rationale**: It matches the async FastAPI backend and supports deterministic `MockTransport` tests.
- **Rejected**: `requests` and `urllib` because they either block async flows or lack ergonomic async test transports.
- **Pitfalls**: Do not let modules construct raw clients that bypass policy.
- **Sources**: https://www.python-httpx.org/, specs/sad.md ADR-0006

## Robots Policy
- **Decision**: Fetch robots.txt per origin, parse locally, and cache policy decisions in memory.
- **Rationale**: RFC 9309 compliance must be enforced before target requests without adding persistent schema in this epic.
- **Rejected**: Persisted robots tables because cache state is operational, not product data.
- **Pitfalls**: Missing robots.txt should not crash checks; explicit disallow must fail closed.
- **Sources**: https://www.rfc-editor.org/rfc/rfc9309, specs/prd.md CAP-008

## Rate Limit and Retry
- **Decision**: Apply per-origin pacing plus bounded backoff for 429 and transient 5xx responses.
- **Rationale**: Manufacturer sites are independent and should not share a global throttle.
- **Rejected**: Global limiter because one slow or throttled site would block unrelated vendors.
- **Pitfalls**: Avoid real sleeps in tests by injecting clock/sleeper hooks.
- **Sources**: https://developer.mozilla.org/docs/Web/HTTP/Headers/Retry-After, https://www.python-httpx.org/advanced/transports/

## Summary

| Topic | Decision | Rationale |
|-------|----------|-----------|
| HTTP Client | `httpx.AsyncClient` wrapper | Async backend and fake transports. |
| Robots Policy | In-memory per-origin cache | Enforce policy without new persistence. |
| Rate Limit and Retry | Per-origin bounded policy | Polite to each vendor independently. |

## Sources Index

| URL | Topic | Fetched |
|-----|-------|---------|
| https://www.python-httpx.org/ | HTTP Client | 2026-05-31 |
| https://www.rfc-editor.org/rfc/rfc9309 | Robots Policy | 2026-05-31 |
| https://developer.mozilla.org/docs/Web/HTTP/Headers/Retry-After | Rate Limit and Retry | 2026-05-31 |
| https://www.python-httpx.org/advanced/transports/ | Rate Limit and Retry | 2026-05-31 |
