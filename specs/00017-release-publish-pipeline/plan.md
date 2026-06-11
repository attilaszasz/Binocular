# Implementation Plan: Release & Publish Pipeline

**Branch**: `00017-release-publish-pipeline` | **Date**: 2026-06-11 | **Spec**: [spec.md](spec.md)

## Summary

**Goal**: Extend the CI/CD architecture to build and publish secure, multi-architecture Docker images to GHCR on SemVer tag pushes, including Trivy security scanning, SLSA provenance/SBOM attestations, and build-time version injection.  
**Approach**: Modify `.github/workflows/release.yml` to support multi-arch builds, SemVer checking, Trivy gates, and SLSA attestations, and introduce `.github/workflows/scheduled-scan.yml` for weekly scans.  
**Key Constraint**: Relying on GitHub Actions hosted runners which build arm64 images via QEMU emulation (can be slow; requires caching setup).

## Technical Context

**Language/Version**: GitHub Actions (YAML)  
**Primary Dependencies**: `actions/checkout@v5`, `docker/setup-qemu-action@v4`, `docker/setup-buildx-action@v4`, `docker/login-action@v4`, `docker/metadata-action@v5`, `docker/build-push-action@v7`, `aquasecurity/trivy-action@v0.36.0`, `actions/attest-build-provenance@v3`, `actions/attest-sbom@v3`  
**Storage**: N/A  
**Testing**: Workflow dry-runs and validation via syntax check or manual tag triggers  
**Target Platform**: GitHub Actions, GitHub Container Registry (GHCR), Docker (linux/amd64, linux/arm64)  
**Project Type**: single  
**Project Mode**: brownfield  
**Performance Goals**: Release build and publish time under 15 minutes  
**Constraints**: GITHUB_TOKEN permissions (packages: write, attestations: write, id-token: write)  
**Scale/Scope**: 2 GitHub Actions YAML workflow files

## Instructions Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Core Principles**:
  - **Honest Failure**: Release and scheduled scan workflows MUST fail visibly, reporting error exits on lint/syntax errors, security failures, or build crashes.
  - **Least-Privilege**: Images continue to build using the existing non-root user setup established in `Dockerfile`. GHA workflows request the minimum permissions scope required (`contents: read`, `packages: write`, `attestations: write`, `id-token: write`).
- **Technology Stack**:
  - Buildx for multi-platform container compilation (`linux/amd64` and `linux/arm64`).
  - GHCR as the target registry for the image.
- **Testing & Quality**:
  - Container vulnerability scanning using Trivy before push in `release.yml`, and weekly scheduled Trivy scanning of the published image in `scheduled-scan.yml`.

## Architecture

```mermaid
C4Container
  Person(maintainer, "Maintainer", "Publishes software release")
  System_Ext(github, "GitHub", "Hosts code repository and triggers GHA workflows")
  
  SystemBoundary(gha_boundary, "GitHub Actions") {
    Container(release_wf, "Release Workflow", "GitHub Actions", "Builds, scans, pushes, and attests multi-arch images")
    Container(scan_wf, "Scheduled Scan Workflow", "GitHub Actions", "Periodically scans published image")
  }

  System_Ext(ghcr, "GitHub Container Registry (GHCR)", "Hosts published container images and attestations")

  Rel(maintainer, github, "Pushes SemVer tag (v*.*.*)", "Git")
  Rel(github, release_wf, "Triggers", "Webhook")
  Rel(release_wf, ghcr, "Pushes multi-arch image and attestations", "HTTPS")
  Rel(scan_wf, ghcr, "Pulls and scans latest image", "HTTPS")
```

## Architecture Decisions

Feature-local tradeoffs only. Project-wide architectural decisions belong in standalone ADRs under `specs/adrs/` — reference them by ID (e.g., "See ADR-0001") instead of duplicating here.

| ID | Decision | Options Considered | Chosen | Rationale |
|----|----------|--------------------|--------|-----------|
| AD-001 | Release Tag Regex Validation | 1. Strict regex inside GHA script<br>2. Build-level check in Python script | 1. Strict regex inside GHA script | Fast fail-fast gate at the beginning of the GHA runner before spinning up VMs/Buildx. |
| AD-002 | Scheduled Scan Target | 1. Scan `latest` tag<br>2. Query GHCR for most recent SemVer tag and scan | 1. Scan `latest` tag | Simple and reliable. The `latest` tag represents the currently published stable release. |

## Data Model Summary

N/A — no persistent data

## API Surface Summary

N/A — no API surface

## Testing Strategy

| Tier | Tool | Scope | Mock Boundary | Install |
|------|------|-------|---------------|---------|
| Unit | `actionlint` | Syntax validation of GHA workflow files | — | `configured` |
| Integration | GHA Dry-Run | Simulating tag triggers and pipeline execution checks | — | `configured` |
| Security | `trivy` | Scan built container image for OS/library CVEs | — | `configured` |
| Coverage | N/A | N/A (Infrastructure pipelines) | — | — |

