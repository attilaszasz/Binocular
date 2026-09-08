# Tasks: Robots Content-Length Tolerance

**Input**: Design documents from `specs/00034-robots-content-length-tolerance/`
**Prerequisites**: `plan.md`, `spec.md`

## Project Mode

Brownfield

## Phase 1: Work Item 1 - Honor Valid Policies (Priority: P1)

- [X] T001 [OBJ1] {TR-001,TR-002} Update robots policy validation to bound the actual body without requiring Content-Length equality in backend/src/binocular/scraping/robots.py → exports: RobotsChecker.policy
- [X] T002 [OBJ1] {TR-003} Add mismatched Content-Length policy regression coverage in backend/tests/scraping/test_robots.py after:T001

---

## Phase 2: Polish & Cross-Cutting Concerns

- [X] T003 [P] [OBJ1] {TR-001,TR-002,TR-003} Run targeted scraper tests and strict static analysis after:T002

## Dependencies

- T002 depends on T001.
- T003 depends on T002.
