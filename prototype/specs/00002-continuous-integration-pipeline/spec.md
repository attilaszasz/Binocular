---
feature_branch: "00002-continuous-integration-pipeline"
created: "2026-05-31"
input: "E002 Continuous Integration Pipeline"
spec_type: "operational"
spec_maturity: "draft"
epic_id: "E002"
epic_sources: "{DOD:DDR-001}{DOD:DDR-002}"
---

# Feature Specification: Continuous Integration Pipeline

**Feature Branch**: `00002-continuous-integration-pipeline`  
**Created**: 2026-05-31  
**Status**: Draft  
**Spec Type**: operational  
**Spec Maturity**: draft  
**Epic ID**: E002  
**Epic Sources**: {DOD:DDR-001}{DOD:DDR-002}  
**Product Document**: specs/prd.md

## Problem Statement

Binocular now has a runnable backend and container, but no automated quality gate protects future changes. Maintainers and contributors need CI that catches lint, type, test, security, coverage, and image-build failures before merge. Without this, later parallel epics can silently break the foundation and erode the correctness-first project promise.

## Scope

### Included

- GitHub Actions workflow for pull requests and pushes to `main`.
- Backend lint, strict type-check, tests with coverage, and dependency security audit.
- Frontend lint/type/test gate that activates when `frontend/package.json` exists.
- Docker image build gate using the repository `Dockerfile`, without publishing.
- Dependency caching for Python and Docker build layers.

### Excluded

- Multi-architecture release publishing to GHCR — owned by E018.
- Trivy image scanning, SBOM, provenance, and SemVer tag publishing — owned by E018.
- Creating the frontend application — owned by E003.
- Adding database, module, scraping, or product-domain tests — owned by later feature epics.

### Edge Cases & Boundaries

- CI MUST pass in the current repository state where E003 has not created `frontend/` yet.
- Frontend checks MUST become active automatically once a frontend package manifest exists.
- PR and push runs MUST build the Docker image but MUST NOT push it to any registry.
- Any lint, type, test, security, coverage, or image-build failure MUST fail the workflow.

## Operational Objectives

### Objective 1 - Backend Quality Gate (Priority: P1)

Run backend validation on every pull request and push.

**Why this priority**: Backend correctness and strict typing are project mandates and block safe parallel development.

**Rationale**: E001 introduced the first runnable backend; all later epics need a repeatable gate around it.

**Deliverables**:
- GitHub Actions backend job using Python 3.13.
- Commands for Ruff, mypy strict, pytest coverage, and pip-audit.

**Verification Criteria**:
1. **Given** a pull request changes backend code, **When** CI runs, **Then** backend lint, type-check, tests, coverage, and security audit execute.
2. **Given** any backend gate fails, **When** CI finishes, **Then** the workflow reports failure.

### Objective 2 - Conditional Frontend Gate (Priority: P1)

Define frontend validation that is visible now and active once E003 adds the SPA.

**Why this priority**: Project instructions require frontend strict checks, but E003 is a parallel future epic.

**Rationale**: The CI contract should not block the current repo for a missing frontend, yet must enforce frontend quality when the app exists.

**Deliverables**:
- GitHub Actions frontend job with an explicit absent-frontend path.
- Conditional npm install, lint, type-check, and test commands for `frontend/package.json`.

**Verification Criteria**:
1. **Given** no `frontend/package.json` exists, **When** CI runs, **Then** the frontend job succeeds with an explicit skip message.
2. **Given** a frontend package exists, **When** CI runs, **Then** frontend install, lint, type-check, and tests execute.

### Objective 3 - Build-Only Docker Gate (Priority: P1)

Build the image on every pull request and push without publishing.

**Why this priority**: The Docker image is the distribution unit and must remain buildable after every change.

**Rationale**: Early image validation reduces release risk while preserving E018 as the owner of publishing.

**Deliverables**:
- Docker Buildx job targeting the repository `Dockerfile`.
- GitHub Actions cache configuration for build layers.
- No registry login or push step.

