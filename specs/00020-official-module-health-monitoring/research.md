# Research: Official Module Health Monitoring

## Topic 1: SQLite Schema & Tracking
To track scraping failures, the `modules` table can be extended with `consecutive_failures` (INTEGER) and `last_success` (DATETIME). Using raw SQL updates with aiosqlite, counters can be updated safely using transactional queries.
Source: SQLite Documentation on ALTER TABLE.

## Topic 2: Alert State Transitions
To avoid notification fatigue, the system must trigger notification dispatch only on the state transition from healthy to failing (e.g., when `consecutive_failures` becomes exactly equal to the threshold). Subsequent failures should log activity but not dispatch duplicate notifications until the counter resets.
Source: Alerting Best Practices, Prometheus Alertmanager Design.
