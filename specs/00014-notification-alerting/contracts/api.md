# API Contracts: Notification & Alerting

All endpoints reside under the `/api/v1` prefix.

## Endpoints

### 1. Get Notification Channels Configuration
- **Method**: `GET`
- **Path**: `/api/v1/notifications`
- **Description**: Retrieve current SMTP and Gotify configuration states (with password/tokens masked).
- **Request Headers**: None
- **Request Parameters**: None
- **Response (200 OK)**:
  ```json
  [
    {
      "type": "email",
      "enabled": true,
      "config": {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "user@gmail.com",
        "smtp_pass": "********",
        "smtp_use_tls": true,
        "from_email": "binocular@example.com",
        "to_email": "operator@example.com"
      }
    },
    {
      "type": "gotify",
      "enabled": false,
      "config": {
        "server_url": "https://gotify.example.com",
        "app_token": "********"
      }
    }
  ]
  ```

### 2. Update Notification Channel Configuration
- **Method**: `PUT`
- **Path**: `/api/v1/notifications`
- **Description**: Create or update the configuration for a specific channel type.
- **Request Body (JSON)**:
  ```json
  {
    "type": "email",
    "enabled": true,
    "config": {
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587,
      "smtp_user": "user@gmail.com",
      "smtp_pass": "my-real-secret-password",
      "smtp_use_tls": true,
      "from_email": "binocular@example.com",
      "to_email": "operator@example.com"
    }
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "type": "email",
    "enabled": true,
    "config": {
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587,
      "smtp_user": "user@gmail.com",
      "smtp_pass": "********",
      "smtp_use_tls": true,
      "from_email": "binocular@example.com",
      "to_email": "operator@example.com"
    }
  }
  ```
- **Response (422 Unprocessable Entity)**:
  ```json
  {
    "detail": [
      {
        "loc": ["body", "config", "smtp_port"],
        "msg": "value is not a valid integer",
        "type": "type_error.integer"
      }
    ]
  }
  ```

### 3. Test Notification Channel Configuration
- **Method**: `POST`
- **Path**: `/api/v1/notifications/test`
- **Description**: Dispatches a test notification with a provided (unsaved) configuration or a saved channel's configuration to verify if details are correct.
- **Request Body (JSON)**:
  ```json
  {
    "type": "gotify",
    "config": {
      "server_url": "https://gotify.example.com",
      "app_token": "my-real-secret-token"
    }
  }
  ```
- **Response (200 OK - Successful Delivery)**:
  ```json
  {
    "success": true,
    "message": "Test notification sent successfully."
  }
  ```
- **Response (400 Bad Request - Delivery Failure)**:
  ```json
  {
    "success": false,
    "message": "Apprise delivery failed: SMTP connection timed out."
  }
  ```
