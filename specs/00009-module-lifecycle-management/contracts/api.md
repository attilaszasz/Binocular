# API Contract: Module Lifecycle Management

Endpoints for listing, uploading, updating, and deleting extension modules.

## Endpoints

### 1. List Modules
* **Method**: `GET`
* **Path**: `/api/v1/modules`
* **Query Parameters**: None
* **Success Response**:
  * **Code**: `200 OK`
  * **Content-Type**: `application/json`
  * **Body**:
    ```json
    [
      {
        "id": 1,
        "name": "sony_alpha",
        "device_type": "camera",
        "version": "1.0.0",
        "author": "Official",
        "file_path": "/app/modules/sony_alpha.py",
        "is_official": true,
        "status": "active",
        "created_at": "2026-06-10T14:00:00Z"
      }
    ]
    ```

### 2. Upload Module
* **Method**: `POST`
* **Path**: `/api/v1/modules`
* **Query Parameters**:
  * `run_phase2` (boolean, optional, default: `false`)
* **Request Body**:
  * `Content-Type`: `multipart/form-data`
  * `file`: UploadFile (the `.py` module file)
* **Success Response**:
  * **Code**: `201 Created`
  * **Body**: `ModuleResponse` (the newly registered module)
* **Error Response**:
  * **Code**: `422 Unprocessable Entity` (for contract validation failures or syntax errors)
  * **Body**:
    ```json
    {
      "detail": "Module validation failed",
      "validation_result": {
        "valid": false,
        "phases": [
          {
            "phase": "ast",
            "passed": false,
            "checks": [
              {
                "name": "has_module_version",
                "passed": false,
                "message": "Missing required constant 'MODULE_VERSION'",
                "line": null,
                "fix_suggestion": "Add at module level: MODULE_VERSION = \"1.0.0\""
              }
            ]
          }
        ]
      }
    }
    ```

### 3. Update Module
* **Method**: `PUT`
* **Path**: `/api/v1/modules/{module_id}`
* **Request Body**:
  * `Content-Type`: `application/json`
  * **Body**:
    ```json
    {
      "status": "inactive"
    }
    ```
    *Note: If updating module file itself, operator can re-upload using POST with the same module name, or we can allow PUT to support file uploads.*
* **Success Response**:
  * **Code**: `200 OK`
  * **Body**: `ModuleResponse`

### 4. Delete Module
* **Method**: `DELETE`
* **Path**: `/api/v1/modules/{module_id}`
* **Success Response**:
  * **Code**: `204 No Content`
* **Error Response**:
  * **Code**: `404 Not Found` (module not found)
  * **Code**: `400 Bad Request` (module is currently linked to devices)
  * **Body**:
    ```json
    {
      "detail": "Cannot delete module: it is currently referenced by 2 active devices."
    }
    ```
