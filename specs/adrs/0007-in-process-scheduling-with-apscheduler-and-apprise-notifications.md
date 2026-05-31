---
adr_id: ADR-0007
status: accepted
date: 2026-05-31
tags: [scheduling, notifications, dependencies]
supersedes: []
superseded_by: ""
related_artifacts: [specs/prd.md#CAP-004, specs/prd.md#CAP-007]
---

# ADR-0007: In-process scheduling with APScheduler and Apprise notifications

## Status

Accepted.

## Context

Binocular must run firmware checks automatically on a per-device-type frequency (CAP-004) and dispatch notifications when a newer version is detected, supporting Email/SMTP and Gotify at launch (CAP-007). Both capabilities must work inside the single-container monolith (ADR-0001) with no external broker, queue, or extra services. Choices are needed for the scheduling mechanism and the notification dispatch mechanism.

## Decision Drivers

- Run scheduling and notifications fully in-process (no Redis/Celery/broker)
- Support configurable per-device-type intervals
- Support Email (SMTP) and Gotify now, with room to add channels cheaply
- Minimal dependencies and operational footprint
- Async-compatible with the FastAPI/Uvicorn runtime

## Considered Options

### Scheduling — Option A: APScheduler running inside the Python process

- **Pros**: No separate service; supports interval/cron jobs; jobs created/updated/removed dynamically from device-type settings.
- **Cons**: Scheduler lifecycle tied to the app process (acceptable for single instance).

### Scheduling — Option B: Celery + Redis beat

- **Pros**: Robust distributed scheduling.
- **Cons**: Requires Redis and worker containers — violates single-container, zero-infra constraint.

### Scheduling — Option C: External system cron invoking the app

- **Pros**: OS-native.
- **Cons**: Not portable across Docker/host; no in-app dynamic control; poor UX for per-device-type config.

### Notifications — Option A: Apprise library

- **Pros**: Abstracts dozens of services (Email, Gotify, plus Telegram/Discord/Slack/Pushover for free) behind one API; new channels essentially free.
- **Cons**: Adds a third-party dependency covering more surface than the launch requirement.

### Notifications — Option B: Hand-rolled SMTP + Gotify clients

- **Pros**: No extra dependency; full control over each channel.
- **Cons**: Per-channel code and ongoing maintenance for each new channel.

## Decision Outcome

Chosen option: **APScheduler for in-process scheduling** and **Apprise for notification dispatch**. APScheduler runs entirely within the application process — no broker or extra container — and supports the dynamic, per-device-type interval/cron jobs the product needs, fitting the single-container model. Apprise provides out-of-the-box Email (SMTP) and Gotify support (the launch requirement) plus a wide range of additional channels at no extra cost, behind a single dispatch API, minimizing notification maintenance.

## Consequences

### Positive

- Scheduling and notifications need zero external infrastructure.
- Per-device-type jobs are managed dynamically.
- New notification channels are essentially free via Apprise.

### Negative

- The scheduler shares the app process lifecycle (restart pauses jobs until next start).
- A missed window is retried on the next interval, not catch-up-replayed.

### Neutral

- Notification delivery success is validated end-to-end at release since no telemetry exists.
- Channel credentials are configured via Settings.

## Links

- specs/prd.md — CAP-004 (Automated Scheduled Checking)
- specs/prd.md — CAP-007 (Notification & Alerting)
- ADR-0001 (single-container monolith)
- ADR-0002 (Python/FastAPI)
