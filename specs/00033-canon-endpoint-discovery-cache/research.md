# Research

## SQLite Persistence and TTL

Persist only endpoint discovery metadata and commit it only after successful discovery. Treat a mapping as fresh when its age is strictly less than 24 hours; at the boundary it is expired. Do not hold a SQLite transaction across network I/O and never treat cached data as a firmware result. SQLite's single-writer model favors short writes and a durable, file-backed restart test. Sources: [SQLite isolation](https://www.sqlite.org/isolation.html), [SQLite transactions](https://www.sqlite.org/lang_transaction.html).

## Single-Flight and Recovery

Use one same-model operation for discovery, refresh, or warm validation, remove its coordination state in `finally`, and propagate its response or failure to waiters. A warm mapping still makes one centralized live endpoint request. Transport, HTTP-status, parsing, or identity failure invalidates the mapping before exactly one full rediscovery attempt; never cache failures or serve stale versions. Source: [asyncio synchronization primitives](https://docs.python.org/3/library/asyncio-sync.html).

## Deterministic Validation

Inject time and HTTP behavior. Use a temporary file-backed SQLite database for migration and restart coverage. Script fixture responses and coordinate callers with events to prove one shared operation, boundary expiry, invalidation, fallback, cancellation cleanup, and error propagation without wall-clock sleeps or live requests. Sources: [pytest-asyncio concepts](https://pytest-asyncio.readthedocs.io/en/stable/concepts.html), [pytest monkeypatch](https://docs.pytest.org/en/stable/how-to/monkeypatch.html).
