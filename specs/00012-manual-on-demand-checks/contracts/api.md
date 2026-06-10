# API Contract: Manual On-Demand Checks

Endpoints for triggering manual firmware checks on individual devices or bulk checking all devices.

## Endpoints

### 1. Trigger Single Device Check
* **Method**: `POST`
* **Path**: `/api/v1/checks/device/{device_id}`
* **Query Parameters**: None
* **Success Response**:
  * **Code**: `200 OK`
  * **Content-Type**: `application/json`
  * **Body**:
    ```json
    {
      "device_id": 1,
      "module_id": 2,
      "latest_version": "2.0.0",
      "current_version": "1.0.0",
      "has_update": true,
      "checked_at": "2026-06-10T19:50:00Z",
      "success": true,
      "error_message": null
    }
    ```
* **Error Response**:
  * **Code**: `404 Not Found`
  * **Body**:
    ```json
    {
      "detail": "Device 1 not found"
    }
    ```
  * **Code**: `422 Unprocessable Entity` (if module execution failed)
  * **Body**:
    ```json
    {
      "device_id": 1,
      "module_id": 2,
      "latest_version": null,
      "current_version": "1.0.0",
      "has_update": false,
      "checked_at": "2026-06-10T19:50:00Z",
      "success": false,
      "error_message": "Failed to load module file: [error details]"
    }
    ```

### 2. Trigger Bulk Checks
* **Method**: `POST`
* **Path**: `/api/v1/checks/bulk`
* **Query Parameters**: None
* **Success Response**:
  * **Code**: `200 OK`
  * **Content-Type**: `application/json`
  * **Body**:
    ```json
    [
      {
        "device_id": 1,
        "module_id": 2,
        "latest_version": "2.0.0",
        "current_version": "1.0.0",
        "has_update": true,
        "checked_at": "2026-06-10T19:50:00Z",
        "success": true,
        "error_message": null
      },
      {
        "device_id": 2,
        "module_id": 3,
        "latest_version": "1.1.0",
        "current_version": "1.1.0",
        "has_update": false,
        "checked_at": "2026-06-10T19:50:05Z",
        "success": true,
        "error_message": null
      }
    ]
    ```
