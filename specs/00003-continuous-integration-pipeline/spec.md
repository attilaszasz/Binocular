---
feature_branch: "00003-continuous-integration-pipeline"
created: "2026-06-10"
input: "E003 GitHub Actions CI pipeline with lint (Ruff, mypy, ESLint, tsc), test (pytest, Vitest), and Docker build stages"
spec_type: "operational"
spec_maturity: "draft"
epic_id: "E003"
epic_sources: "{DOD:DDR-001}{DOD:DDR-002}"
---

# Feature Specification: Continuous Integration Pipeline

**Feature Branch**: `00003-continuous-integration-pipeline`
**Created**: 2026-06-10
**Status**: Draft
**Spec Type**: operational
**Spec Maturity**: draft
**Epic ID**: E003
**Epic Sources**: {DOD:DDR-001}{DOD:DDR-002}
**Product Document**: specs/prd.md

## Problem Statement

Every code change merged to Binocular must pass automated quality gates — linting, type checking, tests, and Docker image buildability — before reaching the main branch. Without CI enforcement, regressions in type safety (Principle V), test coverage, or container correctness can silently accumulate, undermining the set-and-forget reliability (Principle VI) that self-hosters depend on. E001 seeded a CI workflow and E002 extended it; this epic validates, hardens, and formalizes the pipeline as the project's quality gate.

## Scope

### Included

- GitHub Actions workflow on PRs and pushes to `main`
- Backend quality gates: Ruff lint, `mypy --strict`, pytest with coverage enforcement (≥80%), `pip-audit` dependency security scan
- Frontend quality gates: lint (ESLint/Biome), `tsc` strict type check, Vitest test runner — conditional on `frontend/package.json` existence
- Docker image build validation (build-only, no push) via Buildx with GHA cache
- Concurrency controls to cancel superseded runs
- Quality gate failure blocks merge

### Excluded

- Multi-arch image publishing — deferred to E017 (Release Pipeline)
- Playwright end-to-end tests — deferred to when sufficient UI exists
- Image vulnerability scanning (Trivy) — deferred to E017 release pipeline
- Code coverage reporting to external services — not required per project instructions
- Matrix testing across multiple Python/Node versions — single version targets sufficient for project scope

### Edge Cases & Boundaries

- Frontend not yet scaffolded (no `package.json`): frontend job must detect absence and pass gracefully with an informational message
- Backend dependency changes: `uv.lock` changes must trigger full dependency reinstall
- Large PRs triggering concurrent pushes: concurrency group must cancel in-progress runs for the same ref
- Flaky tests: CI must not mask failures — any test failure is a hard gate
- Docker build cache miss: first build in a clean cache must still complete within reasonable time limits

## Operational Objectives

### Objective 1 - Backend Quality Gates (Priority: P1)

The CI pipeline must run Ruff linting, `mypy --strict` type checking, pytest with coverage enforcement, and `pip-audit` security scanning on every PR and push to `main`, failing the workflow on any gate violation.

**Why this priority**: Type safety (Principle V) and coverage (80% mandate) are non-negotiable — without automated enforcement, regressions reach production silently.

**Rationale**: Backend quality gates form the primary defense against type errors, code style violations, untested code, and known dependency vulnerabilities. Running them on every change provides immediate feedback.

**Deliverables**:
- Backend job in `.github/workflows/ci.yml` with sequential lint → type-check → test → security-audit steps
- `uv sync --group dev` for dependency installation
- Coverage threshold enforcement via `pyproject.toml` `[tool.coverage.report]`

**Verification Criteria**:
1. **Given** a PR with a Ruff violation, **When** CI runs, **Then** the backend job fails at the lint step
2. **Given** a PR with a mypy type error, **When** CI runs, **Then** the backend job fails at the type-check step
3. **Given** a PR dropping coverage below 80%, **When** CI runs, **Then** the backend job fails at the test step
4. **Given** a PR with a known-vulnerable dependency, **When** CI runs, **Then** the backend job fails at the security-audit step
5. **Given** a clean PR passing all gates, **When** CI runs, **Then** the backend job succeeds

