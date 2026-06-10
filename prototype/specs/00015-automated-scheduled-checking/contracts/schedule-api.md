# API Contract: Automated Scheduled Checking

## Endpoints

| Method | Path | Purpose | Request | Response |
|--------|------|---------|---------|----------|
| GET | `/api/v1/schedules` | List schedule settings and health for all device types | none | `ScheduleListResponse` |
| PUT | `/api/v1/schedules/device-types/{device_type_id}` | Upsert schedule settings for one device type | `ScheduleUpdateRequest` | `DeviceTypeScheduleResponse` |

## Types

### ScheduleUpdateRequest

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `enabled` | boolean | yes | Disabled schedules are persisted and unscheduled. |
| `intervalMinutes` | integer | yes | Positive bounded interval; server enforces min/max. |

### DeviceTypeScheduleResponse

| Field | Type | Notes |
|-------|------|-------|
| `deviceTypeId` | integer | Existing device type ID. |
| `deviceType` | string | Display name. |
| `enabled` | boolean | Current schedule setting. |
| `intervalMinutes` | integer | Persisted interval. |
| `nextRunAt` | string/null | Scheduler-derived next run when enabled. |
| `lastStartedAt` | string/null | Latest scheduled run start. |
| `lastCompletedAt` | string/null | Latest scheduled run completion. |
| `lastSuccessAt` | string/null | Latest fully successful scheduled run. |
| `lastFailureAt` | string/null | Latest failed or partially failed run. |
| `lastFailureReason` | string/null | Operator-facing diagnostic. |
| `lastSkipReason` | string/null | Overlap or missed-run diagnostic. |

### ScheduleListResponse

| Field | Type | Notes |
|-------|------|-------|
| `schedules` | `DeviceTypeScheduleResponse[]` | One row per configured or discovered device type. |

## Error Semantics

| Case | Response |
|------|----------|
| Device type not found | 404 `device_type_not_found` |
| Invalid interval | 422 validation error |
| Scheduler reschedule failure | 500 structured error and persisted schedule diagnostic when possible |