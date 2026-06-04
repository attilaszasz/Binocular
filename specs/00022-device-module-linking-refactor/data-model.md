# Data Model Design — Device-Module Linking & Refactor

**Epic**: E022  
**Spec**: `specs/00022-device-module-linking-refactor/spec.md`  
**Status**: Draft  
**Phase**: Plan (pre-implementation design)

---

## 1. Schema Before (Pre-Migration)

Migration versions 002–006 define the following schema. All tables use SQLite with `PRAGMA foreign_keys = ON` enforced at connection time.

### Table: `device_types`

| Column           | Type    | Constraints                          |
|------------------|---------|--------------------------------------|
| id               | INTEGER | PRIMARY KEY                          |
| name             | TEXT    | NOT NULL                             |
| normalized_name  | TEXT    | NOT NULL UNIQUE                      |
| created_at       | TEXT    | NOT NULL DEFAULT CURRENT_TIMESTAMP   |
| updated_at       | TEXT    | NOT NULL DEFAULT CURRENT_TIMESTAMP   |

Source: `backend/src/binocular/db/migrations/002_inventory.sql` lines 1–7

### Table: `devices`

| Column            | Type    | Constraints                                                    |
|-------------------|---------|----------------------------------------------------------------|
| id                | INTEGER | PRIMARY KEY                                                    |
| device_type_id    | INTEGER | NOT NULL REFERENCES device_types(id)                          |
| name              | TEXT    | NOT NULL                                                       |
| model             | TEXT    | NOT NULL                                                       |
| current_version   | TEXT    | NOT NULL                                                       |
| latest_version    | TEXT    |                                                                |
| last_checked_at   | TEXT    |                                                                |
| last_success_at   | TEXT    |                                                                |
| last_check_status | TEXT    | NOT NULL DEFAULT 'never_checked' CHECK (IN (...))              |
| is_archived       | INTEGER | NOT NULL DEFAULT 0 CHECK (IN (0, 1))                          |
| created_at        | TEXT    | NOT NULL DEFAULT CURRENT_TIMESTAMP                             |
| updated_at        | TEXT    | NOT NULL DEFAULT CURRENT_TIMESTAMP                             |

Index: `idx_devices_active_type_name` ON devices (is_archived, device_type_id, name COLLATE NOCASE)

Source: `backend/src/binocular/db/migrations/002_inventory.sql` lines 9–26

### Table: `modules` (UNCHANGED by E022)

| Column                  | Type    | Constraints                          |
|-------------------------|---------|--------------------------------------|
| id                      | INTEGER | PRIMARY KEY                          |
| module_id               | TEXT    | NOT NULL UNIQUE                      |
| display_name            | TEXT    | NOT NULL                             |
| source_path             | TEXT    | NOT NULL                             |
| source_hash             | TEXT    | NOT NULL                             |
| author                  | TEXT    |                                      |
| version                 | TEXT    |                                      |
| status                  | TEXT    | NOT NULL DEFAULT 'installed' CHECK ('installed','disabled') |
| validation_status       | TEXT    | NOT NULL DEFAULT 'unvalidated' CHECK ('unvalidated','valid','invalid') |
| validation_summary_json | TEXT    | NOT NULL DEFAULT '{}'               |
| last_validated_at       | TEXT    |                                      |
| created_at              | TEXT    | NOT NULL DEFAULT CURRENT_TIMESTAMP   |
| updated_at              | TEXT    | NOT NULL DEFAULT CURRENT_TIMESTAMP   |

Index: `idx_modules_status_name` ON modules (status, display_name COLLATE NOCASE)

Source: `backend/src/binocular/db/migrations/003_modules.sql`

### Table: `device_type_schedules`

| Column              | Type    | Constraints                          |
|---------------------|---------|--------------------------------------|
| device_type_id      | INTEGER | PRIMARY KEY REFERENCES device_types(id) |
| enabled             | INTEGER | NOT NULL DEFAULT 0                   |
| interval_minutes    | INTEGER | NOT NULL DEFAULT 1440               |
| next_run_at         | TEXT    |                                      |
| last_started_at     | TEXT    |                                      |
| last_completed_at   | TEXT    |                                      |
| last_success_at     | TEXT    |                                      |
| last_failure_at     | TEXT    |                                      |
| last_failure_reason | TEXT    |                                      |
| last_skip_reason    | TEXT    |                                      |
| updated_at          | TEXT    | NOT NULL DEFAULT CURRENT_TIMESTAMP   |

