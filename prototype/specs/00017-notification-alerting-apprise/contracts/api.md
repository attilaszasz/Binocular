# API Contracts: Notification Routing & Configuration

This document specifies the REST API endpoints for configuring notification channels and triggering test dispatches.

## Base Path: `/api/v1/notifications`

### 1. Get Notification Channel Configurations

Returns configurations for all supported channels (SMTP and Gotify). Sensitive configuration values (e.g., passwords and tokens) MUST be masked.

* **URL**: `/api/v1/notifications`
* **Method**: `GET`
* **Response: 200 OK**
  ```json
  [
    {
      "id": 1,
      "type": "smtp",
      "enabled": true,
      "config": {
        "smtpHost": "smtp.example.com",
        "smtpPort": 587,
        "smtpUsername": "user@example.com",
        "smtpPassword": "•"
      }
    }
  ]
  ```

### 2. Create or Update Channel Configuration

Creates or updates the configuration for a specific channel type.

* **URL**: `/api/v1/notifications/{channel_type}`
* **Method**: `PUT`
* **Request Payload**:
  * For SMTP:
    ```json
    {
      "enabled": true,
      "config": {
        "smtpHost": "smtp.example.com",
        "smtpPort": 587,
        "smtpUsername": "user@example.com",
        "smtpPassword": "raw_or_masked_password",
        "smtpUseTls": true,
        "mailFrom": "binocular@example.com",
        "mailTo": "alerts@example.com"
      }
    }
    ```
  * For Gotify:
    ```json
    {
      "enabled": true,
      "config": {
        "gotifyUrl": "https://gotify.example.com",
        "gotifyToken": "raw_or_masked_token"
      }
    }
    ```
* **Response: 200 OK**
  ```json
  {
    "id": 1,
    "type": "smtp",
    "enabled": true,
    "config": {
      "smtpHost": "smtp.example.com",
      "smtpPort": 587,
      "smtpUsername": "user@example.com",
      "smtpPassword": "•"
    }
  }
  ```
* **Response: 422 Unprocessable Entity** (Invalid input format)
  ```json
  {
    "detail": [
      {
        "loc": ["body", "config", "smtpPort"],
        "msg": "Input should be greater than or equal to 1",
        "type": "greater_than_equal"
      }
    ]
  }
  ```

### 3. Send Test Notification

Attempts to dispatch a test notification through the given channel configuration. If the request payload contains configuration fields, it will test using those fields without saving them first.

* **URL**: `/api/v1/notifications/{channel_type}/test`
* **Method**: `POST`
* **Request Payload** (Optional, identical to PUT payload if testing custom unsaved parameters):
  ```json
  {
    "config": {
      "smtpHost": "smtp.example.com",
      "smtpPort": 587,
      "smtpUsername": "user@example.com",
      "smtpPassword": "my_test_password"
    }
  }
  ```
* **Response: 200 OK** (Successful dispatch)
  ```json
  {
    "status": "success",
    "detail": "Test email successfully sent to alerts@example.com via smtp.example.com:587"
  }
  ```
* **Response: 400 Bad Request** (Failed dispatch)
  ```json
  {
    "status": "failed",
    "detail": "Connection timed out connecting to smtp.example.com:587"
  }
  ```