### Objective 2 - Frontend Quality Gates (Priority: P1)

The CI pipeline must run lint, TypeScript strict type checking, and Vitest tests for the frontend — but only when `frontend/package.json` exists, gracefully skipping when the frontend has not been scaffolded yet.

**Why this priority**: Frontend type safety is equally mandated by Principle V; conditional execution prevents false failures before E004 delivers the SPA shell.

**Rationale**: The frontend will be added in E004. CI must be ready to enforce quality from day one of frontend development while not blocking prior epics. Conditional steps based on `package.json` existence achieve both goals.

**Deliverables**:
- Frontend job in `.github/workflows/ci.yml` with conditional lint → typecheck → test steps
- Package existence detection via shell script with `GITHUB_OUTPUT`
- Node 22 setup with npm cache

**Verification Criteria**:
1. **Given** `frontend/package.json` does not exist, **When** CI runs, **Then** the frontend job passes with an informational skip message
2. **Given** `frontend/package.json` exists with a lint error, **When** CI runs, **Then** the frontend job fails at the lint step
3. **Given** `frontend/package.json` exists with a TypeScript error, **When** CI runs, **Then** the frontend job fails at the typecheck step
4. **Given** `frontend/package.json` exists with all gates passing, **When** CI runs, **Then** the frontend job succeeds

### Objective 3 - Docker Build Validation (Priority: P1)

The CI pipeline must build the Docker image on every PR and push without publishing, verifying that the Dockerfile and application are consistently buildable.

**Why this priority**: A broken Docker image blocks deployment and violates set-and-forget reliability — build validation catches Dockerfile regressions immediately.

**Rationale**: Build-only validation (no push) catches syntax errors, dependency resolution failures, and copy/stage issues early. Buildx with GHA cache keeps rebuild times fast. Publishing is deferred to E017.

**Deliverables**:
- Docker build job in `.github/workflows/ci.yml` using `docker/build-push-action` with `push: false`
- Buildx setup with GHA cache layer

**Verification Criteria**:
1. **Given** a valid Dockerfile and source, **When** CI runs, **Then** the Docker image builds successfully
2. **Given** a broken Dockerfile (e.g., invalid COPY), **When** CI runs, **Then** the docker-build job fails
3. **Given** a previous successful build, **When** CI runs again without Dockerfile changes, **Then** cached layers are reused

### Objective 4 - Concurrency & Workflow Governance (Priority: P1)

The CI workflow must use concurrency groups to cancel superseded runs, use minimal permissions, and structure jobs so backend, frontend, and Docker build run in parallel for fast feedback.

**Why this priority**: Parallel jobs and concurrency controls directly impact developer productivity — slow or redundant CI wastes compute and delays feedback.

**Rationale**: Concurrency groups prevent resource waste from rapid pushes. `contents: read` permission follows least-privilege. Parallel jobs minimize total wall-clock time.

**Deliverables**:
- `concurrency` block with `cancel-in-progress: true`
- `permissions: contents: read`
- Three independent parallel jobs

**Verification Criteria**:
1. **Given** two rapid pushes to the same branch, **When** CI triggers, **Then** the first run is cancelled in favor of the second
2. **Given** the workflow file, **When** inspected, **Then** permissions are set to `contents: read` only
3. **Given** all three jobs, **When** CI runs, **Then** backend, frontend, and docker-build execute in parallel

### Operational Constraints

- GitHub Actions free-tier public repo — no self-hosted runners
- Single Python version (3.13) and Node version (22) — no matrix builds
- No secrets required — all checks are read-only operations
- Workflow must be declarative YAML — no custom composite actions for this epic

## Integration Points

- **IP-001**: E001 (App Skeleton) provides `Dockerfile`, `pyproject.toml`, `entrypoint.sh`, and backend source structure
- **IP-002**: E001 seeded the initial `.github/workflows/ci.yml` — this epic validates and hardens it
- **IP-003**: E004 (Frontend SPA) will activate the frontend quality gates when `package.json` is created
- **IP-004**: E017 (Release Pipeline) extends this workflow with multi-arch publish, Trivy scanning, and SBOM generation

