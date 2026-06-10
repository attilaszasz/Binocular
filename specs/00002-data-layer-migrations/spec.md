---
feature_branch: "00002-data-layer-migrations"
created: "2026-06-10"
input: "E002 SQLite data layer with aiosqlite, numbered migration runner, pre-migration backup, repository base with raw SQL"
spec_type: "technical"
spec_maturity: "draft"
epic_id: "E002"
epic_sources: "{SAD:ADR-0004}{DOD:DDR-003}"
---

# Feature Specification: Data Layer & Migrations

**Feature Branch**: `00002-data-layer-migrations`
**Created**: 2026-06-10
**Status**: Draft
**Spec Type**: technical
**Spec Maturity**: draft
**Epic ID**: E002
**Epic Sources**: {SAD:ADR-0004}{DOD:DDR-003}
**Product Document**: specs/prd.md

## Problem Statement

Binocular currently has a running FastAPI application (E001) but no persistent storage. Every subsequent domain epic — device inventory (E006), module registry (E007), scheduled checks (E013), notifications (E014), activity logging (E015) — requires a database to store and retrieve state. Without a data layer, no business feature can be built or tested. The migration infrastructure must be in place from the start so schema changes across future epics are applied safely and automatically, with a pre-migration backup protecting against data loss during upgrades.

## Scope

### Included

- Async SQLite connection management via aiosqlite with WAL mode, foreign keys, and busy timeout pragmas
- Connection lifecycle integrated into the FastAPI app lifespan (E001 dependency)
- Numbered SQL migration runner tracking schema version via `PRAGMA user_version`
- Forward-only migration application at startup with per-migration transaction safety
- Pre-migration database backup via `VACUUM INTO` before applying pending migrations
- Repository base class with parameterized query helpers and `aiosqlite.Row` factory
- Seed migration (`0001_init.sql`) establishing the initial schema version
- `aiosqlite` added to `pyproject.toml` dependencies

### Excluded

- Domain-specific tables (devices, modules, checks) — deferred to E006, E007, E010+
- ORM or query builder — raw SQL per project constraints
- Database connection pooling — single-user app; one long-lived connection suffices
- Backup scheduling or restore API — deferred to E018
- Migration rollback/downgrade support — forward-only by design

### Edge Cases & Boundaries

- First startup: database file does not exist; must be created automatically with all migrations applied
- No pending migrations: startup must skip backup and migration phases cleanly
- Migration failure mid-sequence: transaction rollback must leave database at the last successfully applied version
- Corrupt or missing database file at `data_dir / binocular.db`: connection must fail with a clear error rather than silently creating a new empty database when a non-empty path was expected
- Concurrent startup attempts: busy_timeout pragma prevents immediate lock errors
- Database path directory does not exist: connection must create parent directories or fail clearly

## Technical Objectives

### Objective 1 - Async Database Connection Management (Priority: P1)

A single aiosqlite connection must be established during FastAPI lifespan startup, configured with WAL mode, foreign key enforcement, and busy timeout, and stored in application state for dependency injection into route handlers and services.

**Why this priority**: Every data-dependent epic requires a connection — this is the foundational prerequisite.

**Rationale**: aiosqlite wraps sqlite3 in a background thread, providing async-compatible access. WAL mode enables concurrent reads during background check operations. Foreign key enforcement prevents orphaned records across the entity graph. A single connection managed by lifespan avoids connection churn and ensures clean shutdown.

**Deliverables**:
- `backend/src/binocular/db/connection.py` — async connection open/close, pragma configuration, app state integration
- `backend/src/binocular/db/__init__.py` — package init

**Validation Criteria**:
1. **Given** the application starts, **When** the lifespan runs, **Then** an aiosqlite connection is established with `journal_mode=WAL`, `foreign_keys=ON`, and `busy_timeout=5000`
2. **Given** the application starts, **When** the database file does not exist, **Then** it is created at `{data_dir}/binocular.db`
3. **Given** the application is running, **When** a route handler requests the database connection, **Then** it receives the lifespan-managed connection instance
4. **Given** the application shuts down, **When** the lifespan exits, **Then** the connection is closed cleanly

### Objective 2 - Numbered Migration Runner (Priority: P1)

A forward-only migration runner must discover numbered SQL files in a migrations directory, compare their version numbers against `PRAGMA user_version`, and apply pending migrations in order within individual transactions, updating the schema version after each successful migration.

**Why this priority**: Without migrations, no epic can define its schema — blocks E006, E007, and all domain epics.

**Rationale**: `PRAGMA user_version` is a persistent integer built into SQLite's file header, requiring no extra table. Numbered files (e.g., `0001_init.sql`) provide a deterministic ordering. Forward-only application avoids the complexity and risk of downgrade scripts. Per-migration transactions prevent partial schema corruption.

