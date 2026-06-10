# Tasks: Module Dev Kit & Docs

**Input**: Design documents from `specs/00016-module-dev-kit-docs-authoring/`
**Prerequisites**: `plan.md` (required), `spec.md` (required), `research.md` (if available)
**Tests**: Included because SC-001 through SC-004 require static, runtime, and documentation verification.

## Project Mode

`Brownfield`

## Epic / Capability Map

- `[US1]` → Local Static Validation
- `[US2]` → Local Runtime Execution
- `[US3]` → Standalone Authoring Documentation

## Brownfield Notes

- Existing components touched: backend structures under `backend/src/binocular/extensions/`.
- Regression focus: Core `ModuleLoader` and `ModuleRunner` integrity, strict typing compliance.

## Phase 1: Setup (Repository / Workspace Delta)

- [X] T001 Create backend CLI dev kit skeleton script in backend/src/binocular/extensions/devkit.py

---

## Phase 2: Foundational (Cross-Work-Item Blockers)

- [X] T002 Create devkit unit tests suite in backend/tests/extensions/test_devkit.py

---

## Phase 3: Work Item 1 - Local Static Validation (Priority: P1) 🎯 MVP

- [X] T003 [US1] {FR-001,FR-002} Implement argparse CLI skeleton with check command in backend/src/binocular/extensions/devkit.py after:T001
- [X] T004 [US1] {FR-002} Integrate ModuleLoader in devkit.py to run static contract checks and print structured stdout/stderr reports after:T003
- [X] T005 [US1] [COMPLETES FR-002] Verify static validation CLI commands and exit codes in backend/tests/extensions/test_devkit.py after:T004

---

## Phase 4: Work Item 2 - Local Runtime Execution (Priority: P1) 🎯 MVP

- [X] T006 [US2] {FR-003,FR-004} Add run command parser for device type, model, version, url, and extras in backend/src/binocular/extensions/devkit.py after:T003
- [X] T007 [US2] {FR-005} Implement in-process httpx MockTransport inside devkit.py for network-free local testing after:T006
- [X] T008 [US2] {FR-003,FR-005} Integrate ScrapeClient and ModuleRunner in devkit.py check_firmware runtime execution after:T007
- [X] T009 [US2] [COMPLETES FR-003,FR-004,FR-005] Verify runtime validation and MockTransport testing in backend/tests/extensions/test_devkit.py after:T008

---

## Phase 5: Work Item 3 - Standalone Authoring Documentation (Priority: P1) 🎯 MVP

- [X] T010 [US3] [COMPLETES FR-006] Create comprehensive documentation guide in docs/modules-authoring-guide.md

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T011 Run devkit tests slice to ensure everything passes with green results

---

## Dependencies

Setup → Foundational → US1 P1 static validation → US2 P1 runtime execution → US3 P1 documentation → Polish.

- T003 depends on T001.
- T004 depends on T003.
- T005 depends on T004.
- T006 depends on T003.
- T007 depends on T006.
- T008 depends on T007.
- T009 depends on T008.
- T010 and T011 depend on T009.
