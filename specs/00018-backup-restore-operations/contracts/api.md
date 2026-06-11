# API Contract: Backup Operations

Endpoints for triggering manual database backups.

## Endpoints

### 1. Trigger Manual Database Backup
* **Method**: `POST`
* **Path**: `/api/v1/backups/trigger`
* **Query Parameters**: None
* **Success Response**:
  * **Code**: `200 OK`
  * **Content-Type**: `application/json`
  * **Body**:
    ```json
    {
      "success": true,
      "backup_file": "binocular_backup_20260611_134000.db"
    }
    ```
* **Error Response**:
  * **Code**: `500 Internal Server Error` (if backup creation fails, e.g. disk full)
  * **Body**:
    ```json
    {
      "detail": "Backup failed: [error details]"
    }
    ```