## Requirements

### Operational Requirements

- **OR-001**: CI workflow MUST trigger on all PRs and pushes to `main`
- **OR-002**: Backend job MUST run Ruff lint and fail on violations
- **OR-003**: Backend job MUST run `mypy --strict` and fail on type errors
- **OR-004**: Backend job MUST run pytest with coverage and fail below 80% threshold
- **OR-005**: Backend job MUST run `pip-audit` and fail on known vulnerabilities
- **OR-006**: Frontend job MUST detect `frontend/package.json` and skip gracefully when absent
- **OR-007**: Frontend job MUST run lint, typecheck, and tests when `package.json` exists
- **OR-008**: Docker build job MUST build the image without pushing
- **OR-009**: Docker build job MUST use Buildx with GHA cache
- **OR-010**: Workflow MUST use concurrency groups with cancel-in-progress
- **OR-011**: Workflow MUST set permissions to `contents: read`
- **OR-012**: Quality gate failure MUST block PR merge (via branch protection rule or required status check)

## Assumptions & Risks

### Assumptions

- GitHub Actions is available and the repository is public (free-tier runners)
- `astral-sh/setup-uv@v6`, `actions/setup-python@v6`, `actions/setup-node@v5`, `docker/setup-buildx-action@v4`, and `docker/build-push-action@v7` actions are available and stable
- Branch protection rules for `main` will be configured to require status checks (outside this epic's code scope)
- `uv sync --group dev` installs all backend development dependencies including test/lint tools

### Risks

- **GHA cache eviction** *(likelihood: low, impact: low)*: Docker layer or dependency caches may be evicted, causing slower builds. Mitigation: acceptable for a free-tier project; no action needed.
- **Action version breaking changes** *(likelihood: low, impact: medium)*: Pinned action major versions (v5, v6, v7) may introduce breaking changes. Mitigation: pin to exact major versions; review when updating.

## Implementation Signals

- `NEW-CONFIG` — GitHub Actions workflow YAML configuration
- `NEW-WORKER` — CI jobs running as automated quality gates on every code change

## Success Criteria

### Measurable Outcomes

- **SC-001** [OBJ1]: A PR with a Ruff violation, mypy error, or sub-80% coverage causes CI to fail
- **SC-002** [OBJ2]: With no `frontend/package.json`, the frontend job passes; with it present, lint/typecheck/test gates are enforced
- **SC-003** [OBJ3]: Docker image builds successfully in CI on a clean PR
- **SC-004** [OBJ4]: Concurrent pushes to the same branch cancel the prior CI run

## Glossary

| Term | Definition |
|------|------------|
| Quality gate | A CI job step that must pass for the overall workflow to succeed, blocking merge on failure |
| Buildx | Docker CLI plugin enabling advanced build features including multi-platform builds and GHA cache integration |
| GHA cache | GitHub Actions cache backend for Docker layers and dependency artifacts, reducing rebuild times |
| Concurrency group | GitHub Actions mechanism grouping workflow runs by a key, enabling cancel-in-progress for superseded runs |

## Compliance Check

### Instructions Check Report
**Target**: spec.md
**Status**: PASS

| Principle | Verdict | Notes |
|-----------|---------|-------|
| I. Honest Failure | PASS | OR-002–OR-005 ensure quality violations are visible, not silent |
| II. Polite by Default | N/A | No outbound scraping in CI |
| III. Data Ownership | N/A | CI pipeline has no data persistence |
| IV. Least-Privilege | PASS | OR-011 enforces `contents: read` permissions |
| V. Type Safety | PASS | OR-003 enforces `mypy --strict`; OR-007 enforces `tsc` strict |
| VI. Set-and-Forget | PASS | CI runs automatically on every change; no manual intervention |
| VII. Agent Output Style | N/A | Spec document |