Source: `backend/src/binocular/db/migrations/004_schedules.sql`

### Other tables (UNCHANGED by E022)

- `app_metadata` (001_initial.sql)
- `notification_channels` (005_notification_channels.sql)
- `activity_log` (006_activity_log.sql)
- `schema_version` (managed by `MigrationRunner` in `migrations.py`)

---

## 2. Schema After (Post-Migration)

### Table: `devices` — MIGRATED

| Column            | Type    | Constraints                                                     |
|-------------------|---------|-----------------------------------------------------------------|
| id                | INTEGER | PRIMARY KEY                                                     |
| module_id         | INTEGER | REFERENCES modules(id) (NULLABLE; NOT NULL enforced at app layer) |
| name              | TEXT    | NOT NULL                                                        |
| model             | TEXT    | NOT NULL                                                        |
| current_version   | TEXT    | NOT NULL                                                        |
| latest_version    | TEXT    |                                                                 |
| last_checked_at   | TEXT    |                                                                 |
| last_success_at   | TEXT    |                                                                 |
| last_check_status | TEXT    | NOT NULL DEFAULT 'never_checked' CHECK (IN (...))               |
| is_archived       | INTEGER | NOT NULL DEFAULT 0 CHECK (IN (0, 1))                           |
| created_at        | TEXT    | NOT NULL DEFAULT CURRENT_TIMESTAMP                              |
| updated_at        | TEXT    | NOT NULL DEFAULT CURRENT_TIMESTAMP                              |

Changes from `before`:
- **Removed**: `device_type_id INTEGER NOT NULL REFERENCES device_types(id)`
- **Added**: `module_id INTEGER REFERENCES modules(id)` (NULLABLE after migration; application enforces NOT NULL on create/update)
- Device type is now **derived** at query time: `JOIN modules m ON m.id = d.module_id` → `m.display_name AS device_type`

### Table: `modules` — UNCHANGED

Same as before. No columns added, no schema change. The `id` column (INTEGER PRIMARY KEY) is the FK target on `devices.module_id`.

### Table: `device_type_schedules` — EMPTIED

All rows are deleted during migration. The table structure remains intact but unused until the operator reconfigures per-module schedules (future epic). The table is a candidate for dropping in a subsequent migration once per-module scheduling is implemented.

### Table: `device_types` — DROPPED

The `device_types` table is removed entirely by migration 007.

---

## 3. Entity Relationships

### Before (Pre-Migration)

```
┌──────────────────┐          ┌─────────────────────┐
│   device_types   │          │  device_type_        │
│──────────────────│          │  schedules           │
│ id (PK)          │◄─────────│  device_type_id (PK, │
│ name             │          │    FK→device_types)  │
│ normalized_name  │          │  enabled             │
└────────┬─────────┘          │  interval_minutes    │
         │                    └──────────────────────┘
         │ FK: device_type_id
         │
┌────────▼─────────┐
│     devices      │
│──────────────────│
│ id (PK)          │
│ device_type_id   │
│  → device_types  │
│ name, model      │
│ current_version  │
│ latest_version   │
│ last_check_status│
│ is_archived      │
└──────────────────┘

         implicit (no FK, resolved at check time)
                    │
                    ▼
┌──────────────────┐
│     modules      │
│ id (PK)          │
│ module_id (UQ)   │
│ display_name     │
│ status           │
│ validation_status│
└──────────────────┘
```

**Problem**: The `device_types` table duplicates module identity. `devices` → `device_types` → implicit module matching at check time via `device_types.name` compared to `modules.display_name`. This is fragile and allows type drift.

### After (Post-Migration — Target DAG)

