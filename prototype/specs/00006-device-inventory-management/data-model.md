# Data Model: Device Inventory Management

## Entities

| Entity | Purpose | Key Fields | Rules |
|--------|---------|------------|-------|
| Device Type | User-visible group for inventory and future module association | `id`, `name`, `normalized_name`, `created_at`, `updated_at` | `normalized_name` is trimmed/lowercase unique; display name preserves user casing. |
| Device | Owned offline hardware item | `id`, `device_type_id`, `name`, `model`, `current_version`, `latest_version`, `last_checked_at`, `last_success_at`, `last_check_status`, `is_archived`, `created_at`, `updated_at` | Current/latest versions are text; archived devices are hidden from active views. |
| Inventory Summary | Read model for grouped UI | device type, count, devices | Built from non-archived devices ordered by type/name. |
| Update Confirmation | Domain action that syncs recorded version | `device_id`, `latest_version`, `updated_at` | Allowed only when `latest_version` is non-empty. |

## Relationships

| From | To | Cardinality | Notes |
|------|----|-------------|-------|
| Device Type | Device | 1:* | A device belongs to exactly one type; empty types may exist only if retained for reuse. |
| Device | Update Confirmation | 1:* logical events | This epic updates the device row; E014 may later log events. |

## State Rules

| State | Trigger | Result |
|-------|---------|--------|
| Active | Create/update | Device appears in grouped inventory. |
| Archived | Delete action | Device is hidden from active inventory; identity remains in SQLite. |
| Never checked | New device | `last_check_status` is `never_checked`; latest fields are nullable. |
| Update available | Later detection writes latest version | UI can offer confirmation when latest differs from current. |
| Confirmed | Operator confirms update | `current_version = latest_version`, timestamps update. |

## Validation Rules

| Rule | Validation |
|------|------------|
| Required fields | `name`, `model`, `device_type.name`, and `current_version` must be non-empty after trimming. |
| Type reuse | Normalize device type by trimming and lowercasing before lookup/create. |
| Version storage | Never coerce versions to numeric values. |
| Confirmation | Reject confirmation when `latest_version` is null or empty. |
| Archive | Active inventory queries filter `is_archived = 0`. |