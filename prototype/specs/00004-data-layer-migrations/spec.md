---
spec_type: technical
epic_id: E004
epic_sources:
  - SAD:ADR-0004
  - DOD:DDR-003
spec_maturity: draft
---

# Feature Specification: Data Layer & Migrations

## Problem Statement

Binocular has a runnable FastAPI shell but no durable persistence layer for inventory, modules, check results, logs, or operational state. Later epics depend on one self-contained SQLite database with predictable startup migrations and reusable repository helpers. Without this foundation, downstream features would duplicate database access or risk silent data loss during schema changes.

## Scope

### Included

- Add an `aiosqlite` SQLite connection lifecycle under `backend/src/binocular/`.
- Initialize SQLite with WAL mode, `foreign_keys=ON`, and a bounded `busy_timeout`.
- Add a forward-only numbered migration runner tracked by `schema_version`.
- Run pending migrations during FastAPI lifespan startup before request handling.
- Create a timestamped pre-migration backup before applying pending migrations.
- Provide a repository base for raw, parameterized SQL access and row mapping.
- Add backend tests for migration ordering, pragmas, backups, and repository helpers.

### Excluded

- Device, module, check-result, notification, or activity-log domain tables - later epics own their schemas.
- External databases, ORM integration, or multi-instance coordination - project instructions require single-file SQLite and raw SQL.
- Backup scheduling and restore runbooks - E019 owns ongoing operations.
- Frontend UI for database health or migrations - no operator-facing UI is required for this technical foundation.

### Edge Cases & Boundaries

- If no migrations are pending, startup must be idempotent and must not create a new backup snapshot.
- Backup failure must fail startup before any pending migration applies.
- Migration failure must roll back schema changes and `schema_version` updates together.
- Missing, duplicate, or non-contiguous migration numbers must fail startup visibly.
- Empty database files and missing parent data directories must work during zero-config startup.
- Application code must never build SQL value clauses with string interpolation.

## Technical Objectives

### OBJ1 [P1] SQLite connection lifecycle and settings

**Why this priority**: Every downstream persistence feature depends on a correctly configured single-file SQLite connection.

**Rationale**: The app must preserve data ownership while supporting local API reads and background writes.

**Deliverables**: database settings, connection manager, lifespan hooks, pragma setup, migration logs.

**Validation Criteria**:
1. **Given** a zero-config runtime, **When** the app starts, **Then** it creates or opens the SQLite database under the configured data path.
2. **Given** a new connection, **When** pragmas are inspected, **Then** WAL mode, foreign keys, and busy timeout behavior are active.

### OBJ2 [P1] Numbered migration runner with atomic version tracking

**Why this priority**: Schema evolution must be deterministic before any feature stores durable state.

**Rationale**: Forward-only numbered migrations give maintainers a reviewable path for database changes without an ORM.

**Deliverables**: migration loader, `schema_version`, transaction runner, ordering validation, startup hook.

**Validation Criteria**:
1. **Given** an empty database and ordered migrations, **When** startup runs, **Then** all pending migrations apply in order and their versions are recorded.
2. **Given** a migration raises an error, **When** startup runs, **Then** the migration transaction rolls back and the failed version is not recorded.

### OBJ3 [P1] Pre-migration backup snapshot hook

**Why this priority**: Schema changes must not risk irreversible data loss in the single backup-able SQLite volume.

**Rationale**: The Deployment and Operations requirements call for an automatic safety snapshot before applying pending migrations.

**Deliverables**: backup directory, timestamped snapshots, hard-fail behavior, pending/no-op tests.

**Validation Criteria**:
1. **Given** at least one pending migration, **When** startup runs, **Then** a timestamped database snapshot is created before the first migration executes.
2. **Given** backup creation fails, **When** startup runs, **Then** no pending migration is applied and the failure is logged visibly.

### OBJ4 [P2] Repository base for parameterized raw SQL

**Why this priority**: Downstream domain epics can ship faster and more safely when shared data-access patterns already exist.

**Rationale**: A small base keeps raw SQL explicit while standardizing row mapping and parameter binding.

**Deliverables**: repository base, row helpers, execute/fetch helpers, parameterized-access tests.

**Validation Criteria**:
1. **Given** a repository method uses helper APIs, **When** it executes SQL with values, **Then** values are supplied through bound parameters.
2. **Given** a query returns rows, **When** the repository maps them, **Then** callers receive predictable typed data structures without raw cursor lifetime leaks.

