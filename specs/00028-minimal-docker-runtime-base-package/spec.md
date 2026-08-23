---
feature_branch: "00028-minimal-docker-runtime-base-package"
created: "2026-08-23"
input: "Resolve the scheduled Trivy scan's HIGH Debian 13 util-linux vulnerabilities (CVE-2026-53612, CVE-2026-53613, CVE-2026-53614, CVE-2026-53615) in the published runtime image by applying available OS security updates during its Docker build. Permit only Dockerfile plus dev-only pip>=26.2 quality-gate support, docker-container Buildx --load QC instruction, and local Trivy --pkg-types verification; preserve non-root runtime behavior and production application dependencies."
spec_type: "technical"
spec_maturity: "draft"
epic_id: ""
epic_sources: ""
---

# Feature Specification: Minimal Docker Runtime Base Package Update

**Feature Branch**: `00028-minimal-docker-runtime-base-package`
**Created**: 2026-08-23
**Status**: Draft
**Spec Type**: technical
**Spec Maturity**: draft
**Product Document**: specs/prd.md

## Problem Statement

The scheduled Trivy scan reports four HIGH vulnerabilities in the Debian 13 `util-linux` package included in the published runtime image: CVE-2026-53612, CVE-2026-53613, CVE-2026-53614, and CVE-2026-53615. Operators receive a published image with known, fixable operating-system vulnerabilities despite the release pipeline's vulnerability gate. Applying available OS security updates during the runtime-image build remediates these findings without changing application behavior or production application dependencies.

## Scope

### Included

- A root `Dockerfile` change that refreshes Debian package metadata and applies available OS package updates in the final runtime stage.
- Removal of APT package-list metadata in the same runtime-stage build layer after the update.
- Validation that the rebuilt runtime image no longer reports the four named HIGH `util-linux` findings in the scheduled Trivy scan.
- Preservation of the existing PUID/PGID entrypoint and resulting non-root application process.
- Dev-only quality-gate support in `backend/pyproject.toml` and `backend/uv.lock` that resolves `pip>=26.2` for the `pip-audit` environment only.
- Local QC instruction updates in `.github/agents/_qc-auditor.md` and `.github/skills/quality-control/SKILL.md`: use `docker buildx build --load` with the docker-container Buildx driver and `trivy image --pkg-types os` for local image verification.

### Excluded

- Production application, Python, or Node dependency changes — the sole dependency change is the dev-only `pip>=26.2` quality-gate support and its lockfile resolution.
- Changes to the scheduled scan, release workflow, scanner policy, or vulnerability-severity gate — the support instructions affect local verification only; existing controls remain unchanged.
- Changes outside `Dockerfile`, `backend/pyproject.toml`, `backend/uv.lock`, `.github/agents/_qc-auditor.md`, and `.github/skills/quality-control/SKILL.md` — the remediation has no other permitted paths.
- Base-image tag changes, package pinning, or broad Dockerfile refactoring — unnecessary for this targeted remediation.
- Builder-stage updates — the reported findings are in the published final runtime image.

### Edge Cases & Boundaries

- If APT cannot obtain package metadata or apply updates, the Docker build must fail rather than publish an image with an unverified update state.
- If Debian repositories do not yet provide fixes for any named CVE, the scan may remain failing; no scanner suppression or exception is in scope.
- The update step must not leave APT package-list metadata in the final image.
- The entrypoint may initialize as root for PUID/PGID handling, but the application process must continue to run as the configured non-root UID/GID.

## Technical Objectives

### Objective 1 - Patch Runtime OS Packages (Priority: P1)

Ensure every Docker build of the final published runtime stage applies currently available Debian OS updates so the fixed `util-linux` package versions are included before the image is released.

**Why this priority**: Security-critical remediation; the published image currently contains known HIGH vulnerabilities with available fixes.

**Rationale**: The final stage is the image scanned and published to operators. Updating its installed OS packages addresses the affected Debian package without expanding the application dependency surface.

**Deliverables**:
- `Dockerfile` — final runtime-stage OS update and APT metadata cleanup instruction.

**Validation Criteria**:
1. **Given** the final runtime stage starts from the configured Debian 13-based Python image, **When** the Dockerfile is built with available Debian security updates, **Then** installed runtime OS packages include the available updated `util-linux` version and APT package lists are absent from the final image.
2. **Given** the updated image is scanned by the existing scheduled Trivy configuration, **When** CVE-2026-53612, CVE-2026-53613, CVE-2026-53614, and CVE-2026-53615 have vendor-provided fixes, **Then** none is reported as a HIGH vulnerability in the published runtime image.
3. **Given** a container starts with valid default or configured PUID/PGID values, **When** the entrypoint launches the application after the update, **Then** the application process retains the configured non-root UID/GID behavior.

### Technical Constraints

