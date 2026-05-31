# Data Model: Data Layer & Migrations

## Entities

| Entity | Purpose | Key Fields | Rules |
|--------|---------|------------|-------|
| Database Settings | Runtime persistence configuration | `database_path`, `backup_dir`, `busy_timeout_ms` | Defaults must work with no operator config and remain overrideable by `BINOCULAR_` settings. |
| Schema Version | Tracks applied migrations | `version`, `name`, `applied_at` | One row per applied migration version; version values are monotonic and unique. |
| Migration File | Append-only schema change artifact | `version`, `name`, `path`, `sql` | Filename numbering must be contiguous and immutable after merge. |
| Pre-Migration Backup | Safety snapshot before pending migration execution | `path`, `created_at`, `source_database` | Created only when pending migrations exist; failure blocks migration. |
| Repository Base | Shared raw-SQL data access helper | `connection`, `row_factory`, helper methods | Values are always bound parameters; dynamic identifiers require allowlists. |

## Relationships

| From | To | Cardinality | Notes |
|------|----|-------------|-------|
| Migration File | Schema Version | 1:0..1 | A migration gets a schema-version row only after successful application. |
| Database Settings | Pre-Migration Backup | 1:* | Backup location derives from configured data paths. |
| Repository Base | Database Settings | *:1 | Repositories open connections through the configured connection manager. |

## State Rules

| State | Trigger | Result |
|-------|---------|--------|
| No database | App startup | Create parent directory, open database, apply baseline migration. |
| No pending migrations | App startup | Validate pragmas; no backup created. |
| Pending migrations | App startup | Create backup, apply migrations in order, record schema versions. |
| Migration failed | SQL or validation error | Roll back active migration and fail startup visibly. |
| Backup failed | Snapshot error | Fail startup before applying migration SQL. |

## Validation Rules

| Rule | Validation |
|------|------------|
| Migration numbering | Fail on missing, duplicate, or non-contiguous versions. |
| Version tracking | Apply each migration and insert `schema_version` in the same transaction. |
| Connection setup | Set required pragmas immediately after opening a connection. |
| SQL values | Bind values via parameters; never format values into SQL strings. |