```
┌──────────────────────┐
│       modules        │
│──────────────────────│
│ id (PK)              │
│ module_id (UQ)       │
│ display_name         │
│ source_path          │
│ status               │
│ validation_status    │
└──────────┬───────────┘
           │
           │ FK: module_id            ┌─────────────────────┐
           │                          │  device_type_        │
┌──────────▼───────────┐             │  schedules           │
│       devices        │             │  (empty post-007)    │
│──────────────────────│             │  table retained      │
│ id (PK)              │             │  for per-module      │
│ module_id            │             │  schedule future     │
│  → modules.id        │             └─────────────────────┘
│ name, model          │
│ current_version      │
│ latest_version       │
│ last_check_status    │
│ is_archived          │
└──────────────────────┘

         DROPPED:
┌──────────────────────┐
│  ~~device_types~~    │  ← DROPPED in migration 007
│  (removed entirely)  │
└──────────────────────┘
```

**Design rationale**: A single source of truth (`modules`) determines both device identity and check capability. `devices.module_id` is NULLABLE in the schema (to survive module deletion and allow unmatchable post-migration devices) but the application layer enforces NOT NULL on create and update.

---

## 4. Migration Steps (`007_module_linking.sql`)

Migration file path: `backend/src/binocular/db/migrations/007_module_linking.sql`

### 4.1 Design Decisions

- **Foreign keys**: Enabled via `PRAGMA foreign_keys = ON`. The `ConnectionManager.open()` method already sets this pragma per connection (`connection.py` line 23), but the migration file restates it for self-documenting safety.
- **NULLABLE module_id**: Adding a column with a FK constraint is only safe in SQLite when the default is NULL (or when a valid default references an existing row). Using `DEFAULT NULL` avoids errors on existing rows.
- **NOT NULL enforcement**: The application layer (`InventoryService.create_device`, `update_device`) validates that `module_id` is provided. The schema does not add a NOT NULL constraint because:
  1. Existing rows must be NULL until backfill completes.
  2. Devices that cannot be matched during migration remain NULL (unlinked).
  3. SQLite does not support `ALTER TABLE ... ADD COLUMN ... NOT NULL`.
- **Column removal**: SQLite `ALTER TABLE ... DROP COLUMN` (supported since 3.35.0) rebuilds the table internally. The backup created by `MigrationRunner.apply_pending()` before applying pending migrations provides rollback safety.
- **Schedule clearing**: All `device_type_schedules` rows are deleted. Operators reconfigure per-module schedules post-migration through the UI.
- **Table drop**: `device_types` is dropped after `devices` is migrated and schedules are cleared. The `device_type_schedules` table retains its FK to `device_types`, so the FK must be resolved before dropping `device_types` (either by clearing schedule rows first, then dropping the table).

### 4.2 Migration SQL

```sql
-- Migration: Link devices to modules, drop device_types entity
-- Number: 007
-- Requires: PRAGMA foreign_keys = ON

PRAGMA foreign_keys = ON;

-- ──────────────────────────────────────────────
-- Step 1: Add module_id FK column to devices
-- ──────────────────────────────────────────────
-- NULLABLE at schema level; application enforces NOT NULL on create/update.
ALTER TABLE devices
    ADD COLUMN module_id INTEGER REFERENCES modules(id) DEFAULT NULL;

-- ──────────────────────────────────────────────
-- Step 2: Best-effort backfill
-- ──────────────────────────────────────────────
-- Match existing device_types.name to modules.display_name
-- case-insensitively. Unmatchable devices remain NULL
-- (will appear as "unlinked" in the UI).
UPDATE devices
SET module_id = (
    SELECT m.id
    FROM modules m
    JOIN device_types dt ON dt.id = devices.device_type_id
    WHERE lower(m.display_name) = lower(dt.name)
    LIMIT 1
);

-- ──────────────────────────────────────────────
-- Step 3: Drop the old device_type_id column
-- ──────────────────────────────────────────────
-- SQLite 3.35.0+ supports ALTER TABLE ... DROP COLUMN.
-- The backup snapshot created before migration provides
-- rollback if needed.
ALTER TABLE devices DROP COLUMN device_type_id;

-- ──────────────────────────────────────────────
-- Step 4: Drop the old composite index
-- ──────────────────────────────────────────────
-- The index referenced device_type_id which no longer exists.
DROP INDEX IF EXISTS idx_devices_active_type_name;

-- ──────────────────────────────────────────────
-- Step 5: Create new index for the new FK
-- ──────────────────────────────────────────────
-- Supports common queries: list active devices by module,
-- ordered by module display name then device name.
CREATE INDEX idx_devices_active_module_name
    ON devices (is_archived, module_id, name COLLATE NOCASE);

-- ──────────────────────────────────────────────
-- Step 6: Clear device_type_schedules
-- ──────────────────────────────────────────────
-- Operator reconfigures per-module schedules post-migration.
-- The table structure is retained for future per-module
-- scheduling (out of scope for E022).
DELETE FROM device_type_schedules;

-- ──────────────────────────────────────────────
-- Step 7: Drop the device_types table
-- ──────────────────────────────────────────────
-- No remaining FKs point to it (devices column dropped,
-- schedule rows deleted). The table is no longer needed.
DROP TABLE IF EXISTS device_types;
```

