# Research Report — Device-Module Linking & Refactor

## 1. SQLite Foreign Key Migration with Column Removal

SQLite supports `ALTER TABLE ... DROP COLUMN` since 3.35.0 (2021), which internally rebuilds the table. Adding a column with a `REFERENCES` clause is supported only if the default is NULL. Foreign key enforcement requires `PRAGMA foreign_keys = ON` per connection. The existing migration runner wraps each migration SQL file in `BEGIN IMMEDIATE ... COMMIT` and auto-creates a backup snapshot before applying pending migrations.

**Recommended**: In a single migration file (e.g., `007_module_linking.sql`): add `module_id INTEGER REFERENCES modules(id)` with `DEFAULT NULL`, populate `module_id` from existing data (best-effort lookup via `device_type` → module `display_name`), then drop the old `device_type_id` column. After migration, the application layer should reject NULL `module_id` on device creation. Keep `PRAGMA foreign_keys = ON` — the runner's connection manager should already enable this or it should be enabled in the migration itself.

**Avoid**: Trying to add a NOT NULL column with a default in the same ALTER — SQLite adds it as NULL then requires separate `NOT NULL` enforcement. Do not drop `device_types` table in the same migration as the column removal, to allow a rollback window. Never skip the pre-migration backup snapshot.

Sources: https://www.sqlite.org/lang_altertable.html, https://www.sqlite.org/foreignkeys.html

## 2. UX: Replacing Free-Text Field with Entity Selector Dropdown

Replacing a free-text input with a `<select>` dropdown linked to an existing entity list changes the affordance from generative (type anything) to constrained (pick from available). For the device creation form, the module selector should present `display_name` as the visible label and use `module_id` as the value. The dropdown must be searchable if the module list grows beyond ~10 entries. Loading states matter: the selector should show a loading state while the module list is fetched, and an empty state ("No modules installed") if the list is empty.

**Recommended**: Use a native `<select>` with the existing `listModules()` API call. Filter to only `status: 'installed'` and `validationStatus: 'valid'` modules. Add a `<option value="">` placeholder like "Select a module..." as the default. Keep the select disabled or show a helper message when no valid modules exist, since device creation requires a module.

**Avoid**: Autocomplete/combobox with free-text fallback — defeats the purpose of the refactor. Do not populate the module list on every keystroke; fetch once and filter client-side. Avoid pre-selecting a module by default.

Sources: Existing App.tsx pattern, https://www.w3.org/WAI/tutorials/forms/select/

## 3. Derived Display Fields from Linked Entities

The device type is now read-only and derived from `modules.display_name`. This means the `DeviceRecord` returned by the repository should JOIN with `modules` to include the derived type. The frontend should display the device type as a read-only label, not an editable field. The current `DeviceRecord` already carries `device_type` as a JOIN result from `device_types` — the pattern is established, only the JOIN target changes from `device_types` to `modules`.

**Recommended**: Update the repository query to `JOIN modules m ON m.id = d.module_id` and select `m.display_name AS device_type`. The `DeviceRecord` dataclass keeps its `device_type: str` field unchanged. Group inventory devices by `device_type` (module `display_name`) rather than by `device_type_id`.

**Avoid**: Storing a materialized copy of the module's display name on the device row. Do not make the device type editable in the UI after creation.

Sources: Existing repositories/inventory.py pattern, https://www.sqlite.org/queryplanner.html

## 4. Clean Removal of Deprecated Entities and Endpoints

Removing the `DeviceType` entity means deleting: the `device_types` table (via migration), the `get_or_create_device_type` method on `InventoryRepository`, the `normalize_device_type` static method on `InventoryService`, any `/device-types` API routes, and frontend type definitions. The `DeviceInput` service dataclass changes from `device_type: str` to `module_id: int`.

**Recommended**: Remove in order: migration first (schema change), then backend (repository, service, routes), then frontend (API types, form inputs). Delete the `get_or_create_device_type` method entirely, remove `_device_type_id()` from the service layer, and update `create_device` / `update_device` to accept `module_id` directly.

**Avoid**: "Soft deprecation" — leaving dead code commented out. Do not remove the migration file itself (migrations are append-only). Do not delete the `device_types` table in a migration that also adds data — always add columns first, migrate data, then drop old columns/table in a subsequent migration or at least as a separate statement within the same migration for atomicity.

Sources: Existing codebase, https://martinfowler.com/articles/patterns-of-distributed-systems/

## 5. Backward Compatibility During Schema Refactor

SQLite does not support online schema changes or transactional DDL across multiple tables atomically. The existing migration runner creates a backup snapshot before applying pending migrations. For existing devices that have a `device_type` string but no `module_id`, the migration must perform a best-effort mapping: match the `device_types.normalized_name` against `modules.display_name` using case-insensitive comparison. Unmapped devices will have NULL `module_id` — the application must handle this gracefully.

**Recommended**: In the migration SQL: after adding the `module_id` column, populate it with `UPDATE devices SET module_id = (SELECT m.id FROM modules m JOIN device_types dt ON dt.id = devices.device_type_id WHERE lower(m.display_name) = lower(dt.name) LIMIT 1)`. Leave unmatched devices with NULL and present them in the UI with an "unlinked" badge and a prompt to re-assign. The migration runner's automatic backup ensures rollback safety.

**Avoid**: Assuming all existing devices can be perfectly mapped. Do not delete the `device_types` table in the same migration that adds `module_id`; keep it for one migration cycle as a safety net. Do not force module assignment during the migration itself.

Sources: Existing db/migrations.py backup infrastructure, https://www.sqlite.org/lang_altertable.html