**Verification Criteria**:
1. **Given** a pull request or push, **When** CI runs, **Then** Docker Buildx builds the image successfully.
2. **Given** the workflow runs on any non-release ref, **When** the image build completes, **Then** no image is pushed.

### Operational Constraints

- Use GitHub Actions only; no external CI service.
- Pin third-party actions to major versions.
- Use only built-in GitHub token permissions required for read/build operations.
- Keep release publishing, multi-arch tags, SBOM, and provenance outside E002.

## Integration Points

- **IP-001**: E001 provides `backend/pyproject.toml`, `Dockerfile`, and backend test commands consumed by CI.
- **IP-002**: E003 will provide `frontend/package.json`; the frontend CI job activates from that manifest.
- **IP-003**: E018 will extend CI/release behavior for multi-arch GHCR publishing and release scanning.

## Requirements

### Operational Requirements

- **OR-001**: System MUST provide a GitHub Actions CI workflow for pull requests and pushes to `main`.
- **OR-002**: CI MUST run backend Ruff linting from `backend/`.
- **OR-003**: CI MUST run backend `mypy` strict type-checking from `backend/`.
- **OR-004**: CI MUST run backend tests with coverage and enforce the configured 80% threshold.
- **OR-005**: CI MUST run backend dependency security auditing.
- **OR-006**: CI MUST include a frontend validation job that skips explicitly when `frontend/package.json` is absent and runs install/lint/type/test commands when present.
- **OR-007**: CI MUST build the Docker image from the repository `Dockerfile` on pull requests and pushes.
- **OR-008**: CI MUST NOT publish images, tags, SBOMs, or provenance in this epic.
- **OR-009**: CI MUST use dependency or layer caching where supported by GitHub Actions.

## Assumptions & Risks

### Assumptions

- The repository is hosted on GitHub with Actions enabled.
- E001 backend commands remain valid after the previous epic.
- Frontend package scripts will use conventional names: `lint`, `typecheck`, and `test`.
- Docker Buildx is available in GitHub-hosted runners.

### Risks

- **Frontend parallelism mismatch** *(likelihood: medium, impact: medium)*: E003 may choose different script names; mitigate by documenting expected CI scripts and making failures visible when the manifest exists.
- **CI/runtime drift** *(likelihood: medium, impact: high)*: CI may pass different commands than local QC; mitigate by reusing exact backend commands from E001.
- **Publishing creep** *(likelihood: low, impact: medium)*: Release steps could leak into E002; mitigate by excluding registry login and push settings.

## Implementation Signals

- `NEW-CONFIG` — Add `.github/workflows/ci.yml`.
- `EXTERNAL-SERVICE` — Uses GitHub Actions as the CI runner only.
- `BREAKING-CHANGE` — None expected; adds validation without changing runtime code.

## Success Criteria

### Measurable Outcomes

- **SC-001** [OBJ1]: Backend CI job runs Ruff, mypy, pytest coverage, and pip-audit with failing commands failing the job.
- **SC-002** [OBJ2]: Frontend CI job succeeds with an explicit skip message when no `frontend/package.json` exists.
- **SC-003** [OBJ2]: Frontend CI job contains install, lint, type-check, and test steps gated by manifest presence.
- **SC-004** [OBJ3]: Docker build job builds `Dockerfile` without pushing an image.
- **SC-005** [OBJ3]: Workflow YAML contains no registry login or image-push configuration.

## Glossary

| Term | Definition |
|------|------------|
| Build-only | CI builds an artifact for validation but does not publish it. |
| Quality Gate | CI job or step that fails the workflow when a required check fails. |
| Manifest | Package definition file that indicates a project exists, such as `frontend/package.json`. |

## Compliance Check

- **Status**: PASS
- **Checked Against**: project-instructions.md
- **Notes**: Spec enforces linting, strict typing, tests, coverage, security audit, Docker build validation, and avoids publishing or external runtime services.