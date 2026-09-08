# Data Model: Canon Endpoint Discovery Cache

> Feature: E031 | Storage: existing SQLite `binocular.db` | Migration: next append-only numbered SQL file

## Entities

| Entity | Purpose | Key | Lifetime |
|--------|---------|-----|----------|
| `CanonFirmwareEndpointMapping` | Durable discovered firmware action metadata; never a firmware result | `(catalogue_family, model_key)` | Valid only when `now - discovered_at < 24h` and not invalidated |
| `CanonRefreshLease` | Cross-process single-flight ownership and waiter coordination | `(catalogue_family, model_key)` | Active only until owner closes, all waiters detach, or lease expires |
| `LiveFirmwareResult` | Parsed result from the current centralized request | in-memory shared operation result | Never persisted by this feature |

## CanonFirmwareEndpointMapping

| Column | SQLite Type | Null | Rules |
|--------|-------------|------|-------|
| `catalogue_family` | TEXT | no | Canon allowlist: EOS R camera or RF/RF-S lens family; part of primary key |
| `model_key` | TEXT | no | Existing normalized exact model identity; part of primary key; no aliases |
| `endpoint_url` | TEXT | no | Absolute Canon Asia English firmware action URL discovered from the product page |
| `discovered_at` | INTEGER | no | UTC epoch milliseconds; cache is fresh only below 24 hours at dispatch |
| `last_validated_at` | INTEGER | yes | UTC epoch milliseconds of a successful mapped live parse |
| `invalidated_at` | INTEGER | yes | UTC epoch milliseconds; non-null makes mapping unusable |
| `invalidation_reason` | TEXT | yes | Cached-endpoint failure category, including transport, status, parse, identity, timeout, or cancellation |

| Constraint / Index | Rule |
|--------------------|------|
| `PRIMARY KEY (catalogue_family, model_key)` | One mapping per exact Canon family/model identity |
| URL validation in repository/domain boundary | Reject non-HTTPS, non-Canon Asia English endpoints before persistence |
| validation-state check | `invalidated_at IS NULL` implies `invalidation_reason IS NULL`; an invalidated row is never warm-reused |
| `idx_canon_endpoint_mapping_freshness` | `(catalogue_family, model_key, discovered_at)` supports keyed freshness reads |

## CanonRefreshLease

| Column | SQLite Type | Null | Rules |
|--------|-------------|------|-------|
| `catalogue_family` | TEXT | no | Same canonical key component as mapping |
| `model_key` | TEXT | no | Same canonical key component as mapping |
| `owner_token` | TEXT | no | Random operation identity; compare-and-swap owner proof |
| `fencing_token` | INTEGER | no | Monotonic generation; every owner-dependent mutation includes it |
| `expires_at` | INTEGER | no | UTC epoch milliseconds; stale owner may be taken over atomically |
| `heartbeat_at` | INTEGER | no | UTC epoch milliseconds; owner renewal evidence |
| `waiter_count` | INTEGER | no | Non-negative enrolled caller count; shared work ends only at zero |
| `state` | TEXT | no | `open` or `closing`; closed arrivals cannot attach to a finishing operation |

| Constraint / Index | Rule |
|--------------------|------|
| `PRIMARY KEY (catalogue_family, model_key)` | Exactly one current coordination row per cache key |
| `CHECK (waiter_count >= 0)` | Prevents underflow during cancellation/decrement |
| owner mutation predicate | `owner_token`, `fencing_token`, `state = 'open'`, and unexpired lease must match |
| takeover transaction | Atomically compares expiry, increments fencing token, replaces owner, and enrolls the taker |

## Relationships and Lifecycle

| From | To | Relationship | Rule |
|------|----|--------------|------|
| Mapping | RefreshLease | Same composite identity | No foreign key; lease is transient coordination state and may exist without a mapping |
| RefreshLease | LiveFirmwareResult | One shared operation | Waiters receive only the current live result or the same visible failure |

| Transition | Trigger | Result |
|------------|---------|--------|
| Missing / expired / invalidated → discovery | No fresh usable mapping after lease and pacing acquisition | Full catalogue → product → firmware flow; persist metadata only after live success |
| Fresh → warm validation | Fresh usable mapping | One mapped request through `ScrapeClient`; update `last_validated_at` after parse and identity validation |
| Fresh → invalidated | Cached-endpoint transport, status, parse, identity, timeout, or cancellation failure | Timestamp/reason set before one rediscovery fallback |
| Fresh → retained | Policy failure before the cached endpoint request | Mapping remains; no stale result is returned |
| Open lease → closing / successor | Owner completes, final waiter detaches, or owner becomes stale | Cleanup and successor enrollment are atomic; post-close arrivals join the successor only |

## Repository Contracts

| Contract | Inputs | Atomicity / Output |
|----------|--------|--------------------|
| `get_mapping` | family, model key | Returns mapping and freshness state; does not return a firmware version |
| `upsert_discovery` | validated mapping metadata | Replaces only the mapping metadata after successful full discovery |
| `record_live_validation` | key, timestamp | Updates successful validation timestamp only |
| `invalidate_mapping` | key, timestamp, definitive reason | Conditional update before recovery discovery |
| `acquire_or_join_lease` | key, owner token, now, TTL | Transactionally enrolls under open owner or fences and takes over stale/closing work |
| `heartbeat_lease` | key, owner token, fencing token, expiry | Compare-and-swap renewal; stale owners cannot extend newer leases |
| `detach_waiter` / `close_lease` | key, owner proof or waiter identity | Transactionally decrements; cancels shared work only when count reaches zero; removes/rotates closed state |

## Migration and Invariants

- Use one forward-only idempotent migration after `0008`; never alter prior migrations.
- Use raw parameterized SQL, existing WAL/busy-timeout connection policy, and short write transactions; never hold a transaction across pacing or network I/O.
- Persist no firmware version, release date, or download URL as a cache result.
- Reopen the same file-backed SQLite database to prove migration idempotence and mapping durability.
- Recheck freshness at the linearized dispatch point after lease and centralized pacing acquisition; exactly 24 hours is expired.
