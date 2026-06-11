# Research: Automated Scheduled Checking

## APScheduler 3.x in-process scheduling
APScheduler 3.x offers an `AsyncIOScheduler` that runs directly within the asyncio event loop of a FastAPI application. Since the core system is a single-process monolith, an in-process scheduler is lightweight and avoids external worker dependencies.

## Restart Safety and Database Persistence
Because ADR-0004 restricts us to raw SQLite with `aiosqlite` and prohibits ORMs, we cannot use APScheduler's built-in SQLAlchemyJobStore. Instead, the schedule definitions (interval, last run, next run) are persisted in our own SQLite `schedules` table. On application startup, the `SchedulerService` queries the active schedules, computes their next execution times, and registers them with APScheduler's default in-memory job store. If the application restarts, the database state is read to re-populate the scheduler, ensuring restart safety.

## Run Resume Logic
To resume on next interval without missing or overlapping checks:
- At startup, for each schedule:
  - If `last_run` is null, run immediately (or schedule at `now`).
  - If `last_run` is set, compute `elapsed = now - last_run`.
  - If `elapsed >= interval_hours`, trigger the check immediately and schedule the next run at `now + interval_hours`.
  - Otherwise, schedule the next run at `last_run + interval_hours`.
- Upon successful execution of a module check, update `last_run` and `next_run` in the DB.
