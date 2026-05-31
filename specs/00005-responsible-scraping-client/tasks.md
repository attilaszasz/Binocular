# Tasks: Responsible Scraping Client

## Project Mode

Brownfield — extend the existing FastAPI backend package with a new scraping module and tests.

## Dependencies

- Setup before Foundational.
- Foundational before OBJ1-OBJ4 delivery tasks.
- OBJ2 and OBJ3 consume the client/error/diagnostic types from OBJ1.
- Polish validation depends on all delivery phases.

## Phase 1: Setup

- [X] T001 Update runtime HTTP dependency in backend/pyproject.toml
- [X] T002 Add scrape settings defaults and tests in backend/src/binocular/config.py and backend/tests/test_config.py

## Phase 2: Foundational

- [X] T003 Create scraping package exports in backend/src/binocular/scraping/__init__.py
- [X] T004 [P] Add scraping test scaffolding in backend/tests/test_scraping_client.py

## Phase 3: OBJ1 — Centralize Outbound HTTP Policy 🎯 MVP

- [X] T005 [OBJ1] {TR-001,TR-002,TR-008,TR-009} Implement client types and base fetch flow in backend/src/binocular/scraping/client.py [COMPLETES TR-001]
- [X] T006 [OBJ1] {TR-002,TR-009,TR-010} Add client header/timeout/no-live-network tests in backend/tests/test_scraping_client.py after:T005

## Phase 4: OBJ2 — Enforce Robots Decisions 🎯 MVP

- [X] T007 [OBJ2] {TR-003,TR-004} Implement robots policy cache in backend/src/binocular/scraping/robots.py after:T005
- [X] T008 [OBJ2] {TR-003,TR-004,TR-008} Integrate robots enforcement in backend/src/binocular/scraping/client.py after:T007 [COMPLETES TR-003]
- [X] T009 [OBJ2] {TR-003,TR-004,TR-010} Add robots allow/deny/missing tests in backend/tests/test_scraping_client.py after:T008 [COMPLETES TR-004]

## Phase 5: OBJ3 — Apply Per-Domain Pacing and Backoff 🎯 MVP

- [X] T010 [OBJ3] {TR-005,TR-009} Implement per-origin limiter in backend/src/binocular/scraping/rate_limit.py after:T005 [COMPLETES TR-005]
- [X] T011 [OBJ3] {TR-006,TR-007,TR-008} Integrate retry/backoff and Retry-After handling in backend/src/binocular/scraping/client.py after:T010 [COMPLETES TR-006]
- [X] T012 [OBJ3] {TR-006,TR-007,TR-010} Add rate-limit, retry, and Retry-After tests in backend/tests/test_scraping_client.py after:T011 [COMPLETES TR-007]

## Phase 6: OBJ4 — Expose Diagnostics

- [X] T013 [OBJ4] {TR-008,TR-009} Complete structured diagnostics coverage in backend/src/binocular/scraping/client.py and tests after:T012 [COMPLETES TR-008]

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T014 Run backend ruff, mypy, pytest coverage, and pip-audit from backend/
