# Tasks: E031 — Canon Endpoint Discovery Cache

**Input**: Design documents from `specs/00033-canon-endpoint-discovery-cache/`
**Prerequisites**: `plan.md`, `spec.md`, `data-model.md`, completed `checklists/`

**Tests**: Deterministic SQLite, fixture, virtual-time, scripted-transport, strict typing, lint, security, and coverage validation are mandatory.

## Project Mode

`Brownfield` — extend Canon modules and existing SQLite, runner, check-service, and `ScrapeClient` seams without repository bootstrap work.

## Epic / Capability Map

- `[OBJ1]` → durable endpoint metadata and strict freshness (P1 MVP).
- `[OBJ2]` → centralized live warm validation and bounded recovery (P1 MVP).
- `[OBJ3]` → fenced same-model coordination and deterministic failure coverage (P2).

## Phase 1: Objective 1 — Persist Safe Discovery Metadata 🎯 MVP

- [X] T001 [OBJ1] {TR-001,TR-002,TR-008} Add failing migration, restart, metadata, and 24h-boundary tests in backend/tests/test_canon_endpoint_cache.py
- [X] T002 [OBJ1] {TR-001} Add idempotent mapping and lease schema in backend/src/binocular/db/migrations/0009_canon_endpoint_cache.sql
- [X] T003 [OBJ1] {TR-001,TR-002} [COMPLETES TR-001] Implement mapping freshness in backend/src/binocular/official_modules/canon_endpoint_cache.py → exports: CanonEndpointCache.get_mapping()

---

## Phase 2: Objective 2 — Validate Through the Canonical Client 🎯 MVP

- [X] T004 [OBJ2] {TR-003,TR-004,TR-005,TR-007,TR-008} Add failing warm, miss, expiry, fallback, and visible-failure tests in backend/tests/test_canon_endpoint_cache.py after:T003
- [X] T005 [P] [OBJ2] {TR-003,TR-004,TR-005} Add camera warm flow in backend/src/binocular/official_modules/canon_rf_cameras.py ← T003:CanonEndpointCache.get_mapping
- [X] T006 [P] [OBJ2] {TR-003,TR-004} [COMPLETES TR-004] Add lens warm flow in backend/src/binocular/official_modules/canon_rf_lenses.py ← T003:CanonEndpointCache.get_mapping
- [X] T007 [OBJ2] {TR-003,TR-005,TR-007} [COMPLETES TR-003,TR-005] Preserve live failure and last-success in backend/src/binocular/services/checks.py after:T005,T006

---

## Phase 3: Objective 3 — Recover and Coordinate Deterministically

- [X] T008 [OBJ3] {TR-006,TR-008} Add failing lease takeover, fencing, detach, close-race, and cancellation tests in backend/tests/test_canon_endpoint_cache.py after:T003
- [X] T009 [OBJ3] {TR-006} Add atomic lease CAS and heartbeat in backend/src/binocular/official_modules/canon_endpoint_cache.py after:T003 → exports: acquire_or_join_lease(),heartbeat_lease()
- [X] T010 [OBJ3] {TR-006} Implement fenced waiter detach and lease closure in backend/src/binocular/official_modules/canon_endpoint_cache.py after:T009 ← T009:acquire_or_join_lease
- [X] T011 [OBJ3] {TR-006} Coordinate shared live work in backend/src/binocular/official_modules/canon_endpoint_cache.py after:T010 ← T009:heartbeat_lease → exports: coordinate_live_check()
- [X] T012 [OBJ3] {TR-006} [COMPLETES TR-006] Preserve module cancellation cleanup in backend/src/binocular/extensions/runner.py after:T011 ← T011:coordinate_live_check
- [X] T013 [OBJ3] {TR-008} Add scripted Canon fixture and virtual-time entry-point coverage in backend/tests/test_canon_endpoint_cache.py after:T007,T012
- [X] T014 [OBJ3] {TR-008} [COMPLETES TR-008] Run cache and backend tests, coverage, Ruff, mypy --strict, pip-audit, and image Trivy validation after:T013

---

## Dependencies

Objective 1 → Objective 2 → Objective 3

- T001 defines failing persistence contracts; T002 → T003 establishes the durable cache seam.
- T004 defines Objective 2 behavior; T005 and T006 run in parallel after T003; T007 joins both module paths.
- T008 defines coordination contracts; T009 → T010 → T011 → T012 is the lease and cancellation chain.
- T013 joins entry-point and coordination behavior; T014 is the final validation gate.
- Every `after:T###` reference must resolve to `[X]` before the dependent task runs.

## Phase: Bug Fixes

- [X] T015 [BUG:ERROR] {TR-006} [requirement-gap] Enroll and fence every shared Canon live operation through the SQLite lease — backend/src/binocular/official_modules/canon_endpoint_cache.py:222
  > Error: coordinate_live_check only used an in-process future and never called acquire_or_join_lease.
  > Fix hint: acquire, heartbeat, detach, and close with owner/fencing predicates around shared work.
- [X] T016 [BUG:ERROR] {TR-008} [security-vuln] Remediate Trivy CRITICAL/HIGH image vulnerabilities — Dockerfile:1
  > Error: Trivy reports CRITICAL perl CVE-2026-13221 and multiple HIGH Debian base-package vulnerabilities.
  > Fix hint: update or replace the vulnerable image base and rebuild/scan the produced image.

## Validation

- TR-001 through TR-008 and OBJ1 through OBJ3 are covered.
- `[P]` tasks modify separate module files and do not share a dependency batch with referenced tasks.
- Requirement completion markers occur on the final task for every requirement implemented across three or more tasks.