**Deliverables**:
- `backend/src/binocular/db/migrations.py` — migration discovery, version comparison, application loop
- `backend/src/binocular/db/migrations/0001_init.sql` — seed migration establishing baseline

**Validation Criteria**:
1. **Given** a fresh database with `user_version=0`, **When** migrations `0001` through `000N` exist, **Then** all are applied in order and `user_version` equals `N`
2. **Given** `user_version=2` and migrations `0001`–`0004` exist, **When** the runner executes, **Then** only `0003` and `0004` are applied
3. **Given** a migration contains invalid SQL, **When** the runner applies it, **Then** the transaction is rolled back, `user_version` remains at the previous value, and the error is logged
4. **Given** no pending migrations, **When** the runner executes, **Then** no work is performed and startup continues

### Objective 3 - Pre-Migration Backup (Priority: P1)

Before applying any pending migration, the system must create a backup of the current database file via `VACUUM INTO`, ensuring a recovery point exists in case of migration failure or data corruption.

**Why this priority**: Data loss during schema upgrade violates Principle VI (set-and-forget reliability) — backup before migration is a non-negotiable safety gate.

**Rationale**: `VACUUM INTO` produces a consistent, compact copy of the database while the source remains operational. It works safely with WAL mode. The backup is only created when pending migrations exist, avoiding unnecessary I/O on routine startups.

**Deliverables**:
- Backup logic integrated into `backend/src/binocular/db/migrations.py`

**Validation Criteria**:
1. **Given** pending migrations exist, **When** the migration runner starts, **Then** a backup file is created at `{data_dir}/backups/binocular_pre_migrate_{timestamp}.db` before any migration is applied
2. **Given** no pending migrations, **When** the migration runner starts, **Then** no backup is created
3. **Given** the backup directory does not exist, **When** a backup is triggered, **Then** the directory is created automatically
4. **Given** `VACUUM INTO` fails (e.g., disk full), **When** the runner detects the failure, **Then** migrations are not applied and the error is logged

### Objective 4 - Repository Base Class (Priority: P1)

A base repository class must provide reusable async helpers for executing parameterized SQL queries and fetching results with named-column access, so domain repositories (E006+) have a consistent, type-safe data access pattern.

**Why this priority**: Core infrastructure for every domain repository — without it, each epic would duplicate query boilerplate.

**Rationale**: Raw SQL with parameterized queries is mandated (no ORM). A base class centralizes connection access, parameter binding, and row factory configuration. `aiosqlite.Row` enables dict-like access to columns, reducing index-based errors.

**Deliverables**:
- `backend/src/binocular/db/repository.py` — `RepositoryBase` class with `execute`, `fetch_one`, `fetch_all` helpers

**Validation Criteria**:
1. **Given** a `RepositoryBase` instance with a connection, **When** `execute` is called with a parameterized INSERT, **Then** the row is inserted and the method returns without error
2. **Given** a `RepositoryBase` instance, **When** `fetch_one` is called with a SELECT returning one row, **Then** the result supports named-column access (e.g., `row["column_name"]`)
3. **Given** a `RepositoryBase` instance, **When** `fetch_all` is called with a SELECT returning multiple rows, **Then** all rows are returned as a list with named-column access
4. **Given** a `RepositoryBase` instance, **When** `fetch_one` is called with a SELECT returning no rows, **Then** `None` is returned

### Technical Constraints

- No ORM — raw SQL with parameterized queries only
- WAL mode, `foreign_keys=ON`, `busy_timeout=5000` pragmas on every connection
- All backend code must pass `mypy --strict`
- Source code under `backend/src/binocular/` per ENFORCE_SRC_ROOT policy
- Database file at `{Settings.data_dir}/binocular.db`
- Migrations directory at `backend/src/binocular/db/migrations/`

## Integration Points

- **IP-001**: E001 (App Skeleton) provides the `create_app()` factory and async lifespan hook; database connection open/close integrates into this lifespan
- **IP-002**: E001 provides `Settings.data_dir` for the database file path
- **IP-003**: E006 (Device Inventory) will add domain migrations and repositories consuming `RepositoryBase`
- **IP-004**: E007 (Module Engine) will add module-related migrations consuming the migration runner
- **IP-005**: All domain epics (E006–E018) depend on the connection and repository base for data access

## Requirements

### Technical Requirements

