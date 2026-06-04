# API Contract: Inventory (Post-E022 Device-Module Linking Refactor)

**Epic**: E022 — Device-Module Linking & Refactor
**Spec**: `specs/00022-device-module-linking-refactor/spec.md`
**Base Path**: `/api/v1/inventory`
**Status**: Draft (design contract)

---

## 1. Source Files

| Layer    | File Path                                                        |
|----------|------------------------------------------------------------------|
| Backend  | `backend/src/binocular/routes/inventory.py`                      |
| Service  | `backend/src/binocular/services/inventory.py`                    |
| Repo     | `backend/src/binocular/repositories/inventory.py`                |
| Frontend | `frontend/src/api/inventory.ts`                                  |

---

## 2. Endpoint Contracts

### 2.1 GET /api/v1/inventory — List Inventory (Grouped)

Retrieve all active (non-archived) devices, grouped by their linked module's string identifier.

| Aspect       | Detail                                                                 |
|--------------|------------------------------------------------------------------------|
| Method       | `GET`                                                                  |
| Path         | `/api/v1/inventory`                                                     |
| Auth         | None (local self-hosted)                                                |
| Request Body | None                                                                   |

#### Response: `200 OK`

```json
{
  "groups": [
    {
      "moduleId": "sony-alpha-v2",
      "name": "Sony Alpha",
      "count": 3,
      "devices": [ /* DeviceResponse[] */ ]
    },
    {
      "moduleId": null,
      "name": "Unlinked",
      "count": 1,
      "devices": [ /* DeviceResponse[] */ ]
    }
  ]
}
```

| Field      | Type             | Description                                                        |
|------------|------------------|--------------------------------------------------------------------|
| `groups`   | `GroupResponse[]`| Array of device groups, ordered by module display name (unlinked last). |
| `groups[].moduleId` | `string \| null` | The module's unique string identifier (`modules.module_id`). `null` for the "Unlinked" group. |
| `groups[].name`     | `string`         | Display name derived from module `display_name`. `"Unlinked"` for the unlinked group. |
| `groups[].count`    | `integer`        | Number of devices in this group. |
| `groups[].devices`  | `DeviceResponse[]` | Devices belonging to this group. |

#### Error Responses

This endpoint has no expected application-level error responses. An inventory with no active (non-archived) devices returns `200 OK` with `{"groups": []}`. Unexpected server or database errors return `500 Internal Server Error`.

---

### 2.2 POST /api/v1/inventory — Create Device

Create a new device linked to an installed module.

| Aspect       | Detail                                                                 |
|--------------|------------------------------------------------------------------------|
| Method       | `POST`                                                                 |
| Path         | `/api/v1/inventory`                                                     |
| Content-Type | `application/json`                                                      |

#### Request Body

```json
{
  "name": "A7 IV #1",
  "model": "ILCE-7M4",
  "moduleId": "sony-alpha-v2",
  "currentVersion": "2.0"
}
```

| Field           | Type     | Required | Constraints            | Description                                    |
|-----------------|----------|----------|------------------------|------------------------------------------------|
| `name`          | `string` | yes      | `minLength: 1`         | User-assigned device label.                    |
| `model`         | `string` | yes      | `minLength: 1`         | Device model identifier.                       |
| `moduleId`      | `string` | yes      | `minLength: 1`         | The `modules.module_id` string of the module to link to. Must reference an installed, valid module. |
| `currentVersion`| `string` | yes      | `minLength: 1`         | Currently installed firmware version.          |

#### Response: `201 Created`

Returns a `DeviceResponse` object (see §3.2).

#### Error Responses

Validation proceeds in order: required/missing check → existence check → validity check.

| Status | Code                 | Condition                                                     |
|--------|----------------------|---------------------------------------------------------------|
| `400`  | `module_id_required` | `moduleId` is missing, empty, or whitespace-only in payload.  |
| `400`  | `module_not_found`   | `moduleId` does not reference an existing module.             |
| `400`  | `module_not_valid`   | Referenced module exists but is not `installed` + `valid`.    |
| `422`  | (FastAPI validation) | Payload shape is invalid (blank name, missing fields, etc.).  |