### 4.3 Migration Execution Context

The `MigrationRunner` (`backend/src/binocular/db/migrations.py`) handles the migration lifecycle:

1. **Pre-flight**: Calls `discover_migrations()` which loads all `NNN_name.sql` files sorted by version. The migration file must be named `007_module_linking.sql` to fit the existing pattern: `r"^(?P<version>\d{3})_(?P<name>[a-z0-9_]+)\.sql$"`.
2. **Backup**: Before applying any pending migration, if the database already existed, `create_backup_snapshot()` writes a backup to the configured `backup_dir`.
3. **Apply**: Each migration is wrapped in `BEGIN IMMEDIATE … COMMIT`. Statements are split on semicolons (respecting `BEGIN … END` blocks) and executed sequentially.
4. **Record**: After success, an entry is written to `schema_version (version, name, applied_at)`.

### 4.4 Rollback Path

- The automatic pre-migration backup snapshot (backed by `create_backup_snapshot` in `backup.py`) is the primary rollback mechanism.
- To rollback: restore the backup snapshot over the database file, then restart the application. The `schema_version` table is part of the backup and will reflect only pre-007 applied migrations.
- No `DOWN` script is needed — migrations are forward-only by design.

---

## 5. State Transitions for Device Linking

### 5.1 Device Link States

```
┌──────────────┐          ┌──────────────┐          ┌──────────────┐
│   LINKED     │          │  UNLINKED    │          │  ARCHIVED    │
│              │          │              │          │              │
│ module_id =  │  delete  │ module_id =  │          │ is_archived  │
│   valid FK   │──module──│    NULL      │          │    = 1       │
│              │──────────│              │          │              │
│  device type │          │  device type │          │  (hidden     │
│  = display   │  edit +  │  = "Unlinked"│  archive │   from       │
│  _name       │  select  │              │──────────│   inventory) │
│              │──module──│              │          │              │
└──────────────┘          └──────────────┘          └──────────────┘
       │                        │
       │                        │
       │  edit + select         │
       │  different module      │
       │────────────────────────│
       ▼                        ▼
┌──────────────┐          ┌──────────────┐
│   LINKED     │          │   LINKED     │
│ (new module) │          │ (reassigned) │
└──────────────┘          └──────────────┘
```

### 5.2 Transition Rules

| Transition                     | Trigger                                      | module_id Result     | App Behavior                                          |
|--------------------------------|----------------------------------------------|----------------------|-------------------------------------------------------|
| Created with module selector   | Operator submits device creation form        | Selected module's id | Device appears under module's display_name group      |
| Edited to different module     | Operator changes module on edit form         | New module's id      | Device moves to new group; type display updates       |
| Linked module deleted          | Operator deletes a module from system        | NULL (set by app)    | Device appears in "Unlinked" group; edit to reassign  |
| Migration: match found         | Migration 007 backfill succeeds              | Matched module's id  | Device appears under matched module's name            |
| Migration: no match found      | Migration 007 backfill fails                 | NULL                 | Device appears in "Unlinked" group; edit to reassign  |
| Archived                       | Operator archives device                     | Unchanged (retained) | Device hidden from inventory; not shown in any group  |
| Creation when no valid modules | Operator opens create form                   | — (blocked)          | UI shows guidance: "Install and validate a module first" |

