# Data Model: Module Engine & Contract

## Entities

| Entity | Purpose | Key Fields | Constraints |
|--------|---------|------------|-------------|
| ModuleRecord | Durable installed-module metadata and latest validation summary. | id, module_id, display_name, source_path, source_hash, author, version, status, validation_status, validation_summary_json, last_validated_at, created_at, updated_at | `module_id` unique; status and validation_status constrained enums; source_path required. |

## State Values

| Field | Values | Meaning |
|-------|--------|---------|
| status | installed, disabled | Lifecycle-visible state reserved for E008. |
| validation_status | unvalidated, valid, invalid | Latest validation outcome used by lifecycle and check consumers. |

## Relationships

| Relationship | Cardinality | Notes |
|--------------|-------------|-------|
| ModuleRecord to module file | 1:1 | `source_path` points to a file under configured `modules_dir`. |
| ModuleRecord to validation summary | 1:1 embedded JSON text | Latest summary only; detailed run history belongs to future activity logging. |

## Migration Notes

- Add `003_modules.sql`; never renumber existing migrations.
- Use raw SQL with parameter binding through the existing repository base.
- Store validation summary as JSON text so the initial engine avoids premature table expansion.