---

### 2.3 PATCH /api/v1/inventory/{deviceId} — Update Device

Update an existing device's name, model, module link, or current version.

| Aspect       | Detail                                                                 |
|--------------|------------------------------------------------------------------------|
| Method       | `PATCH`                                                                |
| Path         | `/api/v1/inventory/{deviceId}`                                          |
| Content-Type | `application/json`                                                      |

#### Path Parameters

| Parameter  | Type      | Description              |
|------------|-----------|--------------------------|
| `deviceId` | `integer` | ID of the device to update. Must be non-archived. |

#### Request Body

```json
{
  "name": "A7 IV #1",
  "model": "ILCE-7M4",
  "moduleId": "panasonic-lumix-v1",
  "currentVersion": "2.1"
}
```

Same shape as `POST` request body (see §2.2). All four fields are required (full replacement semantics).

#### Response: `200 OK`

Returns a `DeviceResponse` object (see §3.2).

#### Error Responses

Validation proceeds in order: required/missing check → existence check → validity check → device lookup.

| Status | Code                 | Condition                                                     |
|--------|----------------------|---------------------------------------------------------------|
| `400`  | `module_id_required` | `moduleId` is missing or empty.                               |
| `400`  | `module_not_found`   | `moduleId` does not reference an existing module.             |
| `400`  | `module_not_valid`   | Referenced module exists but is not `installed` + `valid`.    |
| `404`  | `device_not_found`   | Device with `deviceId` does not exist or is archived.         |
| `422`  | (FastAPI validation) | Payload shape is invalid.                                     |

---

### 2.4 DELETE /api/v1/inventory/{deviceId} — Archive Device

Soft-delete (archive) a device. Archived devices are excluded from inventory listing and check scheduling.

| Aspect       | Detail                                                                 |
|--------------|------------------------------------------------------------------------|
| Method       | `DELETE`                                                               |
| Path         | `/api/v1/inventory/{deviceId}`                                          |

#### Path Parameters

| Parameter  | Type      | Description              |
|------------|-----------|--------------------------|
| `deviceId` | `integer` | ID of the device to archive. |

#### Request Body

None.

#### Response: `204 No Content`

Empty body. Success is indicated by the status code.

#### Error Responses

| Status | Code               | Condition                                             |
|--------|--------------------|-------------------------------------------------------|
| `404`  | `device_not_found` | Device does not exist or is already archived.         |

---

### 2.5 POST /api/v1/inventory/{deviceId}/confirm-update — Confirm Firmware Update

Confirm that the operator has physically updated the device firmware. Syncs `currentVersion` to the previously detected `latestVersion`.

| Aspect       | Detail                                                                 |
|--------------|------------------------------------------------------------------------|
| Method       | `POST`                                                                 |
| Path         | `/api/v1/inventory/{deviceId}/confirm-update`                           |
| Content-Type | `application/json`                                                      |

#### Path Parameters

| Parameter  | Type      | Description              |
|------------|-----------|--------------------------|
| `deviceId` | `integer` | ID of the device to confirm. |

#### Request Body

```json
{
  "version": "3.0"
}
```

| Field     | Type     | Required | Description                                              |
|-----------|----------|----------|----------------------------------------------------------|
| `version` | `string` | yes      | The new firmware version now installed on the device.    |

#### Response: `200 OK`

Returns a `DeviceResponse` object (see §3.2) with `currentVersion` updated.

#### Error Responses

| Status | Code                    | Condition                                                   |
|--------|-------------------------|-------------------------------------------------------------|
| `404`  | `device_not_found`      | Device does not exist or is archived.                       |
| `409`  | `no_latest_version`     | Device has no `latestVersion` available to confirm against. |
| `422`  | (FastAPI validation)    | Payload shape is invalid.                                   |

---

## 3. Data Models

