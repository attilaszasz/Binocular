# Quickstart: Inventory API

**Feature**: `00002-inventory-api` | **Plan**: [plan.md](plan.md)

---

## Prerequisites

- Python 3.11+
- Feature 00001 (Database Schema & Models) fully implemented
- `pyproject.toml` dependencies installed: `pip install -e ".[dev]"`

## Running the API Server

### From terminal

```bash
cd /path/to/binocular
uvicorn backend.src.main:app --reload --host 0.0.0.0 --port 8000
```

### From VS Code (F5)

1. Open the workspace in VS Code.
2. Select the **"Binocular: Debug API"** launch configuration.
3. Press **F5** — the server starts on `http://localhost:8000` with debugpy attached.
4. Set breakpoints anywhere in `backend/src/`.

The `.vscode/launch.json` configuration:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Binocular: Debug API",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "backend.src.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000"
      ],
      "cwd": "${workspaceFolder}",
      "env": {
        "BINOCULAR_DB_PATH": "${workspaceFolder}/data/binocular.db"
      },
      "console": "integratedTerminal"
    }
  ]
}
```

## Interactive API Documentation

Once the server is running, browse:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

All endpoints are grouped by tag: **Device Types**, **Devices**, **Actions**.

## Integration Scenarios

### Scenario 1: Complete Inventory Lifecycle

```bash
# 1. Create a device type
curl -X POST http://localhost:8000/api/v1/device-types \
  -H "Content-Type: application/json" \
  -d '{"name": "Sony Alpha Bodies", "firmware_source_url": "https://alphauniverse.com/firmware/"}'

# 2. Add a device under the type (use the returned device_type_id)
curl -X POST http://localhost:8000/api/v1/device-types/1/devices \
  -H "Content-Type: application/json" \
  -d '{"name": "Sony A7IV", "current_version": "3.01"}'

# 3. List all device types (with device counts)
curl http://localhost:8000/api/v1/device-types

# 4. List all devices (cross-type view)
curl http://localhost:8000/api/v1/devices

# 5. Update a device's notes
curl -X PATCH http://localhost:8000/api/v1/devices/1 \
  -H "Content-Type: application/json" \
  -d '{"notes": "Primary camera body"}'

# 6. Retrieve a single device (with derived status)
curl http://localhost:8000/api/v1/devices/1
```

### Scenario 2: Confirm Firmware Update

```bash
# Simulate: device has current=2.00, latest_seen=3.01 (set by scheduler)
# The scheduler would have called update_latest_version — for testing, use the DB directly.

# Confirm the update (one-click, no body)
curl -X POST http://localhost:8000/api/v1/devices/1/confirm

# Verify: current_version now matches latest_seen_version
curl http://localhost:8000/api/v1/devices/1
```

### Scenario 3: Safe Cascade Deletion

```bash
# Try to delete a device type with children (blocked)
curl -X DELETE http://localhost:8000/api/v1/device-types/1
# → 409: "Cannot delete: 1 device would also be deleted."

# Retry with explicit confirmation
curl -X DELETE "http://localhost:8000/api/v1/device-types/1?confirm_cascade=true"
# → 204 No Content
```

### Scenario 4: Filtering and Sorting

```bash
# Filter devices by type
curl "http://localhost:8000/api/v1/devices?device_type_id=1"

# Filter devices with pending updates
curl "http://localhost:8000/api/v1/devices?status=update_available"

# Sort by last checked (most recent first)
curl "http://localhost:8000/api/v1/devices?sort=-last_checked_at"
```

### Scenario 5: Bulk Confirm

```bash
# Confirm all devices with pending updates
curl -X POST http://localhost:8000/api/v1/devices/confirm-all

# Confirm only within a specific type
curl -X POST "http://localhost:8000/api/v1/devices/confirm-all?device_type_id=1"
```

## Running Tests

```bash
cd /path/to/binocular
pytest backend/tests/ -v
```

Tests use isolated temp-file SQLite databases — no shared state between test cases.
