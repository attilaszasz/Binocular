---
adr_id: ADR-0010
status: accepted
date: 2026-06-12
tags: [configuration, settings, database, seeding, notifications]
supersedes: []
superseded_by: ""
related_artifacts: [specs/prd.md, specs/sad.md, specs/dod.md]
---

# ADR-0010: Environment-Variable Based Configuration and Database Seeding

## Status
accepted

## Context
Operators running Binocular in Docker containers need a standard way to pre-configure notification channels (SMTP and Gotify) and basic auth settings using environment variables, avoiding manual setup in the web UI. Currently, notification configurations are stored in the SQLite database (`notification_channels` table). If the environment variables are set in the container environment, the application should automatically apply these configurations at startup and seed/update the database so they are recognized by the UI and the notification service.

## Decision Drivers
- Ease of deployment: container deployment should support a fully automated, declarative config path using standard environment variables.
- User experience: the UI should reflect the configured state, displaying active channels as enabled and credentials as masked.
- Simplicity and backward compatibility: settings should be stored in a unified `Settings` model and synchronized cleanly on startup with the existing database schema.

## Considered Options
### Option A: Read from database only, ignore environment variables for notification channels
- Pros: Simple data flows; no synchronization logic needed.
- Cons: Fails user requirement to support environment variable configuration.

### Option B: Merge database and environment variables at runtime on every read
- Pros: No database writes needed on startup.
- Cons: Hard to represent in the UI correctly (since the UI gets values from database endpoints); makes configuration precedence complex.

### Option C: Sync/seed environment variables to the database on application startup
- Pros: Simple, unified source of truth (the database repository) for runtime operations; the UI and test routes automatically pick up the values; clean separation of concerns.
- Cons: Requires a startup sync hook, but we already have an startup seeder (`OfficialModuleSeeder`).

## Decision Outcome
Chosen option: **Option C: Sync/seed environment variables to the database on application startup** — This aligns with our zero-config and self-hosted principles, allowing declarative environment variables to seamlessly bootstrap the persistent database settings, while keeping the UI and runtime code unchanged.

## Consequences
### Positive
- Notification channels can be fully configured using standard Docker Compose environment variables.
- The UI properly displays the channels as enabled, and masks secret fields (`smtp_pass` and `app_token`) as `********`.
- Basic authentication state can be enabled/disabled via `BINOCULAR_AUTH_ENABLED`.

### Negative
- Database records for notification channels will be overwritten by container environment settings on startup if they are specified in the environment variables.

## Links
- PRD capability: CAP-007 (Notification & Alerting)
- PRD capability: CAP-009 (Self-Hosted Operability)
- SAD sections: Integration Strategy, Operations