### 3.1 DevicePayload (Request — Pydantic)

```python
# backend/src/binocular/routes/inventory.py

class DevicePayload(BaseModel):
    """Create/update request payload (post-E022)."""

    name: str = Field(min_length=1)
    model: str = Field(min_length=1)
    module_id: str = Field(alias="moduleId", min_length=1)
    current_version: str = Field(alias="currentVersion", min_length=1)

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("name", "model", "module_id", "current_version")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            msg = "Field cannot be blank"
            raise ValueError(msg)
        return stripped

    def to_input(self) -> DeviceInput:
        return DeviceInput(
            name=self.name,
            model=self.model,
            module_id=self.module_id,
            current_version=self.current_version,
        )
```

| Field            | JSON Key         | Python Attr       | Type     | Constraints    |
|------------------|------------------|-------------------|----------|----------------|
| `name`           | `name`           | `name`            | `str`    | `min_length=1` |
| `model`          | `model`          | `model`           | `str`    | `min_length=1` |
| `module_id`      | `moduleId`       | `module_id`       | `str`    | `min_length=1` (resolved to `modules.id` integer FK by the service layer) |
| `current_version`| `currentVersion` | `current_version` | `str`    | `min_length=1` |

### 3.2 DeviceResponse (Response — Pydantic)

```python
# backend/src/binocular/routes/inventory.py

class DeviceResponse(BaseModel):
    """Inventory device response (post-E022)."""

    id: int
    module_id: str | None = Field(alias="moduleId")
    device_type: str = Field(alias="deviceType")
    name: str
    model: str
    current_version: str = Field(alias="currentVersion")
    latest_version: str | None = Field(alias="latestVersion")
    last_checked_at: str | None = Field(alias="lastCheckedAt")
    last_success_at: str | None = Field(alias="lastSuccessAt")
    status: Literal["never_checked", "check_failed", "update_available", "up_to_date"]
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)
```

| Field             | JSON Key          | Type                                                              | Description                                                      |
|-------------------|-------------------|-------------------------------------------------------------------|------------------------------------------------------------------|
| `id`              | `id`              | `int`                                                             | Stable device PK.                                                |
| `module_id`       | `moduleId`        | `string \| null`                                                  | The module's unique string identifier. `null` for unlinked devices. |
| `device_type`     | `deviceType`      | `string`                                                          | Display name derived from linked module (`modules.display_name`). `"Unlinked"` when `moduleId` is `null`. |
| `name`            | `name`            | `string`                                                          | User-assigned device label.                                      |
| `model`           | `model`           | `string`                                                          | Device model identifier.                                         |
| `current_version` | `currentVersion`  | `string`                                                          | Currently installed firmware version.                            |
| `latest_version`  | `latestVersion`   | `string \| null`                                                  | Latest firmware version detected by module check.                |
| `last_checked_at` | `lastCheckedAt`   | `string \| null` (ISO 8601)                                      | Timestamp of last check attempt.                                 |
| `last_success_at` | `lastSuccessAt`   | `string \| null` (ISO 8601)                                      | Timestamp of last successful check.                              |
| `status`          | `status`          | `"never_checked" \| "check_failed" \| "update_available" \| "up_to_date"` | Current check status.     |
| `created_at`      | `createdAt`       | `string` (ISO 8601)                                              | Creation timestamp.                                              |
| `updated_at`      | `updatedAt`       | `string` (ISO 8601)                                              | Last update timestamp.                                           |

### 3.3 DeviceGroupResponse (Response — Pydantic)

```python
# backend/src/binocular/routes/inventory.py

class DeviceGroupResponse(BaseModel):
    """Grouped inventory response item (post-E022)."""

    module_id: str | None = Field(alias="moduleId")
    name: str
    count: int
    devices: list[DeviceResponse]
```

