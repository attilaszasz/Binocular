# Quickstart: Module Interface Contract & Mock Execution

**Feature**: 00005-dummy-module  
**Date**: 2026-03-03

## Prerequisites

- Backend running (`uvicorn backend.src.main:app --reload`)
- Database migrated (automatic on startup)
- Seed data loaded (`python -m backend.scripts.seed_mock_data --reset`)

## Integration Verification Scenarios

### 1. List Registered Modules

After startup, the module loader scans the modules directory. Verify that the mock module is registered:

```bash
curl -s http://localhost:8000/api/v1/modules | python -m json.tool
```

**Expected**: Array containing one module with `filename: "mock_module.py"`, `is_active: true`, `supported_device_type: "mock_devices"`.

### 2. Trigger Module Reload

Manually trigger a re-scan of the modules directory:

```bash
curl -s -X POST http://localhost:8000/api/v1/modules/reload | python -m json.tool
```

**Expected**: Response with `loaded_count: 1`, `error_count: 0`, and the full module list.

### 3. Execute a Firmware Check (Mock Module)

First, ensure a device type linked to the mock module exists with a device:

```bash
# Create a "Mock Devices" device type linked to the mock module (module_id from step 1)
curl -s -X POST http://localhost:8000/api/v1/device-types \
  -H "Content-Type: application/json" \
  -d '{"name": "Mock Devices", "firmware_source_url": "https://example.com/firmware", "extension_module_id": 1, "check_frequency_minutes": 360}' | python -m json.tool

# Create a device under that type
curl -s -X POST http://localhost:8000/api/v1/device-types/5/devices \
  -H "Content-Type: application/json" \
  -d '{"name": "Mock Camera A", "current_version": "1.0.0", "model": "MOCK-001"}' | python -m json.tool

# Execute a firmware check
curl -s -X POST http://localhost:8000/api/v1/devices/8/check | python -m json.tool
```

**Expected**: `outcome: "success"`, `latest_version` contains a deterministic dummy version (e.g., `"2.0.0"`).

### 4. Execute Check — Model Not Found Path

Create a device with a model that triggers the "not found" path in the mock module:

```bash
curl -s -X POST http://localhost:8000/api/v1/device-types/5/devices \
  -H "Content-Type: application/json" \
  -d '{"name": "Mock Unknown", "current_version": "1.0.0", "model": "MOCK-NOTFOUND"}' | python -m json.tool

curl -s -X POST http://localhost:8000/api/v1/devices/9/check | python -m json.tool
```

**Expected**: `outcome: "error"`, `error_description` contains "Validation failed: latest_version is required".

### 5. Verify Check History

After executing checks, verify that check history entries were recorded:

```bash
curl -s http://localhost:8000/api/v1/devices/8 | python -m json.tool
```

**Expected**: `last_checked_at` is populated, `latest_seen_version` matches the mock module output.

### 6. Module Validation Error Path

Place a broken module file in the modules directory and trigger reload:

```bash
echo "# Missing check_firmware function" > /app/modules/broken_module.py
curl -s -X POST http://localhost:8000/api/v1/modules/reload | python -m json.tool
```

**Expected**: The broken module appears in the list with `is_active: false` and `last_error` describing the missing function. The mock module remains active and unaffected.

## Smoke Test Sequence

1. Start the application → modules directory created, mock module loaded
2. `GET /api/v1/modules` → mock module listed as active
3. Run seed script → device types and devices created, "Mock Devices" type linked to mock module
4. `POST /api/v1/devices/{id}/check` → success result with dummy version
5. `POST /api/v1/modules/reload` → re-scan succeeds, registry updated
6. Place a broken `.py` file → reload → broken module inactive, mock module unaffected
