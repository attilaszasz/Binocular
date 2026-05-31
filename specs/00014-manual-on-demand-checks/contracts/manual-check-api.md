# API Contract: Manual On-Demand Checks

## POST /api/v1/checks/devices/{deviceId}

Existing endpoint retained for single-device manual checks.

### Request

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `moduleId` | string | yes | Installed valid module to run. |
| `sourceUrl` | string/null | no | Optional source override passed to the module. |
| `extra` | object | no | String map passed to the module. |

### Response 200

`CheckResultResponse` from E009: `deviceId`, `moduleId`, `status`, `currentVersion`, `latestVersion`, `lastCheckedAt`, `lastSuccessAt`, `sourceUrl`, `detail`, `diagnostics`.

### Errors

| Status | Code | Meaning |
|--------|------|---------|
| 404 | `device_not_found` | Device is missing or archived. |
| 404 | `module_not_found` | Module does not exist. |
| 409 | `module_not_runnable` | Module is disabled or invalid. |

## POST /api/v1/checks/all

Run manual checks for all active devices with the selected installed module.

### Request

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `moduleId` | string | yes | Installed valid module to run for each device. |
| `sourceUrl` | string/null | no | Optional source override passed to each module run. |
| `extra` | object | no | String map passed to each module run. |
| `maxConcurrency` | integer/null | no | Optional bounded concurrency, clamped by server settings/defaults. |

### Response 200

| Field | Type | Notes |
|-------|------|-------|
| `results` | CheckResultResponse[] | One entry per eligible active device. |
| `total` | integer | Number of attempted devices. |
| `succeeded` | integer | Results with `up_to_date` or `update_available`. |
| `failed` | integer | Results with `failed`. |

### Errors

| Status | Code | Meaning |
|--------|------|---------|
| 404 | `module_not_found` | Module does not exist. |
| 409 | `module_not_runnable` | Module is disabled or invalid. |
| 422 | validation error | Payload shape is invalid. |
