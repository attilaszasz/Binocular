# API Contract Amendment: Device Model Identifier

**Branch**: `00004-add-device-model` | **Date**: 2026-03-02
**Amends**: [00002-inventory-api/contracts/openapi.yaml](../../00002-inventory-api/contracts/openapi.yaml)

This document specifies the changes to the existing Inventory API contract to support the `model` attribute on devices. No new endpoints are introduced. All changes are additive — existing clients that do not send or read `model` continue to work without modification.

---

## Schema Changes

### `DeviceCreateRequest` — add `model` property

```yaml
# Add to components/schemas/DeviceCreateRequest/properties:
model:
  type: string
  nullable: true
  maxLength: 100
  description: >
    Manufacturer's model identifier used for firmware page lookup
    (e.g., "ILCE-7M4" for Sony A7IV, "DC-GH6" for Panasonic GH6).
    Optional — omit or set to null for manual-tracking-only devices.
```

- **Required**: No — `model` is NOT added to the `required` list.
- **Validation**: `maxLength: 100`. Whitespace-only values are normalized to `null` by the server.

### `DeviceUpdateRequest` — add `model` property

```yaml
# Add to components/schemas/DeviceUpdateRequest/properties:
model:
  type: string
  nullable: true
  maxLength: 100
  description: >
    Manufacturer's model identifier. Set to null or omit to clear.
```

- Consistent with existing optional-update semantics: omitting the field means "don't change", sending `null` means "clear to null".

### `DeviceResponse` — add `model` property

```yaml
# Add to components/schemas/DeviceResponse/properties:
model:
  type: string
  nullable: true
  description: >
    Manufacturer's model identifier for firmware lookup. Null when not set.

# Add "model" to components/schemas/DeviceResponse/required list
```

- **Required in response**: Yes — always present (as a string value or `null`).
- Returned by ALL endpoints that return `DeviceResponse`: `createDevice`, `getDevice`, `updateDevice`, `listDevices`, `confirmDeviceUpdate`.

---

## Affected Endpoints (behavior unchanged, response shape extended)

| Endpoint | Change |
|---|---|
| `POST /api/v1/device-types/{id}/devices` | Accepts optional `model` in body; returns `model` in response |
| `GET /api/v1/devices` | Returns `model` in each device response |
| `GET /api/v1/devices/{id}` | Returns `model` in response |
| `PATCH /api/v1/devices/{id}` | Accepts optional `model` in body; returns `model` in response |
| `DELETE /api/v1/devices/{id}` | Unchanged (204 No Content) |
| `POST /api/v1/devices/{id}/confirm` | Returns `model` in response; MUST NOT alter `model` value (FR-007) |
| `POST /api/v1/devices/confirm-all` | Unchanged response shape (`BulkConfirmResponse`) |

---

## Error Behavior

### Model validation error

When `model` exceeds 100 characters:

```json
{
  "detail": "Model must be at most 100 characters.",
  "error_code": "VALIDATION_ERROR",
  "field": "model"
}
```

HTTP 422 — consistent with existing `VALIDATION_ERROR` responses.

### No new error codes

The `model` field does not introduce any new error codes. It uses the existing `VALIDATION_ERROR` code for length violations.

---

## Example Request/Response

### Create device with model

**Request**: `POST /api/v1/device-types/1/devices`
```json
{
  "name": "My A7IV",
  "current_version": "3.01",
  "model": "ILCE-7M4"
}
```

**Response**: `201 Created`
```json
{
  "id": 5,
  "device_type_id": 1,
  "device_type_name": "Sony Alpha Bodies",
  "name": "My A7IV",
  "model": "ILCE-7M4",
  "current_version": "3.01",
  "latest_seen_version": null,
  "last_checked_at": null,
  "notes": null,
  "status": "never_checked",
  "created_at": "2026-03-02T10:00:00.000Z",
  "updated_at": "2026-03-02T10:00:00.000Z"
}
```

### Create device without model

**Request**: `POST /api/v1/device-types/1/devices`
```json
{
  "name": "Sony A7RV",
  "current_version": "2.00"
}
```

**Response**: `201 Created` — `"model": null`

### Update device — add model

**Request**: `PATCH /api/v1/devices/5`
```json
{
  "model": "ILCE-7M4"
}
```

**Response**: `200 OK` — model updated, all other fields unchanged.

### Update device — clear model

**Request**: `PATCH /api/v1/devices/5`
```json
{
  "model": null
}
```

**Response**: `200 OK` — `"model": null`

### Confirm does not alter model

**Request**: `POST /api/v1/devices/5/confirm`

**Response**: `200 OK` — `"model": "ILCE-7M4"` (unchanged from before confirm).