- **TR-001**: System MUST establish an async aiosqlite connection during app startup with `journal_mode=WAL`, `foreign_keys=ON`, and `busy_timeout=5000`
- **TR-002**: System MUST store the database connection in app state accessible via FastAPI dependency injection
- **TR-003**: System MUST close the database connection cleanly during app shutdown
- **TR-004**: System MUST create the database file automatically if it does not exist
- **TR-005**: System MUST discover migration files matching `NNNN_*.sql` in the migrations directory and apply them in numeric order
- **TR-006**: System MUST track applied migration version via `PRAGMA user_version`
- **TR-007**: System MUST apply each migration within its own transaction, rolling back on failure
- **TR-008**: System MUST skip migrations whose version number is ≤ the current `user_version`
- **TR-009**: System MUST create a `VACUUM INTO` backup before applying pending migrations
- **TR-010**: System MUST skip backup creation when no migrations are pending
- **TR-011**: System MUST provide a `RepositoryBase` class with `execute`, `fetch_one`, and `fetch_all` async methods using parameterized queries
- **TR-012**: System MUST enable `aiosqlite.Row` row factory for named-column access in query results
- **TR-013**: System MUST log each migration application (version, filename) and any failures via structlog
- **TR-014**: All code MUST pass `mypy --strict`

### Key Entities

- **Database Connection**: Async aiosqlite connection configured with SQLite pragmas, managed by app lifespan. Not a domain entity — infrastructure.
- **Migration**: A numbered SQL file (`NNNN_description.sql`) containing forward-only schema changes. Version tracked via `PRAGMA user_version`.
- **RepositoryBase**: Abstract base providing parameterized query helpers for domain repositories. Not persisted — code abstraction.

## Assumptions & Risks

### Assumptions

- E001 app factory and lifespan are implemented and stable (verified: `.qc-passed` exists)
- `Settings.data_dir` defaults to `/app/data` and the directory exists or is writable by the application user
- aiosqlite supports `VACUUM INTO` (delegates to underlying sqlite3, which supports it since SQLite 3.27.0; Python 3.13 bundles SQLite ≥ 3.45)
- Single-user access pattern: one connection suffices without connection pooling

### Risks

- **WAL file cleanup on unclean shutdown** *(likelihood: low, impact: low)*: WAL and SHM files may persist after a crash. SQLite automatically recovers on next open. No mitigation needed beyond documentation.
- **Disk space for backup** *(likelihood: low, impact: medium)*: `VACUUM INTO` creates a full copy. For large databases with many modules, this could consume significant space. Mitigation: E018 will implement backup retention; for now, a single pre-migration backup is acceptable.

## Implementation Signals

- `NEW-API` — database connection dependency injection endpoint for route handlers
- `NEW-CONFIG` — database file path derived from existing `Settings.data_dir`
- `MIGRATION` — numbered migration runner and seed migration file
- `NEW-ENTITY` — RepositoryBase class and migration tracking via `user_version`

## Success Criteria

### Measurable Outcomes

- **SC-001** [OBJ1]: Application starts with a configured aiosqlite connection; `PRAGMA journal_mode` returns `wal`, `PRAGMA foreign_keys` returns `1`, `PRAGMA busy_timeout` returns `5000`
- **SC-002** [OBJ2]: On first startup with `0001_init.sql` present, `PRAGMA user_version` returns `1` after migration
- **SC-003** [OBJ3]: When pending migrations exist, a backup file is created in `{data_dir}/backups/` before migration; when none pending, no backup is created
- **SC-004** [OBJ4]: `RepositoryBase.fetch_one` returns a row with named-column access; `RepositoryBase.fetch_all` returns a list of such rows

## Glossary

| Term | Definition |
|------|------------|
| WAL | Write-Ahead Logging — SQLite journaling mode enabling concurrent reads during writes |
| user_version | SQLite pragma storing a persistent 32-bit integer in the database header, used here to track applied migration version |
| VACUUM INTO | SQLite command creating a compact, consistent backup copy of the database to a specified path |
| RepositoryBase | Abstract base class providing async execute/fetch helpers for raw parameterized SQL queries |

## Compliance Check

### Instructions Check Report
**Target**: spec.md
**Status**: PASS

| Principle | Verdict | Notes |
|-----------|---------|-------|
| I. Honest Failure | PASS | TR-007 requires migration rollback on failure; TR-013 requires logging failures |
| II. Polite by Default | N/A | No outbound scraping in data layer |
| III. Data Ownership | PASS | SQLite single file, no external DB, backup via VACUUM INTO |
| IV. Least-Privilege | N/A | No trust boundary changes |
| V. Type Safety | PASS | TR-014 requires mypy --strict |
| VI. Set-and-Forget | PASS | Auto-create DB, auto-apply migrations, pre-migration backup |
| VII. Agent Output Style | N/A | Spec document |
