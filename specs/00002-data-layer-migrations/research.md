## Research Report

**Context**: Best practices for SQLite data layer with aiosqlite, numbered migration runner, pre-migration backup, and repository base pattern for a self-hosted Python/FastAPI application.

## aiosqlite Connection Management

- **Key findings**: WAL mode enables concurrent reads with a single writer. Set via `PRAGMA journal_mode=WAL` at connection init. Use `PRAGMA foreign_keys=ON` and `PRAGMA busy_timeout=5000` for safety. aiosqlite wraps sqlite3 in a background thread — one long-lived connection is preferred over pool for single-user apps.
- **Recommended**: Single connection managed by app lifespan; WAL + foreign_keys + busy_timeout pragmas set on every connect. Store connection in app state for dependency injection.
- **Avoid**: Opening/closing connections per request. Running without busy_timeout (causes immediate lock errors under concurrent access).
### Sources
- https://aiosqlite.omnilib.dev — aiosqlite API reference and usage patterns
- https://www.sqlite.org/wal.html — SQLite WAL mode documentation

## Numbered Migration Runner

- **Key findings**: SQLite's `PRAGMA user_version` provides a persistent integer for schema version tracking without extra tables. Migrations stored as numbered SQL files (e.g., `0001_init.sql`). Forward-only: compare file number > user_version, apply in order, update pragma after each. Wrap each migration in a transaction.
- **Recommended**: Use `PRAGMA user_version` for tracking. Name files `NNNN_description.sql`. Apply atomically with rollback on failure. Log each applied migration.
- **Avoid**: Using a schema_version table (unnecessary overhead for SQLite). Allowing out-of-order or skipped migrations. Using executescript without transaction boundaries.
### Sources
- https://www.sqlite.org/pragma.html#pragma_user_version — SQLite pragma reference
- https://eskerda.com/sqlite-migrations/ — Lightweight migration patterns

## Pre-Migration Backup

- **Key findings**: `VACUUM INTO` creates a consistent, compact backup of the database while the source remains operational. Available since SQLite 3.27.0. Safe to run with WAL mode active. Alternative: file copy, but requires ensuring no active writers.
- **Recommended**: `VACUUM INTO '/path/to/backup'` before applying pending migrations. Only when pending migrations exist (skip if already current). Store backup alongside data dir with timestamp.
- **Avoid**: File-level copy without ensuring write quiescence. Backing up on every startup when no migrations are pending.
### Sources
- https://www.sqlite.org/lang_vacuum.html — VACUUM INTO documentation
- https://www.sqlite.org/backup.html — Online backup alternatives

## Repository Base Pattern

- **Key findings**: Raw SQL with parameterized queries is the project's chosen approach (no ORM). A base class providing execute/fetch helpers with connection access simplifies repositories. Use `aiosqlite.Row` row factory for dict-like access.
- **Recommended**: Base class accepting a connection, providing `execute`, `fetch_one`, `fetch_all` async helpers. Use `?` parameter placeholders. Enable `row_factory = aiosqlite.Row` for named column access.
- **Avoid**: String interpolation in SQL queries. Returning raw tuples without column names.
### Sources
- https://docs.python.org/3/library/sqlite3.html — sqlite3 row factory and parameterized queries
- https://aiosqlite.omnilib.dev — aiosqlite Row support

### Summary
Use a single aiosqlite connection managed in the FastAPI lifespan with WAL, foreign_keys, and busy_timeout pragmas. Track schema version via `PRAGMA user_version` with numbered SQL migration files applied forward-only at startup. Run `VACUUM INTO` before pending migrations. Provide a repository base class with parameterized query helpers and Row factory for named column access.

### Sources Index
| URL | Topic | Fetched |
|-----|-------|---------|
| https://aiosqlite.omnilib.dev | aiosqlite connection | 2026-06-10 |
| https://www.sqlite.org/wal.html | WAL mode | 2026-06-10 |
| https://www.sqlite.org/pragma.html#pragma_user_version | migration tracking | 2026-06-10 |
| https://eskerda.com/sqlite-migrations/ | migration patterns | 2026-06-10 |
| https://www.sqlite.org/lang_vacuum.html | backup | 2026-06-10 |
| https://docs.python.org/3/library/sqlite3.html | repository base | 2026-06-10 |
