---
feature_branch: "00017-release-publish-pipeline"
created: "2026-06-11"
input: "E017"
spec_type: "operational"
spec_maturity: "draft"
epic_id: "E017"
epic_sources: "{DOD:DDR-001}"
---

# Feature Specification: Release & Publish Pipeline

**Feature Branch**: `00017-release-publish-pipeline`  
**Created**: 2026-06-11  
**Status**: Draft  
**Spec Type**: operational  
**Spec Maturity**: draft  
**Epic ID**: E017  
**Epic Sources**: {DOD:DDR-001}  
**Product Document**: specs/prd.md

## Problem Statement *(mandatory)*

Without a dedicated and automated release pipeline, publishing new versions of Binocular relies on manual, error-prone developer steps that risk building and distributing inconsistent or vulnerable container images. This impacts operators running offline/homelab devices who expect reliable multi-architecture support (amd64 and arm64), verifiable provenance, and secure images. Automating these steps through GitHub Actions ensures every SemVer tag translates directly to a secure, vetted, and properly attested public release.

## Scope *(mandatory)*

### Included

- **SemVer Release Trigger**: Automated workflow trigger when a git tag matching `v*.*.*` is pushed.
- **Multi-Architecture Build**: Compiling and publishing Docker images supporting both `linux/amd64` and `linux/arm64` architectures.
- **GHCR Publication**: Authenticating and pushing final images to GitHub Container Registry (GHCR) with standard tags.
- **Trivy Vulnerability Scan**: Scanning the built image before release and gating publication on any High or Critical severity issues that have available fixes.
- **Supply Chain Security**: Generating Software Bill of Materials (SBOM) and SLSA build provenance attestations.
- **Build-Time Version Injection**: Injecting the active git tag version into the React/Vite frontend environment during the build.
- **Scheduled Image Rescans**: A secondary weekly job that rescans the published `latest` container image to catch newly disclosed vulnerabilities.

### Excluded

- **Automatic Git Tagging / Changelog Generation** — tagging must be performed manually or by developer request; the release pipeline only reacts to pushes.
- **Continuous Deployment to Staging** — this epic focuses strictly on building, signing, scanning, and publishing the artifact.
- **Third-party Registry Pushes (Docker Hub, etc.)** — publishing is scoped only to GHCR as defined in DDR-001.

### Edge Cases & Boundaries

- **Invalid SemVer Tags**: Pushing a tag that begins with `v` but does not conform to strict SemVer (e.g. `v1.2` instead of `v1.2.0`) should fail validation immediately.
- **No Available Fixes in Trivy**: Trivy scan must not fail the release pipeline for vulnerabilities that do not have an available vendor patch.
- **Attestation Failures**: If SBOM or provenance generation fails during the publish step, the pipeline must fail to ensure we never publish unattested images.

## Operational Objectives *(mandatory for operational specs only)*

### Objective 1 - Automated Build and Publish Pipeline (Priority: P1)

Establish a secure GitHub Actions workflow that executes the multi-architecture build, validates the image quality, and publishes the resulting artifacts to GHCR.

**Why this priority**: Core release requirement; without this, automated distribution of the application to homelab users cannot occur.

**Rationale**: Containerization and registry publishing are required for deployment and distribution of self-hosted homelab software.

**Deliverables**:
- `.github/workflows/release.yml`

**Verification Criteria**:
1. **Given** a new git tag matching `v1.0.0` is pushed, **When** the Release workflow runs, **Then** a multi-arch container image is built for `linux/amd64` and `linux/arm64` and pushed to `ghcr.io`.
2. **Given** the frontend build stage runs, **When** the container is initialized, **Then** the value of `VITE_APP_VERSION` matches `v1.0.0`.

### Objective 2 - Image Scanning and Vulnerability Gate (Priority: P1)

Gate release publishing on security checks and configure continuous visibility into image dependencies via periodic rescans.

**Why this priority**: Required to prevent distributing known high-risk vulnerabilities to user devices.

**Rationale**: Maintaining a secure software supply chain and keeping homelab deployments safe from known vulnerabilities.

**Deliverables**:
- Trivy scan steps integrated into `.github/workflows/release.yml`
- `.github/workflows/scheduled-scan.yml`

**Verification Criteria**:
1. **Given** the build candidate contains a HIGH or CRITICAL vulnerability with an available fix, **When** the Trivy gate step runs, **Then** the build fails and publishing is aborted.
2. **Given** the weekly Sunday schedule is reached, **When** the scheduled-scan workflow runs, **Then** the published `latest` image is scanned and results are reported.

### Objective 3 - Software Bill of Materials (SBOM) and Attestation (Priority: P2)

Attach verifiable SBOM and build provenance to all published images using modern SLSA frameworks.

**Why this priority**: Enhances trust and verification for enterprise and homelab users, but is secondary to the functional build/push flow.

