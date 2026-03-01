# Quickstart: Database Schema & Data Models

**Branch**: `00001-db-schema-models` | **Plan**: [plan.md](plan.md) | **Data Model**: [data-model.md](data-model.md)

## Overview

This quickstart describes how the data layer integrates with downstream features and how to verify it works correctly. The feature delivers: SQLite connection factory, migration runner, Pydantic models, and repository layer.

## Integration Scenarios

### Scenario 1: Fresh Application Startup

**Actors**: Application process (on boot)

1. Application starts → connection factory opens `binocular.db` in `/app/data`
2. Connection factory applies pragmas: `journal_mode = WAL`, `busy_timeout = 5000`, `foreign_keys = ON`
3. Migration runner reads `schema_version` table (creates it if missing → fresh DB detected per FR-015)
4. Migration runner scans `migrations/` directory, applies any unapplied scripts in numeric order
5. `app_config` seed row exists with all defaults → application is functional with zero configuration (FR-009)

**Verification**: Query `PRAGMA journal_mode` → returns `wal`. Query `SELECT * FROM app_config` → returns one row with default values. Query `SELECT version FROM schema_version` → returns current migration number.

### Scenario 2: Device Inventory CRUD (Integration with Feature 1.2)

**Actors**: Inventory API (future Feature 1.2) → Repository layer → SQLite

1. API receives "Create Device Type" request → calls `DeviceTypeRepo.create(DeviceTypeCreate(name="Sony Alpha Bodies", firmware_source_url="https://..."))`
2. Repository validates via Pydantic model, executes INSERT, returns `DeviceType` model
3. API receives "Add Device" request → calls `DeviceRepo.create(DeviceCreate(device_type_id=1, name="A7IV", current_version="3.01"))`
4. Repository validates, executes INSERT with composite unique check, returns `Device` model
5. Duplicate device name within same type → `IntegrityError` caught → validation error returned

**Verification**: `SELECT * FROM device WHERE device_type_id = 1` returns the device. Attempting a duplicate name raises an `IntegrityError`.

### Scenario 3: Firmware Check Lifecycle (Integration with Features 2.x, 3.x)

**Actors**: Scheduler (future Feature 3.1) → Extension Engine (future Feature 2.x) → Repository layer

1. Scheduler triggers a check → Extension Engine scrapes firmware page → returns version string
2. `DeviceRepo.update_latest_version(device_id=1, version="3.02", checked_at=now)` sets `latest_seen_version` and `last_checked_at`
3. Query-time status derivation: `version_compare("3.01", "3.02")` → semver comparison → "Update Available"
4. User confirms update → `DeviceRepo.confirm_update(device_id=1)` sets `current_version = latest_seen_version`
5. `CheckHistoryRepo.create(...)` logs the event → piggyback cleanup deletes entries older than 90 days

**Verification**: Device's `latest_seen_version` updated. History entry created. Old entries purged.

### Scenario 4: Extension Module Registration (Integration with Feature 2.1)

**Actors**: Module Validation Engine (future Feature 2.2) → Repository layer

1. Module file `sony_alpha.py` placed in `/app/modules`
2. Validation engine loads file, validates contract → passes
3. `ExtensionModuleRepo.register(filename="sony_alpha.py", module_version="1.0.0", file_hash="abc123")` → sets `is_active=1`
4. `DeviceTypeRepo.assign_module(device_type_id=1, extension_module_id=1)` links the module
5. On next restart, if file hash changed → module revalidated, registry updated (US4-AS3)

**Verification**: `SELECT * FROM extension_module WHERE filename = 'sony_alpha.py'` shows active with hash.

### Scenario 5: Application Upgrade with Schema Migration

**Actors**: Application process (on boot after upgrade)

1. New version ships with `002_add_notes_column.sql` in `migrations/`
2. Migration runner reads `schema_version` → current is `1`
3. Runner finds `002_*.sql`, applies it in a transaction → `ALTER TABLE device ADD COLUMN notes TEXT`
4. Runner updates `schema_version` to `2`
5. Existing data preserved — all devices still present with new column defaulting to NULL

**Verification**: `SELECT version FROM schema_version` → `2`. `SELECT notes FROM device` → column exists, existing rows have NULL.

## Setup Instructions (for Development)

### Prerequisites

- Python 3.11+
- Poetry or pip with a virtual environment

### Local Development

```bash
# Install dependencies
pip install fastapi pydantic aiosqlite pytest pytest-asyncio

# Run migration on a local DB
python -c "
import asyncio
from backend.src.db.connection import get_connection
from backend.src.db.migration_runner import run_migrations
asyncio.run(run_migrations('dev.db'))
"

# Run tests (uses temp-file SQLite fixtures)
pytest backend/tests/ -v
```

### Docker Development

```bash
docker compose up -d
# DB is auto-created at /app/data/binocular.db with WAL mode
# Migrations auto-applied on startup
```

## Key Integration Points

| Component | Depends On | Interface |
|---|---|---|
| Inventory API (Feature 1.2) | Repository layer | `DeviceTypeRepo`, `DeviceRepo` async methods |
| Extension Engine (Feature 2.x) | `ExtensionModuleRepo` | `register()`, `update_hash()`, `set_error()` |
| Scheduler (Feature 3.1) | `DeviceRepo`, `CheckHistoryRepo` | `update_latest_version()`, `create()` |
| Alerting (Feature 4.2) | `AppConfigRepo` | `get_config()` for notification settings |
| Settings UI (Feature 1.3) | `AppConfigRepo` | `get_config()`, `update_config()` |
