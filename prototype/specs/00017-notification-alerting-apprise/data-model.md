# Data Model: Notification Channels

This document describes the schema, constraints, and migrations for persisting notification channel settings.

## Entity: NotificationChannel

The `notification_channels` table persists the configuration and enabled/disabled state of SMTP and Gotify alerting.

### Schema: `notification_channels`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique identifier for the channel configuration. |
| `type` | TEXT | NOT NULL UNIQUE | Channel type: `'smtp'` or `'gotify'`. One record per type. |
| `enabled` | INTEGER | NOT NULL DEFAULT 0 | 0 = disabled, 1 = enabled. |
| `config` | TEXT | NOT NULL | JSON string containing credentials, hosts, ports, tokens, and target addresses. |
| `created_at` | TEXT | NOT NULL DEFAULT CURRENT_TIMESTAMP | ISO8601 timestamp of creation. |
| `updated_at` | TEXT | NOT NULL DEFAULT CURRENT_TIMESTAMP | ISO8601 timestamp of last modification. |

### JSON Config Field Schemes

#### Email/SMTP Configuration Schema
```json
{
  "smtp_host": "smtp.example.com",
  "smtp_port": 587,
  "smtp_username": "user@example.com",
  "smtp_password": "my_secure_password",
  "smtp_use_tls": true,
  "mail_from": "binocular@example.com",
  "mail_to": "alerts@example.com"
}
```

#### Gotify Configuration Schema
```json
{
  "gotify_url": "https://gotify.example.com",
  "gotify_token": "AppSecureToken"
}
```

### Migration: `005_notification_channels.sql`

```sql
CREATE TABLE notification_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL UNIQUE CHECK (type IN ('smtp', 'gotify')),
    enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
    config TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```