| Field       | JSON Key    | Type              | Description                                                      |
|-------------|-------------|-------------------|------------------------------------------------------------------|
| `module_id` | `moduleId`  | `string \| null`  | The module's unique string identifier. `null` for the "Unlinked" group. |
| `name`      | `name`      | `string`          | Display name derived from module `display_name`. `"Unlinked"` for the unlinked group. |
| `count`     | `count`     | `int`             | Number of devices in this group.                                 |
| `devices`   | `devices`   | `DeviceResponse[]`| Devices belonging to this group.                                 |

### 3.4 InventoryResponse (Top-Level Wrapper — Pydantic)

```python
# backend/src/binocular/routes/inventory.py

class InventoryResponse(BaseModel):
    """Grouped inventory response (post-E022)."""

    groups: list[DeviceGroupResponse]
```

### 3.5 ConfirmUpdatePayload (Pydantic)

```python
# backend/src/binocular/routes/inventory.py

class ConfirmUpdatePayload(BaseModel):
    """POST /inventory/{device_id}/confirm-update request body."""

    version: str = Field(min_length=1)
```

---

## 4. TypeScript Type Definitions

```typescript
// frontend/src/api/inventory.ts

export type DeviceStatus =
  | 'never_checked'
  | 'check_failed'
  | 'update_available'
  | 'up_to_date';

export type InventoryDevice = {
  id: number;
  moduleId: string | null;
  deviceType: string;
  name: string;
  model: string;
  currentVersion: string;
  latestVersion: string | null;
  lastCheckedAt: string | null;
  lastSuccessAt: string | null;
  status: DeviceStatus;
  createdAt: string;
  updatedAt: string;
};

export type DeviceGroup = {
  moduleId: string | null;
  name: string;
  count: number;
  devices: InventoryDevice[];
};

export type InventoryResponse = {
  groups: DeviceGroup[];
};

export type DeviceInput = {
  name: string;
  model: string;
  moduleId: string;
  currentVersion: string;
};

export type ConfirmUpdateInput = {
  version: string;
};
```

| Type                   | Key Change (pre-E022 → post-E022)                                  |
|------------------------|---------------------------------------------------------------------|
| `InventoryDevice`      | `deviceTypeId: number` → `moduleId: string \| null`                |
| `DeviceGroup`          | `id: number` → `moduleId: string \| null`                          |
| `DeviceInput`          | `deviceType: string` → `moduleId: string`                          |
| `ConfirmUpdateInput`   | **NEW** — was previously no request body on confirm-update.        |

---

## 5. Error Response Schema

All error responses conform to the standard FastAPI/Starlette error shape and the existing module error convention.

### 5.1 Validation Errors (422)

