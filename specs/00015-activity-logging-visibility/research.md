# Research: Size-Bounded Activity Logging & Visibility

This document outlines design patterns, tech stack recommendations, and database strategies for implementing a size-bounded activity log persisted in SQLite and displayed in the frontend.

## Size-Bounded Log Retention in SQLite
In self-hosted applications, unbounded logs will slowly grow and exhaust disk space. To prevent this, rolling retention is enforced.
- **Pruning Strategy**: When inserting a new record, prune old entries if the count exceeds a predefined limit (e.g., 1000 records). 
- **Query Optimization**: A post-insert or pre-insert hook deletes oldest entries using a subquery:
  ```sql
  DELETE FROM activity_log 
  WHERE id NOT IN (
      SELECT id FROM activity_log 
      ORDER BY created_at DESC, id DESC 
      LIMIT 1000
  );
  ```
  An index on `(created_at, id)` ensures this cleanup query runs efficiently.

## API Design & Filtering
- **Endpoint**: `GET /api/v1/activity`
- **Query Parameters**:
  - `level`: Filter by log severity (`INFO`, `WARNING`, `ERROR`).
  - `category`: Filter by source/event category (`check`, `notification`, `system`).
  - `device_id`: Filter by a specific device.
  - `limit`: Maximum records to return (default 50, max 100).
  - `offset`: Pagination offset.
- **Response Shape**: Returns a JSON object with a list of log entries and a total count for pagination:
  ```json
  {
    "items": [
      {
        "id": 1,
        "timestamp": "2026-06-11T08:20:00Z",
        "level": "INFO",
        "category": "check",
        "message": "Update check completed for Sony Alpha",
        "device_id": 3,
        "module_name": "sony_alpha",
        "traceback": null
      }
    ],
    "total": 120
  }
  ```

## Frontend Logs Viewer
- **UI Components**:
  - **FilterBar**: Selectors for `level`, `category`, and a clear filter button.
  - **LogTable**: Paginated list showing timestamp, level (with colored badges), category, message, and device name (derived from `device_id`).
  - **TracebackPanel**: A slide-out sheet or collapsible panel to inspect stack traces for error logs.
