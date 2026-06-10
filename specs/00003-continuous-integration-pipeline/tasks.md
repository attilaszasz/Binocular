# Tasks: Continuous Integration Pipeline

**Project Mode**: Brownfield
**Epic**: E003 — Continuous Integration Pipeline
**Spec Type**: operational

## Phase 1: OBJ1 — Backend Quality Gates 🎯 MVP

- [X] T001 [OBJ1] {OR-001,OR-002} Verify ci.yml trigger config (on: push/PR) and Ruff lint step in `.github/workflows/ci.yml`
- [X] T002 [OBJ1] {OR-003} Verify mypy --strict step runs correctly in `.github/workflows/ci.yml`
- [X] T003 [OBJ1] {OR-004} Verify pytest step enforces coverage ≥80% via pyproject.toml threshold in `.github/workflows/ci.yml`
- [X] T004 [OBJ1] {OR-005} [COMPLETES OR-005] Verify pip-audit dependency security step in `.github/workflows/ci.yml`

## Phase 2: OBJ2 — Frontend Quality Gates 🎯 MVP

- [X] T005 [OBJ2] {OR-006} Verify frontend package.json detection and graceful skip in `.github/workflows/ci.yml`
- [X] T006 [OBJ2] {OR-007} [COMPLETES OR-007] Verify conditional lint, typecheck, and test steps in `.github/workflows/ci.yml`

## Phase 3: OBJ3 — Docker Build Validation 🎯 MVP

- [X] T007 [OBJ3] {OR-008} Verify Docker build-push-action with push: false in `.github/workflows/ci.yml`
- [X] T008 [OBJ3] {OR-009} [COMPLETES OR-009] Verify Buildx setup and GHA cache configuration in `.github/workflows/ci.yml`

## Phase 4: OBJ4 — Concurrency & Workflow Governance 🎯 MVP

- [X] T009 [OBJ4] {OR-010} Verify concurrency group with cancel-in-progress: true in `.github/workflows/ci.yml`
- [X] T010 [OBJ4] {OR-011} Verify permissions: contents: read in `.github/workflows/ci.yml`
- [X] T011 [OBJ4] {OR-012} [COMPLETES OR-012] Document branch protection rule requirement for required status checks

## Phase 5: Polish & Cross-Cutting

- [X] T012 Run full backend quality gates locally (ruff, mypy, pytest --cov, pip-audit) to confirm green baseline
- [X] T013 [P] Verify ci.yml is valid YAML and all action versions are pinned to major versions