Standard FastAPI `RequestValidationError`:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "moduleId"],
      "msg": "Field required",
      "input": { "name": "Foo" }
    }
  ]
}
```

### 5.2 Application Errors (400)

Follow the module error convention for consistency:

```json
{
  "code": "module_not_found",
  "detail": "Module 'nonexistent-module' is not installed"
}
```

```json
{
  "code": "module_not_valid",
  "detail": "Module 'sony-alpha-v2' is disabled or has not passed validation"
}
```

```json
{
  "code": "module_id_required",
  "detail": "moduleId is required to create or update a device"
}
```

### 5.3 Not Found (404)

```json
{
  "detail": "Device not found"
}
```

### 5.4 Conflict (409)

```json
{
  "detail": "No latest known version available"
}
```

---

## 6. Breaking Changes Summary

### 6.1 Field Mapping: Request Payloads

| Old Field (JSON)  | New Field (JSON)  | Type Change                    | Notes                                                       |
|--------------------|--------------------|--------------------------------|-------------------------------------------------------------|
| `deviceType`       | `moduleId`         | `string` → `string`            | Semantics changed: was free-text type name, now references a `modules.module_id` string. The old value accepted any string; the new value must match an installed, valid module. |

### 6.2 Field Mapping: Response Objects (`DeviceResponse` / `InventoryDevice`)

| Old Field (JSON)   | New Field (JSON)   | Type Change                     | Notes                                                      |
|---------------------|---------------------|---------------------------------|------------------------------------------------------------|
| `deviceTypeId`      | `moduleId`          | `number` → `string \| null`     | Was the integer PK of `device_types`. Now the string `modules.module_id` (or `null` for unlinked). |
| `deviceType`        | `deviceType`        | `string` → `string` (unchanged) | Still a display string, but now derived from `modules.display_name` via LEFT JOIN instead of `device_types.name`. Value `"Unlinked"` when `moduleId` is `null`. |

### 6.3 Field Mapping: Group Objects (`DeviceGroupResponse` / `DeviceGroup`)

| Old Field (JSON) | New Field (JSON) | Type Change                     | Notes                                                      |
|-------------------|-------------------|---------------------------------|------------------------------------------------------------|
| `id`              | `moduleId`        | `number` → `string \| null`     | Was `device_types.id`. Now `modules.module_id` string (or `null` for "Unlinked"). |
| `name`            | `name`            | `string` → `string` (unchanged) | Still a display string; derived from module `display_name`. Value `"Unlinked"` for the `null`-keyed group. |

### 6.4 Endpoint Changes

| Endpoint                                           | Pre-E022                                     | Post-E022                                                  |
|----------------------------------------------------|----------------------------------------------|------------------------------------------------------------|
| `POST /api/v1/inventory/{deviceId}/confirm-update` | No request body.                             | Accepts `{ "version": string }` to allow the operator to specify the new current version. |
| `DELETE /api/v1/inventory/{deviceId}`              | Returns `{ "success": true, "message": "..." }` | Returns `204 No Content` with empty body.                 |

All other endpoints (`GET /`, `POST /`, `PATCH /{id}`, `DELETE /{id}`) retain the same HTTP methods, paths, and status code semantics.

### 6.5 Removed Concepts

- **`deviceTypeId` field**: Eliminated from all API surfaces. Backend resolves module by the `moduleId` string; the integer FK is internal.
- **`DeviceType` entity**: The `device_types` DB table, `get_or_create_device_type()` repository method, `normalize_device_type()` service method, and all related types are removed. No `/device-types` endpoints ever existed publicly.
- **Free-text device type input**: Replaced by a module selector dropdown that only lists installed, valid modules.

---

## 7. Behavior Notes

- **Resolver**: The service layer resolves the `moduleId` string to `modules.id` (integer PK) for storage. Validation against `modules` table (`status='installed'` AND `validation_status='valid'`) occurs at this layer before persisting.
- **Unlinked devices**: Devices with `module_id = NULL` in the database (from migration failures or module deletion) are surfaced with `moduleId: null` and `deviceType: "Unlinked"`. They appear in a single "Unlinked" group sorted last.
- **Module deletion**: When a module is deleted, the application sets `module_id = NULL` on all referencing devices before issuing the `DELETE`. This is an application-level cascade, not a DB trigger.
- **Module rename**: If a module's `display_name` changes, all devices linked to it immediately reflect the new name on the next read (no cached copy on the device row).
- **No valid modules installed**: Device creation is rejected with `400 module_not_valid` guidance. The frontend should disable the submit button and show a message directing the operator to install and validate a module first.

---

## 8. Service-Layer Contract (`DeviceInput` dataclass)

```python
# backend/src/binocular/services/inventory.py

@dataclass(frozen=True)
class DeviceInput:
    """Validated inventory input (post-E022)."""
    name: str
    model: str
    module_id: str          # The modules.module_id string; service resolves to integer FK
    current_version: str
```

The `DeviceInput` dataclass carries the `moduleId` string. `InventoryService.create_device()` and `update_device()` are responsible for:
1. Looking up `modules.id` from `modules.module_id`.
2. Validating that the module is `installed` and `valid`.
3. Passing the integer FK to the repository layer.

---

## 9. Contract Versioning

| Version | Date       | Author   | Changes                                                              |
|---------|------------|----------|----------------------------------------------------------------------|
| 0.1.0   | 2026-06-04 | E022     | Initial contract replacing `deviceTypeId`/`deviceType` with module-based linking. |
