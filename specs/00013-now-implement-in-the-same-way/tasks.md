# Tasks — Official Panasonic Lumix Module

## Phase 1 — Artifacts and Fixtures

- [X] T001 [P] [US1] {FR-003} Add Panasonic firmware index fixture with GH/G rows and JavaScript download handlers
- [X] T002 [P] [US1] {FR-005} Add unparseable Panasonic fixture

## Phase 2 — Module Implementation

- [X] T003 [P] [US1] {FR-001} Create official Panasonic Lumix module metadata and check entrypoint
- [X] T004 [P] [US1] {FR-002} Ensure module uses only injected ScrapeClient
- [X] T005 [P] [US1] {FR-003} Implement Panasonic firmware index parser
- [X] T006 [P] [US2] {FR-004} Implement grouped model alias matching
- [X] T007 [P] [US1] {FR-005} Implement visible module failure results

## Phase 3 — Tests and Docs

- [X] T008 [P] [US1] {FR-003} Add parser and latest-version tests
- [X] T009 [P] [US2] {FR-004} Add grouped alias tests
- [X] T010 [P] [US1] {FR-005} Add failure-mode tests
- [X] T011 [P] [US3] {FR-006} Update official module documentation
- [X] T012 [P] [US1] {FR-001} Run focused and full QC validation

## Dependencies

| Task | Depends On |
|------|------------|
| T001 | — |
| T002 | — |
| T003 | T001 |
| T004 | T003 |
| T005 | T001, T003 |
| T006 | T005 |
| T007 | T005 |
| T008 | T005 |
| T009 | T006 |
| T010 | T002, T007 |
| T011 | T003 |
| T012 | T008, T009, T010, T011 |