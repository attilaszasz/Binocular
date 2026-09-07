# Tasks: Source-Aware HTTP Pacing

## Phase 1: Foundational (Cross-Work-Item Blockers)

- [X] T001 Create/test clock, sleep, jitter, transport, barrier, and trace APIs in backend/tests/scraping/{conftest,test_conftest}.py

## Phase 2: Objective 1 - Enforce Source-Aware Pacing (Priority: P1) 🎯 MVP

- [X] T002 [OBJ1] {TR-001} [COMPLETES TR-001] Test/implement OriginKey in backend/{tests/scraping/test_rate_limit.py,src/binocular/scraping/rate_limit.py} after:T001
- [X] T003 [OBJ1] {TR-002} [COMPLETES TR-002] Test/implement robots ownership/TTL/LRU in backend/{tests/scraping/test_robots.py,src/binocular/scraping/{robots,rate_limit}.py} after:T002
- [X] T004 [OBJ1] {TR-003} [COMPLETES TR-003] Test/implement Crawl-delay floor in backend/{tests/scraping/test_robots.py,src/binocular/scraping/robots.py} after:T003
- [X] T005 [OBJ1] {TR-004} [COMPLETES TR-004] Test/implement reservation order, updates, and caps in backend/{tests/scraping/test_rate_limit.py,src/binocular/scraping/rate_limit.py} after:T004
- [X] T006 [OBJ1] {TR-005} [COMPLETES TR-005] Test/implement attempts, backoff, Retry-After in backend/{tests/scraping/test_client.py,src/binocular/scraping/client.py} after:T005
- [X] T007 [OBJ1] {TR-014} [COMPLETES TR-014] Test/implement safe bounded redirects in backend/{tests/scraping/test_client.py,src/binocular/scraping/client.py} after:T006

## Phase 3: Objective 2 - Bound Check Lifecycles (Priority: P1) 🎯 MVP

- [X] T008 [OBJ2] {TR-006} [COMPLETES TR-006] Test/implement deadline in backend/{tests/scraping/test_scope.py,src/binocular/scraping/{scope,client}.py} after:T007
- [X] T009 [OBJ2] {TR-007} [COMPLETES TR-007] Test/implement credit/cap/rollback in backend/{tests/scraping/test_scope.py,src/binocular/scraping/{scope,rate_limit}.py} after:T008
- [X] T010 [OBJ2] {TR-008} [COMPLETES TR-008] Test/implement expiry/start in backend/{tests/scraping/test_scope.py,src/binocular/scraping/{scope,client}.py} after:T009
- [X] T011 [OBJ2] {TR-009} [COMPLETES TR-009] Test cancel in backend/tests/extensions/test_runner.py; implement in backend/src/binocular/{extensions/runner.py,scraping/scope.py} after:T010
- [X] T012 [OBJ2] {TR-021} [COMPLETES TR-021] Test/implement terminal cleanup in backend/{tests/scraping/test_scope.py,src/binocular/scraping/scope.py} after:T011
- [X] T013 [OBJ2] {TR-022} [COMPLETES TR-022] Test bounded counts in backend/tests/scraping/; reclaim in backend/src/binocular/scraping/{rate_limit,robots,scope}.py after:T012

## Phase 4: Objective 3 - Prove Compatibility Deterministically (Priority: P1) 🎯 MVP

