# Tasks: Responsible Scraping Client

**Input**: Design documents from `specs/00005-responsible-scraping-client-central-polite/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md`

## Project Mode

`Brownfield`

## Brownfield Notes

- Existing flows touched: `backend/src/binocular/app.py`
- Compatibility or migration concerns: Zero database persistence, in-memory state only
- Regression focus: Application starts cleanly and `/healthz` remains functional

---

## Phase 1: OBJ1 - ScrapeClient Core & Lifespan (Priority: P1) 🎯 MVP

- [X] T001 [P] [OBJ1] {TR-001,TR-002,TR-008} Implement ScrapeClient exceptions and base client class in backend/src/binocular/scraping/client.py → exports: ScrapeClient, ScrapeError
- [X] T002 [OBJ1] {TR-009} Register scrape client in app lifespan in backend/src/binocular/app.py after:T001 ← T001:ScrapeClient
- [X] T003 [OBJ1] {TR-001,TR-002,TR-008} [COMPLETES TR-001,TR-002,TR-008] Write unit tests for core client features in backend/tests/scraping/test_client.py after:T002 ← T001:ScrapeClient

---

## Phase 2: OBJ2 - Robots.txt Enforcement (Priority: P1) 🎯 MVP

- [X] T004 [P] [OBJ2] {TR-003,TR-004} Implement RobotsChecker with async fetch and cache in backend/src/binocular/scraping/robots.py → exports: RobotsChecker
- [X] T005 [OBJ2] {TR-005} Integrate RobotsChecker into ScrapeClient in backend/src/binocular/scraping/client.py after:T004 ← T004:RobotsChecker
- [X] T006 [OBJ2] {TR-003,TR-004,TR-005} [COMPLETES TR-003,TR-004,TR-005] Write tests for robots.txt rules compliance in backend/tests/scraping/test_robots.py after:T005 ← T004:RobotsChecker

---

## Phase 3: OBJ3 - Per-Origin Rate Limiting & Backoff (Priority: P1) 🎯 MVP

- [X] T007 [P] [OBJ3] {TR-006} Implement RateLimiter using memory pacing dict in backend/src/binocular/scraping/rate_limit.py → exports: RateLimiter
- [X] T008 [OBJ3] {TR-007} Integrate RateLimiter and backoff retries in backend/src/binocular/scraping/client.py after:T007 ← T007:RateLimiter
- [X] T009 [OBJ3] {TR-006,TR-007} [COMPLETES TR-006,TR-007] Write tests for pacing delays and backoff retries in backend/tests/scraping/test_rate_limit.py after:T008 ← T007:RateLimiter

---

## Dependencies

Setup (if present) → Foundational (if present) → Delivery Work Items (by priority) → Polish (if present)

- Tasks marked `[P]` can run in parallel within their phase.
- Tasks with `after:T###` depend on the referenced task — the implementing agent must verify the dependency is `[X]` before executing.
- A task with `after:T###` or `← T###:Symbol` must not be `[P]`-batched with the referenced task.