### 5.3 Handling Module Deletion

When a module is deleted via `ModuleRepository.delete_module()`:

1. The application (service layer) queries all devices where `module_id = <deleted_module_id>`.
2. Each affected device has its `module_id` set to NULL.
3. Devices appear in inventory grouped under "Unlinked" with a reassignment prompt.
4. The `DELETE FROM modules` succeeds because `devices.module_id` has no `ON DELETE CASCADE` or `ON DELETE SET NULL` clause — the application handles the cascade explicitly to ensure it runs before the module row is removed.

**SQLite FK behavior**: With `PRAGMA foreign_keys = ON`, deleting a module row that still has referencing devices would fail with a foreign key constraint error. Therefore:
- The application **must** set `module_id = NULL` on referencing devices **before** deleting the module row.
- Alternatively, add `ON DELETE SET NULL` to the FK constraint, but explicit handling gives the application control to log the unlink event and notify the operator.

---

## 6. Repository Query Changes

### 6.1 `InventoryRepository` — `inventory.py`

All queries that currently JOIN `device_types` are rewritten to JOIN `modules`.

#### `DeviceRecord` dataclass

| Field          | Before (J2C)                | After (E022)                | Change Reason                        |
|----------------|-----------------------------|-----------------------------|--------------------------------------|
| device_type_id | `int` (from `device_types.id`) | `int` (renamed to `module_id`) | FK target changed                    |
| device_type    | `str` (from `device_types.name`) | `str` (from `modules.display_name`) | Derived from modules, not device_types |

Post-migration `DeviceRecord`:

```python
@dataclass(frozen=True)
class DeviceRecord:
    id: int
    module_id: int | None          # ⬅  was device_type_id: int
    device_type: str               # ⬅  derived from modules.display_name
    name: str
    model: str
    current_version: str
    latest_version: str | None
    last_checked_at: str | None
    last_success_at: str | None
    status: str
    created_at: str
    updated_at: str
```

Note: `module_id` is `int | None` because unlinked devices have NULL. The service layer rejects NULL on create/update.

#### Query: `get_device(device_id)` — single device

**Before**:
```sql
SELECT d.id, d.device_type_id, dt.name AS device_type, d.name, d.model,
       d.current_version, d.latest_version, d.last_checked_at, d.last_success_at,
       d.last_check_status AS status, d.created_at, d.updated_at
FROM devices d
JOIN device_types dt ON dt.id = d.device_type_id
WHERE d.id = ? AND d.is_archived = 0
```

**After**:
```sql
SELECT d.id, d.module_id,
       COALESCE(m.display_name, 'Unlinked') AS device_type,
       d.name, d.model,
       d.current_version, d.latest_version,
       d.last_checked_at, d.last_success_at,
       d.last_check_status AS status, d.created_at, d.updated_at
FROM devices d
LEFT JOIN modules m ON m.id = d.module_id
WHERE d.id = ? AND d.is_archived = 0
```

Changes:
- `device_type_id` → `module_id`
- `JOIN device_types` → `LEFT JOIN modules` (LEFT JOIN because unlinked devices have NULL `module_id`)
- `dt.name AS device_type` → `COALESCE(m.display_name, 'Unlinked') AS device_type`
- `_record_from_row` uses `"module_id"` key instead of `"device_type_id"`

#### Query: `list_active_devices()` — all active devices

**Before**:
```sql
SELECT d.id, d.device_type_id, dt.name AS device_type, d.name, d.model,
       d.current_version, d.latest_version, d.last_checked_at, d.last_success_at,
       d.last_check_status AS status, d.created_at, d.updated_at
FROM devices d
JOIN device_types dt ON dt.id = d.device_type_id
WHERE d.is_archived = 0
ORDER BY dt.name COLLATE NOCASE, d.name COLLATE NOCASE, d.id
```

