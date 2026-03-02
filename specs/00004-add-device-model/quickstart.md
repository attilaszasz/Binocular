# Quickstart: Device Model Identifier

**Branch**: `00004-add-device-model` | **Date**: 2026-03-02

## Prerequisites

- Features 00001 (DB Schema), 00002 (Inventory API), and 00003 (Core Frontend) are implemented.
- Backend server running (`uvicorn backend.src.main:app --reload`).
- Frontend dev server running (`cd frontend && npm run dev`).

## Integration Scenarios

### Scenario 1: Create a device with a model identifier

1. Open the dashboard in a browser.
2. Click "Add Device" to open the device form.
3. Select a device type (e.g., "Sony Alpha Bodies").
4. Enter name "My A7IV", model "ILCE-7M4", version "3.01".
5. Submit — the device card appears with "ILCE-7M4" displayed below the device name.

**API equivalent**:
```bash
curl -X POST http://localhost:8000/api/v1/device-types/1/devices \
  -H "Content-Type: application/json" \
  -d '{"name": "My A7IV", "model": "ILCE-7M4", "current_version": "3.01"}'
```

### Scenario 2: Create a device without a model

1. Add a device with name "Old Camera" and version "1.0", leave the model field empty.
2. Submit — the device card shows "No model set" in a muted style below the name.

### Scenario 3: Edit a device to add/change model

1. Click "Edit" on an existing device without a model.
2. Enter "ILCE-7M4" in the Model field.
3. Save — the device card now shows the model below the name.

**API equivalent**:
```bash
curl -X PATCH http://localhost:8000/api/v1/devices/1 \
  -H "Content-Type: application/json" \
  -d '{"model": "ILCE-7M4"}'
```

### Scenario 4: Clear a device's model

1. Edit a device that has a model set.
2. Clear the Model field.
3. Save — the device card reverts to showing "No model set".

### Scenario 5: Confirm does not alter model

1. Have a device with model "ILCE-7M4" and a pending update (`latest_seen_version` set).
2. Click "Sync Local" (confirm action).
3. Verify `current_version` updates but the model remains "ILCE-7M4".

### Scenario 6: Migration — existing devices unaffected

1. After deploying the migration, verify all existing devices load without error.
2. Existing devices show "No model set" in the secondary label position.
3. No user intervention required.

## Verification Checklist

- [ ] New device with model: model persisted and displayed
- [ ] New device without model: created successfully, shows "No model set"
- [ ] Edit to add model: model saved and visible
- [ ] Edit to clear model: model removed, shows "No model set"
- [ ] Confirm action: model unchanged
- [ ] Existing devices: accessible with null model, no errors
- [ ] Whitespace trimming: "  ILCE-7M4  " stored as "ILCE-7M4"
- [ ] Max length: 101-character model rejected with validation error
