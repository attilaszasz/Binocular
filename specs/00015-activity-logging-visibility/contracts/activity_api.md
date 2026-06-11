# API Contract: Activity Log

Defines the FastAPI REST endpoints for querying the activity log.

## Endpoints

### 1. GET `/api/v1/activity`
Retrieves a paginated, filtered list of activity log entries.

#### Request

**Query Parameters:**
- `level` (string, optional): Filter by log level (`INFO`, `WARNING`, `ERROR`).
- `category` (string, optional): Filter by log category (`check`, `notification`, `system`).
- `device_id` (integer, optional): Filter by device ID.
- `limit` (integer, optional, default: `50`, max: `100`): Pagination limit.
- `offset` (integer, optional, default: `0`): Pagination offset.

#### Response

- **Status**: `200 OK`
- **Body Schema**:
```json
{
  "items": [
    {
      "id": 12,
      "timestamp": "2026-06-11T08:20:00Z",
      "level": "INFO",
      "category": "check",
      "message": "Update check completed: Sony Alpha (no updates)",
      "device_id": 3,
      "device_name": "My Sony A7IV",
      "module_name": "sony_alpha",
      "traceback": null
    }
  ],
  "total": 1
}
```
*(Note: `device_name` is derived via SQL JOIN with the `devices` table to show it in the UI table directly without N+1 requests.)*

#### Error Responses

- **Status**: `422 Unprocessable Entity`
  - Returned when query parameters fail Pydantic validation (e.g., negative offset/limit, invalid level/category).
