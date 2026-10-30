# Research: Catalog Persistence and Write Ownership

## Migration integrity
- **Decision**: Append migration 0011 behind the fatal pre-migration SQLite backup gate; test empty/populated upgrades, failure rollback, and reopen.
- **Rationale**: Python sqlite3 executescript can implicitly commit an existing transaction. Migration schema/data/version must form one atomic script, not a BEGIN before executescript.
- **Avoid**: Editing shipped SQL, network calls, guessed catalog rows, raw-file WAL backups.
- **Sources**: [Python sqlite3](https://docs.python.org/3.13/library/sqlite3.html), [SQLite transactions](https://www.sqlite.org/lang_transaction.html).

## Write ownership
- **Decision**: Dedicated caller-owned write connections, short BEGIN IMMEDIATE, foreign_keys=ON, busy_timeout=5000, WAL; repositories within a unit of work never independently commit. Network remains outside transactions. Exceptions/cancellation before commit submission roll back; after submission, drain commit completion and establish the durable outcome before closing. Cancellation may coincide with a committed unit and must not be reported as rollback. Always close the connection.
- **Rationale**: aiosqlite serializes connection operations, not logical transaction ownership. Existing RepositoryBase commits each mutation on the lifespan connection.
- **Participants**: Device CRUD/check/confirmation/watermark; module upload/pause/delete; checks and scheduler; module/settings seeding; activity and notification repositories; Canon endpoint cache; backup/VACUUM path. SQL triggers/cascades remain transaction participants.
- **Avoid**: A competing application lock over the shared connection or compatibility paths that can commit another writer's work.
- **Sources**: [aiosqlite](https://aiosqlite.omnilib.dev/en/stable/), [SQLite WAL](https://www.sqlite.org/wal.html).

## Exact identity
- **Decision**: Stable UUID, unique module/source key/nonnullable canonical variant; preserve region/mount/hardware revision. Composite ownership constraints reject cross-module linkage. Aliases are searchable metadata, never sufficient identity proof.
- **Rationale**: SQLite nullable UNIQUE keys permit duplicates. Legacy rows stay explicit until one exact verified variant matches; migration cannot verify a source offline.
- **Avoid**: Name-only matching, implicit region merging, invented per-channel delivered history.
- **Sources**: [SQLite constraints](https://www.sqlite.org/lang_createtable.html), [SQLite foreign keys](https://www.sqlite.org/foreignkeys.html).

## Durable work
- **Decision**: Persist generations/revisions, finite budgets, bounded cursors, claim tokens and fenced conditional transitions; unique device/canonical-version/channel intents. Commit observations/device revisions with reevaluation work atomically. Keep workers dormant until later epics.
- **Rationale**: Process-memory admission cannot recover after restart. Lease expiry alone cannot authorize another sender while a prior send may be running; interrupted sends require uncertain state, not automatic replay.
- **Avoid**: Enabling unfinished refresh/fan-out/delivery behavior or external exactly-once claims.
- **Sources**: [SQLite transactions](https://www.sqlite.org/lang_transaction.html), [ADR-0017](../adrs/0017-shared-model-refresh-with-transactional-comparison-and-notification-delivery.md).

## Validation baseline
- **Decision**: Reuse pytest/pytest-asyncio/coverage, Ruff, mypy strict, pip-audit and existing frontend/CI tooling; file-backed interleaving, rollback, restart, variant and preserved-history tests. Runtime/tool availability must be checked by execution phases.
- **Sources**: [Project policy](../../project-instructions.md), [Technical context](../sad.md).