- [X] T014 [OBJ3] {TR-010} [COMPLETES TR-010] Test 403/5xx/fetch-failure denial and other-4xx allowance in backend/tests/scraping/test_robots.py after:T013
- [X] T015 [OBJ3] {TR-011} [COMPLETES TR-011] Test compatibility/isolation in backend/tests/{scraping/test_client.py,extensions/test_runner.py} after:T014
- [X] T016 [OBJ3] {TR-012} [COMPLETES TR-012] Add exact policy/lifecycle boundary tests in backend/tests/scraping/ after:T015
- [X] T017 [OBJ3] {TR-013} [COMPLETES TR-013] Test/fix visible outcomes and last-success in backend/{tests/services/test_checks.py,src/binocular/services/checks.py} after:T016
- [X] T018 [OBJ3] {TR-015} Verify/configure existing whole-project gates in backend/pyproject.toml, frontend/package.json, Dockerfile, and .github/workflows/{ci,release}.yml after:T017
- [X] T019 [OBJ3] {TR-016} [COMPLETES TR-016] Add conformance/fair-yield tests for T001 APIs in backend/tests/scraping/test_conftest.py after:T018
- [X] T020 [OBJ3] {TR-017} [COMPLETES TR-017] Assert fields, counts, budgets, outcomes, and exact three-run traces in backend/tests/scraping/test_trace.py after:T019
- [X] T021 [OBJ3] {TR-018} [COMPLETES TR-018] Test every phase rejects eligibility/start at or beyond deadline in backend/tests/scraping/test_scope.py after:T020
- [X] T022 [OBJ3] {TR-019} [COMPLETES TR-019] Test origins, contention, scopes, updates, exits, and races in backend/tests/scraping/{test_rate_limit,test_robots}.py after:T021
- [X] T023 [OBJ3] {TR-020} [COMPLETES TR-020] Test all limit/Retry-After edges, no fifth attempt, and no eleventh redirect under backend/tests/scraping/ after:T022
- [X] T024 [OBJ3] {TR-023} [COMPLETES TR-023] Test/fix scoped calls in backend/{tests/extensions/test_runner.py,src/binocular/{scraping/client.py,extensions/runner.py}} after:T023
- [X] T025 [OBJ3] {TR-024} [COMPLETES TR-024] Document user-vetted extensions as unsandboxed/in-process with full application privileges and LAN limits in {docs/security.md,README.md} after:T024
- [X] T026 [OBJ3] {TR-025} [COMPLETES TR-025] Test redirect normalization, downgrade rejection, and all credential removal in backend/tests/scraping/test_client.py after:T025
- [X] T027 [OBJ3] {TR-026} [COMPLETES TR-026] Test robots TTL/status/failure/body-size matrix and cancellation no-cache in backend/tests/scraping/test_robots.py after:T026
- [X] T028 [OBJ3] {TR-027} [COMPLETES TR-027] Test robots redirect re-reservation and cross-origin rejection in backend/tests/scraping/{test_robots,test_client}.py after:T027
- [X] T029 [OBJ3] {TR-028} [COMPLETES TR-028] Test 5s force-close, failure, registry ownership, settlement, and bounds in backend/tests/extensions/test_runner.py after:T028
- [X] T030 [OBJ3] {TR-029} [COMPLETES TR-029] Prove policy, credentials, retries, cleanup, and rejection in backend/tests/ after:T029

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T031 {TR-015} [COMPLETES TR-015] Run backend pytest --cov, Ruff, strict mypy, pip-audit; frontend test/lint/strict tsc; Docker build; Trivy HIGH/CRITICAL after:T030

## Success Criteria Coverage

- SC-001 → T002,T005,T022; SC-002 → T002-T007,T014,T016,T023,T026-T028
- SC-003 → T008-T009,T021,T023; SC-004 → T010-T013,T029
- SC-005 → T014-T017,T024-T025; SC-006 → T001,T019-T020
- SC-007 → T018,T031; SC-008 → T024-T030

## Dependencies

- Acyclic `after:T###` chain: T001-T031 in numeric order.
- T018 configures; T031 runs gates after T030.

## Phase: Bug Fixes

- [X] T032 [BUG:ERROR] {TR-002} [requirement-gap] Preserve unexpired robots policy and future cooldown while enforcing one shared 1,024-origin LRU — backend/src/binocular/scraping/{rate_limit,robots}.py
  > Error: Inactive limiter entries with future cooldown can be evicted; robots cache is independently unbounded.
  > Fix hint: Share origin lifecycle protection and evict only entries with no policy, fetch, cooldown, queue, or active request.
- [X] T033 [BUG:ERROR] {TR-002} [requirement-gap] Make shared robots fetch collectively scope-owned with per-waiter deadline detach and final-waiter cancellation — backend/src/binocular/scraping/robots.py
  > Error: Shared fetch executes under the initiating scope, so initiator expiry can fail later live waiters.
  > Fix hint: Track waiter scopes/deadlines and use fetch authority that remains valid while any waiter is live.
- [X] T034 [BUG:ERROR] {TR-007} [requirement-gap] Separate default and effective origin schedules for exact own-delay credit excluding contention — backend/src/binocular/scraping/rate_limit.py
  > Error: default_eligible_at currently uses the effective next-start timeline, producing zero credit after longer policy discovery.
  > Fix hint: Maintain parallel default/effective schedules and commit only the own reservation delta before authorization.
- [X] T035 [BUG:ERROR] {TR-025} [requirement-gap] Prevent client cookie/auth regeneration on cross-origin redirects and retries — backend/src/binocular/scraping/client.py
  > Error: Sanitized kwargs do not prevent the root httpx cookie jar from adding target-origin credentials.
  > Fix hint: Build sanitized redirect requests without inherited client auth/cookies and assert every credential class is absent.
- [X] T036 [BUG:WARNING] {TR-017} [requirement-gap] Emit production validation events for policy, pacing, attempts, redirects, credentials, deadlines, cleanup, outcomes, and counts — backend/src/binocular/scraping/{client,rate_limit,robots,scope}.py
  > Error: Exact three-run evidence currently records a synthetic test trace rather than runtime boundary events.
  > Fix hint: Add an injectable trace sink and assert canonical runtime traces across three fresh runs.
