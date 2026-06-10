# Data Model: Manual On-Demand Checks

## Entities

| Entity | Persistence | Key Fields | Relationships | Notes |
|--------|-------------|------------|---------------|-------|
| CheckResult | Existing device status fields | `device_id`, `module_id`, `status`, versions, timestamps, diagnostics | Device + module execution | Reused from E009 service/API contract. |
| ManualCheckRequest | Transient API payload | `module_id`, `source_url`, `extra` | Targets one device or all active devices | No new table. |
| ManualCheckBatch | Transient API response | `results`, `total`, `succeeded`, `failed` | Collection of `CheckResult` | Represents all-device manual execution. |

## State Transitions

| Trigger | From | To | Persistence |
|---------|------|----|-------------|
| Successful newer check | any active device | `update_available` | `latest_version`, `last_checked_at`, `last_success_at`, `last_check_status` |
| Successful equal/older check | any active device | `up_to_date` | same success fields |
| Failed manual check | any active device | `check_failed` | `last_checked_at`, `last_check_status`; preserve `last_success_at` |
| Empty all-device request | no eligible devices | empty batch | no write |

## Validation Rules

| Rule | Enforcement |
|------|-------------|
| Only active devices are checked | `InventoryRepository.get_device()` and `list_active_devices()` filter archived rows. |
| Bulk results are independent | Service catches per-device domain failures as `CheckResult` values. |
| No external persistence is introduced | Batch response is computed from E009 results and not stored separately. |