**Rationale**: Assures consumers of the software that the image was built in a secure, untampered environment directly from the source repository.

**Deliverables**:
- Attestation configurations in `.github/workflows/release.yml`

**Verification Criteria**:
1. **Given** a successful image push to GHCR, **When** the attestation steps run, **Then** SBOM and SLSA provenance data are published to GHCR associated with the digest.

### Operational Constraints

- **Execution Environment**: GitHub Actions runner (Ubuntu).
- **Authentication Scope**: Use of temporary, short-lived OIDC tokens and standard `GITHUB_TOKEN` credentials; no persistent maintainer secrets should be required for registry push.
- **Docker Multi-Arch**: Building multi-architecture images must use `docker/setup-qemu-action` and `docker/setup-buildx-action`.

## Integration Points *(mandatory for technical and operational specs)*

- **IP-001**: The Release workflow depends on `Dockerfile` for build layers and instructions.
- **IP-002**: The frontend shell SPA depends on the release pipeline to inject `VITE_APP_VERSION` via build args during the image compilation.

## Requirements *(mandatory)*

### Operational Requirements *(operational specs only)*

- **OR-001**: Release workflow MUST trigger on pushes matching the tag pattern `v*.*.*`.
- **OR-002**: Release workflow MUST fail if the tag ref does not match standard SemVer `^v[0-9]+\.[0-9]+\.[0-9]+$`.
- **OR-003**: Release workflow MUST build images for both `linux/amd64` and `linux/arm64`.
- **OR-004**: Release workflow MUST tag the published image with the exact SemVer tag, the `major.minor` tag (e.g. `v1.2`), and `latest`.
- **OR-005**: Release workflow MUST run a Trivy vulnerability scan on the compiled image candidate prior to pushing.
- **OR-006**: Release workflow MUST fail the build if Trivy detects HIGH or CRITICAL vulnerabilities that have available fixes.
- **OR-007**: Release workflow MUST generate and attach an SBOM (in CycloneDX format) and build provenance attestation (SLSA) to the published container image.
- **OR-008**: Release workflow MUST pass the git tag name to the Docker build command as the `VITE_APP_VERSION` build argument.
- **OR-009**: A weekly scheduled workflow MUST scan the latest published image using Trivy and report any discovered vulnerabilities.

### Runbook Requirements *(include for operational specs if applicable)*

- **RR-001**: A runbook MUST exist detailing how to manually trigger the release workflow or publish an emergency hotfix.

## Assumptions & Risks *(mandatory)*

### Assumptions

- The `GITHUB_TOKEN` inside the repository has adequate default permissions or is configured with custom `permissions` blocks to push to GHCR.
- The `Dockerfile` at the root of the project correctly consumes the `VITE_APP_VERSION` build argument to set the version variable.
- The GHA runner environment supports QEMU emulation for building `linux/arm64` binaries.

### Risks

- **QEMU Emulation Overhead** *(likelihood: medium, impact: low)*: Building multi-architecture images via emulation can be slow. Mitigation: utilize GitHub Actions caching (`cache-from` and `cache-to` with `type=gha`).
- **Trivy False Positives or Temporary Network Errors** *(likelihood: low, impact: medium)*: Scanner lookup failures can halt release builds. Mitigation: ensure Trivy uses standard caching and can run offline/cache-fallback when possible.

## Implementation Signals *(mandatory)*

- `NEW-CONFIG` — Creation of GitHub Action workflow `.github/workflows/scheduled-scan.yml`.
- `BREAKING-CHANGE` — Strict SemVer tag check prevents any unstructured tag pushes from running build/publish steps.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** [OBJ1]: An image is pushed to GHCR under `ghcr.io/<owner>/binocular` with tags `v1.0.0`, `1.0`, and `latest` upon tagging a release.
- **SC-002** [OBJ1]: A container run of the published image shows the version metadata `v1.0.0` in the frontend UI.
- **SC-003** [OBJ2]: If an image candidate contains a HIGH vulnerability with a fix, the pipeline is blocked and does not push to GHCR.
- **SC-004** [OBJ2]: The weekly scheduled scan triggers and completes scanning the published image on Sundays.
- **SC-005** [OBJ3]: The image page on GHCR displays the SBOM and provenance attestations.

## Glossary *(include when spec introduces 2+ domain-specific terms)*

| Term | Definition |
|------|------------|
| GHCR | GitHub Container Registry, GitHub's built-in hosting service for container images. |
| Trivy | An open-source vulnerability scanner specifically optimized for container images. |
| SBOM | Software Bill of Materials, a structured list of all components and dependencies in the image. |
| Provenance | A verifiable record of the build environment and execution steps (SLSA standard). |
| Buildx | Docker's CLI plugin extending capabilities with BuildKit, enabling multi-platform compilation. |
