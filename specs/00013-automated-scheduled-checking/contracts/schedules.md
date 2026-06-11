# API Contracts: Schedules

This document specifies the REST API endpoints for viewing and updating automated scheduled checks.

## GET `/api/v1/schedules`

Retrieve a list of all module check schedules.

### Response

- **Status**: 200 OK
- **Content-Type**: `application/json`
- **Body**:

```json
[
  {
    "module_id": 1,
    "module_name": "Sony Alpha",
    "device_type": "Sony Cameras",
    "interval_hours": 24,
    "last_run": "2026-06-10T12:00:00Z",
    "next_run": "2026-06-11T12:00:00Z"
  }
]
```

## PUT `/api/v1/schedules`

Update the check schedule interval for a module.

### Request

- **Method**: PUT
- **Content-Type**: `application/json`
- **Body**:

```json
{
  "module_id": 1,
  "interval_hours": 12
}
```

### Response

- **Status**: 200 OK
- **Content-Type**: `application/json`
- **Body**:

```json
{
  "module_id": 1,
  "module_name": "Sony Alpha",
  "device_type": "Sony Cameras",
  "interval_hours": 12,
  "last_run": "2026-06-10T12:00:00Z",
  "next_run": "2026-06-10T23:00:00Z"
}
```

### Error Responses

- **400 Bad Request**: If `interval_hours` is less than 1.
- **404 Not Found**: If no module exists with the given `module_id`.