**After**:
```sql
SELECT d.id, d.module_id,
       COALESCE(m.display_name, 'Unlinked') AS device_type,
       d.name, d.model,
       d.current_version, d.latest_version,
       d.last_checked_at, d.last_success_at,
       d.last_check_status AS status, d.created_at, d.updated_at
FROM devices d
LEFT JOIN modules m ON m.id = d.module_id
WHERE d.is_archived = 0
ORDER BY COALESCE(m.display_name, 'ZZZ_Unlinked') COLLATE NOCASE,
         d.name COLLATE NOCASE, d.id
```

Changes:
- `JOIN device_types` → `LEFT JOIN modules`
- `dt.name` → `COALESCE(m.display_name, 'Unlinked')`
- ORDER BY uses `COALESCE(m.display_name, 'ZZZ_Unlinked')` to put unlinked devices at the bottom of the listing

#### Removed method: `get_or_create_device_type()`

```python
# REMOVED — no replacement
async def get_or_create_device_type(self, name: str, normalized_name: str) -> int:
    ...
```

Device creation now accepts `module_id` directly. The service layer reads `module_id` from the request payload; no lookup or normalization is needed.

#### Updated method: `create_device()`

**Before**:
```python
async def create_device(self, *, device_type_id: int, name: str, model: str, current_version: str) -> DeviceRecord:
    await self.execute(
        """INSERT INTO devices (device_type_id, name, model, current_version)
           VALUES (?, ?, ?, ?)""",
        (device_type_id, name, model, current_version),
    )
```

**After**:
```python
async def create_device(self, *, module_id: int, name: str, model: str, current_version: str) -> DeviceRecord:
    await self.execute(
        """INSERT INTO devices (module_id, name, model, current_version)
           VALUES (?, ?, ?, ?)""",
        (module_id, name, model, current_version),
    )
```

#### Updated method: `update_device()`

**Before**:
```python
async def update_device(self, device_id: int, *, device_type_id: int, name: str, model: str, current_version: str) -> DeviceRecord | None:
    await self.execute(
        """UPDATE devices
           SET device_type_id = ?, name = ?, model = ?, current_version = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ? AND is_archived = 0""",
        (device_type_id, name, model, current_version, device_id),
    )
```

**After**:
```python
async def update_device(self, device_id: int, *, module_id: int, name: str, model: str, current_version: str) -> DeviceRecord | None:
    await self.execute(
        """UPDATE devices
           SET module_id = ?, name = ?, model = ?, current_version = ?, updated_at = CURRENT_TIMESTAMP
           WHERE id = ? AND is_archived = 0""",
        (module_id, name, model, current_version, device_id),
    )
```

#### New method: `unlink_devices_for_module()`

Handles FK constraint before module deletion:

```python
async def unlink_devices_for_module(self, module_db_id: int) -> int:
    """Set module_id to NULL for all devices referencing the given module row."""
    row_count = await self.execute(
        "UPDATE devices SET module_id = NULL, updated_at = CURRENT_TIMESTAMP WHERE module_id = ?",
        (module_db_id,),
    )
    return row_count
```

### 6.2 `ScheduleRepository` — `schedules.py`

The `device_type_schedules` table is emptied by migration 007. After migration:

- `list_schedules()` returns an empty list (no rows to join).
- `upsert_schedule()`, `get_schedule()`, `record_run_*()` still accept `device_type_id: int` but operate on an empty table.
- These methods are retained as no-ops until a future epic implements per-module scheduling with a new `module_schedules` table.

**No query changes needed** in `schedules.py` for E022 — the table is simply empty.

### 6.3 `InventoryService` — `inventory.py`

#### Removed method: `_device_type_id()`

```python
# REMOVED
async def _device_type_id(self, device_type: str) -> int:
    return await self.repository.get_or_create_device_type(
        device_type, self.normalize_device_type(device_type),
    )
```

#### Removed method: `normalize_device_type()`

```python
# REMOVED
@staticmethod
def normalize_device_type(device_type: str) -> str:
    return " ".join(device_type.strip().lower().split())
```

#### Updated `DeviceInput` dataclass

**Before**:
```python
@dataclass(frozen=True)
class DeviceInput:
    name: str
    model: str
    device_type: str
    current_version: str
```

