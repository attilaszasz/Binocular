# Data Model: Update Detection & Comparison

## Entities

| Entity | Persistence | Key Fields | Relationships | Notes |
|--------|-------------|------------|---------------|-------|
| Device | Existing SQLite table `devices` | `id`, `device_type_id`, `model`, `current_version`, `latest_version`, `last_checked_at`, `last_success_at`, `last_check_status` | Belongs to `device_types`; check service reads and updates one active device | No new migration required for core status persistence. |
| Module | Existing SQLite table `modules` | `module_id`, `source_path`, `status`, `validation_status` | Loaded by `ModuleLoader`; executed by `ModuleRunner` | Check request supplies the module to execute for this core increment. |
| CheckResult | Typed service/API model | `device_id`, `module_id`, `status`, `current_version`, `latest_version`, `last_checked_at`, `last_success_at`, `source_url`, `detail`, `diagnostics` | Derived from Device + ModuleCheckResult + VersionComparison | Returned to callers; detailed event history is deferred to E014. |
| VersionComparison | Value object | `current`, `latest`, `is_newer`, `normalized_current`, `normalized_latest` | Used by CheckService | Invalid comparison maps to failed result. |

## State Transitions

| Input | Stored `last_check_status` | `latest_version` | `last_checked_at` | `last_success_at` |
|-------|----------------------------|------------------|-------------------|-------------------|
| Module success + latest newer | `update_available` | Detected latest | Updated to now | Updated to now |
| Module success + latest equal/older | `up_to_date` | Detected latest | Updated to now | Updated to now |
| Module failed | `check_failed` | Previous value retained | Updated to now | Previous value retained |
| Missing or unparseable version | `check_failed` | Previous value retained | Updated to now | Previous value retained |

## Validation Rules

| Rule | Enforcement |
|------|-------------|
| Device must exist and not be archived | `InventoryRepository.get_device()` returns active rows only |
| Module must exist, be installed, and be valid | `ModuleRepository.get_module()` plus service validation |
| Latest version must be non-empty for success | Check service converts missing latest to failed |
| Version comparison must be deterministic | Comparator returns newer/not-newer or raises comparison failure |
| Failure must preserve last successful check | Repository update method must not change `last_success_at` on failure |
