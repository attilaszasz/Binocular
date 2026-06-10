# API Contract: Device Check Result

## Endpoint Summary

| Method | Path | Purpose | Auth | Request | Response |
|--------|------|---------|------|---------|----------|
| POST | `/api/v1/checks/devices/{device_id}` | Run one detection check for an active device through an installed module | Optional basic auth when enabled | `RunDeviceCheckRequest` | `CheckResultResponse` |

## RunDeviceCheckRequest

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `module_id` | string | yes | Installed module to run for this core comparison increment. |
| `source_url` | string or null | no | Overrides or supplements module input source URL. |
| `extra` | object string:string | no | Extra module input fields. Defaults to empty object. |

## CheckResultResponse

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `device_id` | integer | yes | Checked device ID. |
| `module_id` | string | yes | Module used for the check. |
| `status` | enum | yes | `up_to_date`, `update_available`, or `failed`. |
| `current_version` | string | yes | Version recorded before the check. |
| `latest_version` | string or null | yes | Latest version detected on success; null on unsafe failure. |
| `last_checked_at` | string | yes | Timestamp of this attempt. |
| `last_success_at` | string or null | yes | Timestamp of last successful comparable result. |
| `source_url` | string or null | yes | Source URL from request or module result. |
| `detail` | string or null | yes | Human-readable failure or module detail. |
| `diagnostics` | object | yes | Structured module/comparison diagnostics. |

## Error Responses

| Status | Code | Trigger |
|--------|------|---------|
| 404 | `device_not_found` | Device is missing or archived. |
| 404 | `module_not_found` | Requested module does not exist. |
| 409 | `module_not_runnable` | Module is disabled or not valid. |
| 500 | `check_failed` | Unexpected internal failure outside normal module failure handling. |

## Contract Notes

- Normal module failures return HTTP 200 with `status: failed` because the check completed and produced a visible failed result.
- The endpoint does not dispatch notifications or write activity-log history; those are downstream responsibilities.
- The service contract behind this endpoint is reusable by scheduled checks without requiring HTTP recursion.
