# Research: Data Layer & Migrations
> Feature | 2026-05-31 | SQLite migration and repository planning

## Migration Runner
- **Decision**: Use a dedicated startup migration connection and apply pending numbered SQL files in ascending order.
- **Rationale**: `aiosqlite` serializes work per connection and SQLite allows one writer, so startup is the safest migration window.
- **Rejected**: Concurrent or request-time migrations; they add lock contention and failure ambiguity.
- **Pitfalls**: Avoid implicit transactions, nested `BEGIN`, and serving requests before migrations finish.
- **Sources**: https://aiosqlite.omnilib.dev/en/stable/, https://www.sqlite.org/lang_transaction.html

## Connection Pragmas
- **Decision**: Apply `foreign_keys=ON`, bounded `busy_timeout`, and WAL initialization before application transactions.
- **Rationale**: These pragmas are connection-scoped or persistent behaviors that must be set deliberately.
- **Rejected**: Depending on SQLite defaults or changing foreign-key behavior inside a transaction.
- **Pitfalls**: WAL still allows only one writer and should not be treated as multi-writer coordination.
- **Sources**: https://www.sqlite.org/pragma.html, https://www.sqlite.org/wal.html

## Pre-Migration Backup
- **Decision**: Create a timestamped SQLite backup snapshot before applying pending migrations.
- **Rationale**: SQLite backup semantics produce a consistent snapshot and avoid WAL file-copy hazards.
- **Rejected**: Copying only `binocular.db` while WAL may contain committed data.
- **Pitfalls**: Backup failure must be fatal; otherwise migrations could damage the only durable state.
- **Sources**: https://www.sqlite.org/backup.html, https://docs.python.org/3/library/sqlite3.html

## Repository Base
- **Decision**: Provide repository helpers that bind SQL values through DB-API parameters and return mapped rows.
- **Rationale**: Parameter binding is the primary SQL injection defense and keeps raw SQL explicit without an ORM.
- **Rejected**: f-string SQL for values, user-controlled identifiers, and cursors escaping connection lifetime.
- **Pitfalls**: Dynamic identifiers require allowlists; helper methods should not hide transaction boundaries.
- **Sources**: https://docs.python.org/3/library/sqlite3.html, https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html

## Summary
| Topic | Decision | Rationale |
|-------|----------|-----------|
| Migration Runner | Dedicated startup runner | Deterministic writer window before requests |
| Connection Pragmas | WAL, foreign keys, busy timeout | Reliable local SQLite behavior |
| Pre-Migration Backup | SQLite snapshot before pending migrations | Protects single durable state |
| Repository Base | Parameterized helpers | Raw SQL without injection-prone value formatting |

## Sources Index
| URL | Topic | Fetched |
|-----|-------|---------|
| https://aiosqlite.omnilib.dev/en/stable/ | Migration Runner | 2026-05-31 |
| https://www.sqlite.org/lang_transaction.html | Migration Runner | 2026-05-31 |
| https://www.sqlite.org/pragma.html | Connection Pragmas | 2026-05-31 |
| https://www.sqlite.org/wal.html | Connection Pragmas | 2026-05-31 |
| https://www.sqlite.org/backup.html | Pre-Migration Backup | 2026-05-31 |
| https://docs.python.org/3/library/sqlite3.html | Pre-Migration Backup; Repository Base | 2026-05-31 |
| https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html | Repository Base | 2026-05-31 |