## Error Handling Strategy

| Error Category | Pattern | Response | Retry |
|----------------|---------|----------|-------|
| Invalid Tag Ref | Fail-fast check | Stop run, print error message, exit with code 1 | No |
| Build Failures | Fail-fast check | Workflow marked failed in GitHub Actions UI | Manual retry |
| Trivy Scan Failures | Security gate failure | Stop run, do not publish, exit with code 1 | Manual retry after patching dependencies |

## Integration Points

| Spec Reference | System/Service | Technical Approach | Contract |
|----------------|----------------|--------------------|----------|
| IP-001 | Dockerfile | Release workflow builds image using local Dockerfile | Context path `.`, file `Dockerfile` |
| IP-002 | Frontend Version Injection | Release workflow passes git tag as `VITE_APP_VERSION` | Docker build arg: `VITE_APP_VERSION` |

## Risk Mitigation

| Risk (from spec) | Likelihood | Impact | Mitigation | Owner |
|-------------------|------------|--------|------------|-------|
| QEMU Emulation Overhead | Medium | Low | Use GitHub Actions caching (`cache-from: type=gha`, `cache-to: type=gha,mode=max`) to optimize subsequent layer compilation times. | Release workflow |
| Trivy False Positives or Temporary Network Errors | Low | Medium | Utilize standard latest Trivy actions and fallback on failure where appropriate, but maintain strict fail-on-error. | Release workflow |

## Requirement Coverage Map

| Req ID | Component(s) | File Path(s) | Notes |
|--------|--------------|--------------|-------|
| OR-001 | Release GHA Workflow Trigger | [.github/workflows/release.yml](../../.github/workflows/release.yml) | Set trigger `on.push.tags` to `v*.*.*` |
| OR-002 | SemVer Validation Check | [.github/workflows/release.yml](../../.github/workflows/release.yml) | Shell validation utilizing regex: `^v[0-9]+\.[0-9]+\.[0-9]+$` |
| OR-003 | Multi-arch Compilation | [.github/workflows/release.yml](../../.github/workflows/release.yml) | Setup QEMU and set `platforms: linux/amd64,linux/arm64` in build-push action |
| OR-004 | Multi-arch Image Tagging | [.github/workflows/release.yml](../../.github/workflows/release.yml) | Configure `docker/metadata-action` with `semver` and `latest` |
| OR-005 | Pre-push Vulnerability Scan | [.github/workflows/release.yml](../../.github/workflows/release.yml) | Local single-arch build scanned using `aquasecurity/trivy-action` |
| OR-006 | Vulnerability Gate | [.github/workflows/release.yml](../../.github/workflows/release.yml) | Set `exit-code: 1` and `ignore-unfixed: true` with severity `HIGH,CRITICAL` in Trivy gate |
| OR-007 | Supply Chain Attestation | [.github/workflows/release.yml](../../.github/workflows/release.yml) | Generate CycloneDX SBOM with Trivy and publish using GHA attestations actions |
| OR-008 | Version Build Argument | [.github/workflows/release.yml](../../.github/workflows/release.yml) | Pass `VITE_APP_VERSION=${{ github.ref_name }}` to Buildx step |
| OR-009 | Scheduled Weekly Scan | [.github/workflows/scheduled-scan.yml](../../.github/workflows/scheduled-scan.yml) | Setup workflow with schedule cron `0 0 * * 0` executing Trivy scan |
| RR-001 | Runbook Documentation | [specs/00017-release-publish-pipeline/runbook.md](runbook.md) | Create manual intervention/hotfix runbook |

## Project Structure

### Source Code

```text
~ .github/workflows/
  ~ release.yml
  + scheduled-scan.yml
~ specs/
  ~ project-plan.md
  ~ 00017-release-publish-pipeline/
    + runbook.md
```

**Patterns to reuse**: Existing Github Actions structure, build tools, and caching protocols in `ci.yml`.  
**Tests to extend**: N/A  
**Naming conventions**: Standard camelCase or hyphenated workflow actions.

## Implementation Hints

- **[HINT-001]** Caching: Set up GHA caching in `docker/build-push-action` using `cache-from: type=gha` and `cache-to: type=gha,mode=max` to prevent building frontend node modules and backend virtualenvs from scratch.
- **[HINT-002]** Attestations Permissions: Make sure packages, attestations, and id-token permissions are explicitly set to `write` on the release job.
- **[HINT-003]** Tag Match Syntax: Ensure `docker/metadata-action` configures both `pattern={{version}}` and `pattern={{major}}.{{minor}}` so that tag `v1.2.3` creates `1.2.3`, `1.2`, and `latest`.