**After**:
```python
@dataclass(frozen=True)
class DeviceInput:
    name: str
    model: str
    module_id: str          # The modules.module_id string; service resolves to integer FK
    current_version: str
```

#### Updated `list_groups()` method

**Before** (groups by `device_type_id`):
```python
async def list_groups(self) -> tuple[DeviceGroup, ...]:
    devices = await self.repository.list_active_devices()
    groups: dict[int, list[DeviceRecord]] = {}
    names: dict[int, str] = {}
    for device in devices:
        groups.setdefault(device.device_type_id, []).append(device)
        names[device.device_type_id] = device.device_type
    return tuple(
        DeviceGroup(id=device_type_id, name=names[device_type_id], devices=tuple(group_devices))
        for device_type_id, group_devices in groups.items()
    )
```

**After** (groups by `module_id`, handles NULL/unlinked):
```python
async def list_groups(self) -> tuple[DeviceGroup, ...]:
    devices = await self.repository.list_active_devices()
    groups: dict[int | None, list[DeviceRecord]] = {}
    names: dict[int | None, str] = {}
    for device in devices:
        key = device.module_id  # None for unlinked
        groups.setdefault(key, []).append(device)
        names[key] = device.device_type  # "Unlinked" for NULL
    result: list[DeviceGroup] = []
    # Unlinked group last (None key sorts high)
    for key in sorted(groups.keys(), key=lambda k: (k is None, k or 0)):
        result.append(
            DeviceGroup(id=key or -1, name=names[key], devices=tuple(groups[key]))
        )
    return tuple(result)
```

#### Updated `create_device()` and `update_device()`

**Before**: `create_device` calls `_device_type_id(payload.device_type)` → `get_or_create_device_type` → returns `int` → passes to `repository.create_device(device_type_id=...)`.

**After**: `create_device` and `update_device` resolve the `module_id` string to `modules.id` (integer FK), validate that the module is `installed` and `valid`, then pass the integer FK to the repository:

```python
async def create_device(self, payload: DeviceInput) -> DeviceRecord:
    if not payload.module_id:
        raise ValueError("module_id is required to create a device")
    # Resolve module_id string → modules.id integer, validate installed + valid
    module_db_id = await self._resolve_module_db_id(payload.module_id)
    record = await self.repository.create_device(
        module_id=module_db_id,
        name=payload.name,
        model=payload.model,
        current_version=payload.current_version,
    )
    await self.repository.connection.commit()
    return record
```

### 6.4 `SchedulerService` — `scheduler.py`

The scheduler currently operates on `device_type_id` to group and check devices. After E022, it should operate on `module_id`:

| Current Method        | Uses                      | Post-E022 Target              |
|-----------------------|---------------------------|-------------------------------|
| `_run_scheduled_check`| `device.device_type_id`   | `device.module_id`            |
| `reschedule_type`     | `device_type_id: int`     | `module_db_id: int`           |
| `start`               | `schedule.device_type_id` | `schedule.device_type_id` (empty table) |

The scheduler changes are **deferred to a future epic** (per-module scheduling). E022 only empties the `device_type_schedules` table. The scheduler will start with zero jobs and the operator must reconfigure schedules through a new per-module scheduling UI.

### 6.5 `CheckService` — `checks.py`

The check service's `run_device_check` receives a `module_id` string (the `modules.module_id` value, not the DB row id). E022 does not change this interface — it was already a placeholder (`_resolve_module` returning `"default"`). The real resolution logic (resolve `module_id` from `device.module_id` FK → `modules.module_id` string) is part of check execution and out of scope for E022 data model changes.

---

## 7. API Surface Changes

### 7.1 `DevicePayload` — `routes/inventory.py`

**Before**:
```python
class DevicePayload(BaseModel):
    name: str = Field(min_length=1)
    model: str = Field(min_length=1)
    device_type: str = Field(alias="deviceType", min_length=1)
    current_version: str = Field(alias="currentVersion", min_length=1)
```

**After**:
```python
class DevicePayload(BaseModel):
    name: str = Field(min_length=1)
    model: str = Field(min_length=1)
    module_id: str = Field(alias="moduleId", min_length=1)
    current_version: str = Field(alias="currentVersion", min_length=1)
```

