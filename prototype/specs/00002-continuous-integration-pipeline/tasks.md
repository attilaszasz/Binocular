# Tasks: Continuous Integration Pipeline

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Project Mode**: mixed

## Dependencies

| Phase | Depends On | Parallel Notes |
|-------|------------|----------------|
| Phase 1 Setup | — | Create workflow directory if needed. |
| Phase 2 🎯 MVP OBJ1 | Phase 1 | Backend CI gates. |
| Phase 3 🎯 MVP OBJ2 | Phase 2 | Frontend job shares workflow. |
| Phase 4 🎯 MVP OBJ3 | Phase 3 | Docker job completes workflow. |
| Phase 5 Verification | Phases 2-4 | Local command and YAML validation. |

## Phase 1: Setup

- [X] T001 Create workflow directory .github/workflows if missing
- [X] T002 Create CI workflow shell in .github/workflows/ci.yml after:T001

## Phase 2: 🎯 MVP Objective 1 - Backend Quality Gate

- [X] T003 [OBJ1] {OR-001,OR-009} Add PR and main push triggers plus minimal permissions in .github/workflows/ci.yml after:T002
- [X] T004 [OBJ1] {OR-002,OR-003,OR-004,OR-005} Add backend job in .github/workflows/ci.yml after:T003 [COMPLETES OR-005]

## Phase 3: 🎯 MVP Objective 2 - Conditional Frontend Gate

- [X] T005 [OBJ2] {OR-006} Add frontend manifest detection and explicit skip step in .github/workflows/ci.yml after:T004
- [X] T006 [OBJ2] {OR-006} Add conditional npm install, lint, typecheck, and test steps in .github/workflows/ci.yml after:T005 [COMPLETES OR-006]

## Phase 4: 🎯 MVP Objective 3 - Build-Only Docker Gate

- [X] T007 [OBJ3] {OR-007,OR-008,OR-009} Add Docker Buildx build-only job in .github/workflows/ci.yml after:T006

## Phase 5: Verification

- [X] T008 {OR-001,OR-009} Validate workflow YAML and absence of publish settings in .github/workflows/ci.yml after:T007
- [X] T009 {OR-002,OR-003,OR-004,OR-005} Run backend lint, type, test coverage, and security audit locally after:T004
- [X] T010 {OR-007,OR-008} Run local Docker build for the repository Dockerfile after:T007 [COMPLETES OR-007] [COMPLETES OR-008]