### Technical Constraints

- No ORM may be introduced; all persistence uses raw parameterized SQL.
- Migrations are forward-only and append-only; merged files must not be renumbered.
- SQLite state must stay in the configured data directory under `/app/data`.
- Database initialization must complete before API routes or background work use repositories.
- Backup, ordering, or migration failure must surface as startup failure.

## Integration Points

| Integration | Contract | Owner |
|-------------|----------|-------|
| FastAPI lifespan from E001 | Initialize DB and apply migrations before requests | Backend app factory |
| Settings from E001 | Provide DB and backup paths with `BINOCULAR_` overrides | Backend config |
| Future E005/E006/E014 schemas | Add append-only migrations and repositories using the shared base | Domain epics |
| E019 backup operations | Reuse database and backup directory conventions | Operations epic |

## Requirements

TR-001: System MUST define a zero-config SQLite path inside the application data volume with `BINOCULAR_` overrides.
TR-002: System MUST initialize every SQLite connection with WAL mode, `foreign_keys=ON`, and bounded busy timeout before transactions.
TR-003: System MUST maintain a `schema_version` table that records applied numbered migration versions.
TR-004: System MUST discover migration files, validate numbering, and apply only pending migrations in ascending order.
TR-005: System MUST apply each migration and its `schema_version` update atomically.
TR-006: System MUST run pending migrations during FastAPI lifespan startup before API request handling begins.
TR-007: System MUST create a timestamped backup snapshot before applying pending migrations to an existing database.
TR-008: System MUST fail startup visibly when backup creation, migration ordering, or migration execution fails.
TR-009: System MUST provide repository helpers for raw parameterized SQL execution, fetching, and row mapping.
TR-010: System MUST include backend tests for pragmas, startup idempotence, migrations, backups, and repository helpers.
TR-011: System MUST bind SQL values through parameters and restrict any dynamic SQL identifiers to static allowlists.

### Key Entities

- **Database Settings**: Database, backup, and busy-timeout values.
- **Connection Manager**: Opens connections with required pragmas.
- **Migration**: Numbered SQL file for one schema change.
- **Schema Version**: Applied migration record.
- **Pre-Migration Backup**: Snapshot before migrations.
- **Repository Base**: Shared helper for parameterized SQL.

## Assumptions & Risks

### Assumptions

- `aiosqlite` remains the only async SQLite dependency for backend persistence.
- Startup migrations run before background schedulers are introduced.
- The default DB location is writable by the non-root container user.
- Later epics will append migrations without modifying prior files.

### Risks

- WAL backup behavior can be wrong if raw file copy is used instead of SQLite backup semantics *(likelihood: medium, impact: high)*.
- Migration startup failures can make the app unavailable until fixed, but this is preferable to silent data corruption *(likelihood: low, impact: medium)*.
- Future parallel epics can collide on migration numbering unless project-plan guidance is followed *(likelihood: medium, impact: medium)*.

## Implementation Signals

- **NEW-ENTITY**: Add schema metadata and migration concepts used by all future persistent features.
- **MIGRATION**: Add initial migration and migration runner infrastructure.
- **NEW-CONFIG**: Add database path, backup path, and busy-timeout settings with zero-config defaults.
- **NEW-API**: No public HTTP API is required; internal repository APIs become the integration surface.
- **BREAKING-CHANGE**: FastAPI startup now fails if persistence initialization cannot complete.

## Success Criteria

SC-001 [OBJ1]: Backend tests verify SQLite connections expose WAL mode, enabled foreign keys, and configured busy timeout.
SC-002 [OBJ2]: Starting with an empty database applies all numbered migrations once and records their versions in ascending order.
SC-003 [OBJ2]: A failing migration leaves both schema state and `schema_version` unchanged for that migration.
SC-004 [OBJ3]: Pending migrations create a timestamped backup snapshot before migration SQL executes.
SC-005 [OBJ3]: Backup failure exits startup visibly and leaves pending migrations unapplied.
SC-006 [OBJ4]: Repository helper tests demonstrate bound parameters and stable row mapping without raw cursor leaks.
SC-007 [OBJ4]: Repository tests verify dynamic SQL identifiers are allowlisted when identifier selection is required.

## Compliance Check

| Check | Result | Notes |
|-------|--------|-------|
| Project instructions alignment | PASS | Preserves self-contained SQLite, visible failure, zero-config startup, raw parameterized SQL, and backend validation. |