`DevicePayload.to_input()` maps `self.module_id` instead of `self.device_type`.

### 7.2 `DeviceResponse` — `routes/inventory.py`

**Before**:
```python
class DeviceResponse(BaseModel):
    id: int
    device_type_id: int = Field(alias="deviceTypeId")
    device_type: str = Field(alias="deviceType")
    ...
```

**After**:
```python
class DeviceResponse(BaseModel):
    id: int
    module_id: str | None = Field(alias="moduleId")
    device_type: str = Field(alias="deviceType")
    ...
```

`_device_response()` maps `record.module_id` instead of `record.device_type_id`.

### 7.3 `DeviceGroupResponse`

The `id` field for groups changes from `device_type_id` to `module_id` (or `-1` for "Unlinked"). The `name` field continues to hold the derived display name (including "Unlinked").

---

## 8. Edge Cases and Error Handling

| Scenario                                      | Behavior                                                       |
|-----------------------------------------------|----------------------------------------------------------------|
| Device created with valid module_id           | `module_id` is set; device appears under module's display_name |
| Device created with invalid module_id (no FK) | SQLite FK constraint error; 400 response from API              |
| Device created with NULL module_id            | App layer rejection: HTTP 422 with "module_id is required"     |
| Module deleted while devices reference it     | App sets `module_id = NULL` before `DELETE`; devices unlinked  |
| Module deleted, devices NOT pre-unlinked      | FK constraint error prevents DELETE; rollback entire operation |
| Migration backfill: no match found            | `module_id` remains NULL; device shows as "Unlinked"           |
| Migration backfill: ambiguous match (not possible) | `LIMIT 1` picks first match; deterministic per SQLite      |
| `device_types` table has FK from another table| Schedule rows deleted first; then DROP TABLE succeeds          |
| Operator views inventory, no modules installed| All devices show as "Unlinked" group                           |
| Operator views inventory, all devices linked  | No "Unlinked" group appears                                    |

---

## 9. Files Affected

| File                                                    | Change Type        |
|---------------------------------------------------------|--------------------|
| `backend/src/binocular/db/migrations/007_module_linking.sql` | **NEW**            |
| `backend/src/binocular/repositories/inventory.py`       | MODIFY             |
| `backend/src/binocular/repositories/modules.py`         | MODIFY (add pre-delete unlinking helper) |
| `backend/src/binocular/services/inventory.py`           | MODIFY             |
| `backend/src/binocular/routes/inventory.py`             | MODIFY             |
| `backend/src/binocular/services/scheduler.py`           | MODIFY (minor: handle empty schedule table) |
| `backend/src/binocular/services/checks.py`              | NO CHANGE (placeholder unchanged) |
| `backend/src/binocular/repositories/schedules.py`       | NO CHANGE (empty table, methods retained) |
| `backend/src/binocular/extensions/contract.py`          | NO CHANGE (module contract untouched) |

---

## 10. Key Design Decisions Summary

| ID  | Decision                                                                    | Rationale                                                                 |
|-----|-----------------------------------------------------------------------------|---------------------------------------------------------------------------|
| D1  | `module_id` is NULLABLE in schema but NOT NULL enforced at app layer        | Allows unlinked devices and safe column addition during migration         |
| D2  | `LEFT JOIN` modules instead of `JOIN`                                       | Devices with NULL `module_id` (unlinked) must still appear in inventory   |
| D3  | `COALESCE(m.display_name, 'Unlinked')` for device_type display              | Provides a meaningful label for unlinked devices in the UI                |
| D4  | No `ON DELETE SET NULL` on FK                                               | Application controls unlink before delete; enables audit/logging hook     |
| D5  | `device_type_schedules` emptied but table retained                          | Future per-module scheduling will repurpose or replace this table         |
| D6  | Migration drops `device_types` table immediately (not deferred)             | No remaining FKs; backup snapshot provides rollback safety                |
| D7  | Best-effort backfill with `LIMIT 1`                                         | Prevents ambiguity if multiple modules match; operator can reassign later |
| D8  | `module_id` stored on device row; `display_name` derived at query time      | Schema normalized; no stale cached names; module renames propagate instantly |