- Change only `Dockerfile`, `backend/pyproject.toml`, `backend/uv.lock`, `.github/agents/_qc-auditor.md`, and `.github/skills/quality-control/SKILL.md`.
- Retain the current `python:3.13-slim` runtime base-image family, entrypoint, command, exposed port, and PUID/PGID behavior.
- In `backend/pyproject.toml` and `backend/uv.lock`, allow only dev-only resolution of `pip>=26.2` for the `pip-audit` environment; do not alter production application dependencies.
- In the two named QC instruction paths, allow only the `docker buildx build --load` instruction for the docker-container Buildx driver and `trivy image --pkg-types os` local-verification instruction; do not alter the release workflow or scanner policy.
- Refresh package metadata, apply updates, and remove package lists in one Docker build instruction so stale metadata is not reused and metadata is not retained.

## Integration Points

- **IP-001**: `Dockerfile` produces the final image consumed by the release and publish pipeline in `specs/00017-release-publish-pipeline/spec.md`.
- **IP-002**: The final runtime stage invokes `entrypoint.sh`, which maintains the non-root PUID/PGID contract specified in `specs/00001-app-skeleton/spec.md`.
- **IP-003**: The existing scheduled Trivy scan verifies remediation of the published image; its configuration is not modified.

## Requirements

### Technical Requirements

- TR-001: The final runtime stage in the root `Dockerfile` MUST refresh Debian package metadata and apply all available OS package updates during the image build.
- TR-002: The runtime-stage update instruction MUST remove APT package-list metadata before the layer is committed.
- TR-003: The `Dockerfile` change MUST remediate CVE-2026-53612, CVE-2026-53613, CVE-2026-53614, and CVE-2026-53615 from the published runtime image when fixed `util-linux` packages are available from configured Debian repositories.
- TR-004: The `Dockerfile` change MUST preserve the existing entrypoint-mediated non-root application runtime behavior for default and configured PUID/PGID values.
- TR-005: The change MUST be confined to `Dockerfile`, `backend/pyproject.toml`, `backend/uv.lock`, `.github/agents/_qc-auditor.md`, and `.github/skills/quality-control/SKILL.md`. The backend files MAY only add and lock dev-only `pip>=26.2` for the `pip-audit` environment; the QC instruction files MAY only require `docker buildx build --load` for the docker-container Buildx driver and `trivy image --pkg-types os` local verification. The change MUST NOT alter production application dependencies, source behavior, release workflow, scanner policy, or runtime privilege behavior.

## Assumptions & Risks

### Assumptions

- The `python:3.13-slim` runtime base image uses Debian 13 repositories that expose the vendor fixes for the named `util-linux` CVEs.
- The scheduled Trivy scan evaluates the final published runtime image and recognizes the installed Debian package versions.
- The existing entrypoint continues to perform PUID/PGID setup independently of the runtime-stage package update.

### Risks

- **Vendor fix unavailable or scanner data lag** *(likelihood: low, impact: high)*: A named finding may persist until Debian publishes a fixed package version or Trivy refreshes its advisory data. Mitigation: allow the existing scan to fail visibly; do not suppress findings.
- **Package update build failure** *(likelihood: low, impact: medium)*: A repository or package-resolution failure can prevent image creation. Mitigation: fail the Docker build and preserve the prior published image rather than silently bypassing updates.

## Implementation Signals

- `NEW-CONFIG` — Update the runtime-stage package-management instruction in the root `Dockerfile`; no new configuration surface or application component is introduced.

## Success Criteria

### Measurable Outcomes

- SC-001 [OBJ1]: A newly built runtime image has no HIGH Trivy findings for CVE-2026-53612, CVE-2026-53613, CVE-2026-53614, or CVE-2026-53615 when scanned with the existing scheduled-scan configuration.
- SC-002 [OBJ1]: The final runtime image contains no APT package-list metadata after its OS update layer completes.
- SC-003 [OBJ1]: A container from the rebuilt image starts successfully and its application process runs as the default or supplied non-root PUID/PGID.

## Glossary

| Term | Definition |
|------|------------|
| APT | Debian's package-management tool and package-metadata system. |
| Runtime image | The final Docker build stage that is published and runs the Binocular application. |
| Trivy | The vulnerability scanner used by the existing scheduled image scan. |
| util-linux | Debian package containing core Linux utilities and the package affected by the named CVEs. |

## Compliance Check

### Instructions Check Report
**Target**: spec.md
**Status**: PASS

| Principle | Verdict | Notes |
|-----------|---------|-------|
| I. Honest Failure | PASS | Build and scan failures remain visible; no suppression is allowed. |
| II. Polite by Default | N/A | No outbound scraping behavior changes. |
| III. Data Ownership | N/A | No state or service dependency changes. |
| IV. Least-Privilege | PASS | TR-004 preserves the entrypoint-mediated non-root runtime contract. |
| V. Type Safety | N/A | No application source changes. |
| VI. Set-and-Forget | PASS | The remediation is applied during repeatable image builds without runtime configuration. |
| VII. Agent Output Style | N/A | Spec document. |
