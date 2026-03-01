# Research: DB Schema & Data Models

## Research Report

**Context**: Domain best practices for designing Binocular's foundational data layer — device inventory modeling, SQLite schema design, configuration storage, and extension metadata tracking.

### Device Inventory Data Modeling

- **Key findings**: Two-tier grouping (DeviceType → Device) is standard. DeviceType carries shared scraping config; Device carries instance state. Firmware versions should be stored as plain strings (schemes vary wildly). Derive update status at query time rather than persisting flags.
- **Recommended**: Separate `current_version`, `latest_seen_version`, and `last_checked_at` fields. Handle NULL `latest_seen_version` as "never checked" state.
- **Avoid**: Storing computed status flags; complex version-comparison logic in the DB layer.
- **Sources**: [sqlite.org/appfileformat](https://www.sqlite.org/appfileformat.html), [docs.pydantic.dev/latest/concepts/models](https://docs.pydantic.dev/latest/concepts/models/)

### SQLite Schema Design for Self-Hosted Apps

- **Key findings**: WAL mode enables concurrent reads during scheduler writes. `busy_timeout` (5000ms) handles contention. Foreign keys require explicit `PRAGMA foreign_keys = ON`. With <1K rows, minimal indexing is sufficient.
- **Recommended**: Enable foreign keys at connection time, use `ON DELETE CASCADE` for parent-child relationships, keep to 3–5 core tables for MVP, use numbered SQL migrations with a `schema_version` metadata entry.
- **Avoid**: Over-indexing small tables, using alembic/heavy migration frameworks for a single-file DB.
- **Sources**: [sqlite.org/wal.html](https://www.sqlite.org/wal.html), [sqlite.org/whentouse.html](https://www.sqlite.org/whentouse.html)

### Configuration & Settings Storage Patterns

- **Key findings**: Three patterns — single-row typed table, key-value store, JSON blob. Single-row typed table maps directly to Pydantic `BaseSettings` and preserves type safety.
- **Recommended**: Single-row `app_config` table with typed columns. Use SQLite UPSERT for atomic writes.
- **Avoid**: Key-value stores (lose type safety), JSON blobs (harder to query).
- **Sources**: [sqlite.org/lang_upsert.html](https://www.sqlite.org/lang_upsert.html), [docs.pydantic.dev/latest/concepts/pydantic_settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

### Extension/Plugin Metadata Storage

- **Key findings**: Need a registry table for module lifecycle: filename, version, supported device type, activation status, error state. Create records after successful contract validation. Store file hash for change detection on restart.
- **Recommended**: `extension_module` table with `filename` (unique), `module_version`, `is_active`, `last_error`, `file_hash`. DeviceType references its module by foreign key.
- **Avoid**: Creating module records before validation succeeds.
- **Sources**: [docs.python.org/3/library/importlib.html](https://docs.python.org/3/library/importlib.html), [packaging.python.org/en/latest/guides/creating-and-discovering-plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/)

### Sources Index

- https://www.sqlite.org/appfileformat.html
- https://docs.pydantic.dev/latest/concepts/models/
- https://www.sqlite.org/wal.html
- https://www.sqlite.org/whentouse.html
- https://www.sqlite.org/lang_upsert.html
- https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- https://docs.python.org/3/library/importlib.html
- https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/
