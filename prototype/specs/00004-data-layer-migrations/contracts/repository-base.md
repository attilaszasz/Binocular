# Internal Contract: Repository Base

## Purpose

Define the internal Python data-access contract consumed by later domain repositories. This is not a public HTTP API.

## Surface

| Contract | Caller | Responsibility |
|----------|--------|----------------|
| `ConnectionManager.open()` | Lifespan, repositories | Return an `aiosqlite` connection with required pragmas applied. |
| `MigrationRunner.apply_pending()` | FastAPI lifespan | Validate and apply pending migrations before serving requests. |
| `Repository.execute()` | Domain repositories | Execute parameterized write SQL without leaking cursors. |
| `Repository.fetch_one()` | Domain repositories | Return one mapped row or `None`. |
| `Repository.fetch_all()` | Domain repositories | Return mapped rows as stable Python values. |

## Parameter Contract

| Input | Rule |
|-------|------|
| SQL values | Always passed through qmark or named parameters. |
| Identifiers | Must be static or selected from an allowlist. |
| Transactions | Migration runner owns migration transactions; repositories do not hide service-level transaction boundaries. |
| Errors | Database and validation failures propagate to the caller and are logged at the boundary. |

## Compatibility

- Future repositories for devices, modules, checks, activity logs, and settings use this base.
- No public OpenAPI route is introduced by this feature.
- No ORM session or model abstraction is introduced.
