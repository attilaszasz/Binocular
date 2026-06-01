# Research: Automated Scheduled Checking
> E011 | 2026-05-31 | Inform scheduler architecture and validation

## Scheduler Ownership
- **Decision**: Use one in-process APScheduler owned by the FastAPI lifespan.
- **Rationale**: Binocular supports a single-process container, and APScheduler job stores are not safe for multi-process coordination.
- **Rejected**: External workers or every-worker schedulers, because they violate self-contained deployment or duplicate jobs.
- **Pitfalls**: Do not imply multi-worker Uvicorn can safely run one scheduler per worker.
- **Sources**: https://apscheduler.readthedocs.io/en/3.x/faq.html, https://fastapi.tiangolo.com/deployment/server-workers/

## Durable Schedule State
- **Decision**: Store schedule configuration in SQLite and rebuild interval jobs on startup.
- **Rationale**: SQLite remains the product state source while APScheduler is a derived runtime mechanism.
- **Rejected**: APScheduler persistent job stores as product state, because serialization and duplicate IDs add complexity.
- **Pitfalls**: Persist before rescheduling so restart behavior matches the last saved UI state.
- **Sources**: https://apscheduler.readthedocs.io/en/3.x/userguide.html

## Missed Windows
- **Decision**: Coalesce runtime overlaps and do not replay downtime backlog.
- **Rationale**: One next-window retry protects polite scraping and avoids bursty catch-up behavior.
- **Rejected**: Running every missed interval after restart, because it can overload vendor pages.
- **Pitfalls**: Record skipped overlaps visibly so no run disappears silently.
- **Sources**: https://apscheduler.readthedocs.io/en/3.x/userguide.html

## Summary
| Topic | Decision | Rationale |
|-------|----------|-----------|
| Scheduler Ownership | Lifespan-owned APScheduler | Matches single-process deployment |
| Durable Schedule State | SQLite source of truth | Keeps all state backup-able |
| Missed Windows | No backlog replay | Prevents scraping bursts |

## Sources Index
| URL | Topic | Fetched |
|-----|-------|---------|
| https://apscheduler.readthedocs.io/en/3.x/faq.html | Scheduler Ownership | 2026-05-31 |
| https://apscheduler.readthedocs.io/en/3.x/userguide.html | Durable Schedule State, Missed Windows | 2026-05-31 |
| https://fastapi.tiangolo.com/deployment/server-workers/ | Scheduler Ownership | 2026-05-31 |