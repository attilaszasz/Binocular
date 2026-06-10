# API Contract: Activity Logging & Visibility

This document describes the API endpoints, Pydantic schemas, and payload schemas for the Activity Logging & Visibility feature.

## 1. Endpoints

Exposes a query path to fetch paginated/filtered check and notification activities.

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| `GET` | `/api/v1/activity` | List rolling activity records | Optional Basic Auth |

## 2. API Schemas (Pydantic Models)

All camelCase key conventions are strictly maintained for compatibility with the frontend SPA.

```json
{
  "ActivityLogResponse": {
    "id": 142,
    "eventType": "check",
    "status": "failed",
    "deviceName": "Sony A7 IV",
    "moduleName": "sony_alpha",
    "message": "Scrape connection failed: DNS resolution timeout",
    "traceback": "Traceback (most recent call):\n  File \"/app/services/checks.py\", line 114...\nHTTPError: Host not found",
    "createdAt": "2026-06-01T17:05:00Z"
  }
}
```

## 3. Query Parameter Contracts

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | Integer | `100` | Maximum number of records to return (capped at 500) |
| `offset` | Integer | `0` | Pagination offset |
| `eventType` / `type` | String | `None` | Filter by `check` or `notification` |
| `status` | String | `None` | Filter by `success` or `failed` |

## 4. HTTP Responses

### 4.1 `200 OK`
Returned on a successful query, exposing a JSON array.

```json
[
  {
    "id": 142,
    "eventType": "check",
    "status": "failed",
    "deviceName": "Sony A7 IV",
    "moduleName": "sony_alpha",
    "message": "Scrape connection failed: DNS resolution timeout",
    "traceback": "Traceback (most recent call):\n  File \"/app/services/checks.py\", line 114...\nHTTPError: Host not found",
    "createdAt": "2026-06-01T17:05:00Z"
  }
]
```

### 4.2 `422 Unprocessable Entity`
Returned on invalid request payloads or malformed query types.

```json
{
  "detail": [
    {
      "loc": ["query", "limit"],
      "msg": "value is not a valid integer",
      "type": "type_error.integer"
    }
  ]
}
```
