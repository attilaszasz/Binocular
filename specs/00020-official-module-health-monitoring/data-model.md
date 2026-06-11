# Data Model: Official Module Health Monitoring

## Database Schema Extensions

We extend the `modules` table to track consecutive failure counts and last successful check times.

### Table: `modules`

| Column | Type | Constraints | Default | Description |
|--------|------|-------------|---------|-------------|
| `consecutive_failures` | INTEGER | NOT NULL | 0 | Count of consecutive failed check runs since last success. |
| `last_success` | TEXT | NULL | NULL | ISO8601 timestamp of the last successful check run. |

## Migrations

### `0007_module_health.sql`

```sql
-- Migration 0007: Module health tracking fields
ALTER TABLE modules ADD COLUMN consecutive_failures INTEGER NOT NULL DEFAULT 0;
ALTER TABLE modules ADD COLUMN last_success TEXT NULL;
```
