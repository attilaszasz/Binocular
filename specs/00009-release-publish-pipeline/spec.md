---
feature_branch: "00009-release-publish-pipeline"
created: "2026-05-31"
input: "E018 Release & Publish Pipeline"
spec_type: "operational"
spec_maturity: "draft"
epic_id: "E018"
epic_sources: "{DOD:DDR-001}"
---

# Feature Specification: Release & Publish Pipeline

**Feature Branch**: `00009-release-publish-pipeline`  
**Created**: 2026-05-31  
**Status**: Draft  
**Spec Type**: operational  
**Spec Maturity**: draft  
**Epic ID**: E018  
**Epic Sources**: {DOD:DDR-001}  
**Product Document**: specs/prd.md

## Problem Statement *(mandatory)*

Binocular currently has CI that validates code and builds an image, but it does not publish release images for operators. Maintainers need a repeatable tag-driven release path that produces multi-architecture GHCR images with traceable metadata, vulnerability gating, and supply-chain evidence. Without this, self-hosters cannot reliably pull versioned release images and maintainers lack release provenance.

## Scope *(mandatory)*

### Included

- Tag-triggered GitHub Actions release workflow for SemVer refs.
- Multi-architecture Docker Buildx publishing for `linux/amd64` and `linux/arm64`.
- GHCR image metadata, versioned tags, and `latest` tag for release refs.
- Trivy image vulnerability gate for fixable HIGH and CRITICAL findings.
- SBOM and provenance attestations bound to the published image digest.

### Excluded

- Application runtime feature changes — this epic only releases the existing container image.
- Non-GHCR registry publishing — GHCR is the project release target for v1.
- Manual release approval environment — tag protection and workflow gates are sufficient for this increment.

### Edge Cases & Boundaries

- Non-SemVer tags MUST NOT publish release images.
- Pull requests and branch pushes MUST NOT push images or attestations.
- Vulnerabilities without available fixes MUST NOT block if the scan is configured for fixable-only gating.
- Attestations MUST target immutable image digests, not mutable tags.

## Operational Objectives *(mandatory for operational specs only)*

### Objective 1 - Publish Versioned Multi-Arch Images (Priority: P1)

Provide a release workflow that publishes one OCI image manifest for `linux/amd64` and `linux/arm64` to GHCR only when a valid SemVer tag is pushed.

**Why this priority**: Core release capability — operators need a stable, versioned image to deploy.

**Rationale**: The product is distributed primarily as a Docker container, and existing CI already validates image builds without publishing. Release publishing must be isolated from normal CI and branch activity.

**Deliverables**:
- `.github/workflows/release.yml`
- GHCR image tags derived from SemVer metadata
- Multi-architecture OCI image manifest

**Verification Criteria**:
1. **Given** a SemVer tag, **When** the workflow runs, **Then** it publishes `linux/amd64` and `linux/arm64` images to GHCR.
2. **Given** a branch or PR, **When** CI runs, **Then** no release image is pushed.

### Objective 2 - Gate Releases with Vulnerability Scanning (Priority: P1)

Run a Trivy image scan against the candidate release image and fail the workflow when fixable HIGH or CRITICAL vulnerabilities are detected.

**Why this priority**: Release integrity depends on blocking known severe fixable vulnerabilities before publication is trusted.

**Rationale**: The project promises a self-hosted image suitable for unattended operation; known severe fixable issues should stop a release.

**Deliverables**:
- Trivy image scan step
- Release-gating failure behavior
- Scan output retained in workflow logs or uploaded evidence

**Verification Criteria**:
1. **Given** a fixable HIGH or CRITICAL vulnerability, **When** Trivy scans the image, **Then** the workflow fails.
2. **Given** only unfixed vulnerabilities, **When** fixable-only policy runs, **Then** those findings do not fail the workflow.

### Objective 3 - Attach Supply-Chain Evidence (Priority: P2)

Generate SBOM and provenance attestations for published release images and attach them to GHCR using the pushed image digest.

**Why this priority**: Significant operational trust improvement; release images are usable without it, but provenance and SBOMs improve verification.

**Rationale**: Self-hosters and maintainers benefit from artifact traceability, and GitHub artifact attestations support digest-bound verification.

**Deliverables**:
- SBOM generation or attestation step
- Provenance attestation step
- Verification guidance for maintainers

**Verification Criteria**:
1. **Given** a published image digest, **When** attestations are generated, **Then** provenance and SBOM evidence target that digest.
2. **Given** a maintainer verifies the image, **When** they run the documented command, **Then** verification succeeds.

### Operational Constraints

- Workflow permissions MUST use least privilege: `contents: read`, `packages: write`, `id-token: write`, and `attestations: write` only where needed.
- Release publication MUST be tag-triggered and MUST NOT push on pull requests or branches.
- Release workflow MUST preserve the single-image Docker distribution model.
- Build cache SHOULD improve speed without becoming a correctness dependency.

## Integration Points *(mandatory for technical and operational specs)*

- **IP-001**: E018 depends on E002 via the existing GitHub Actions CI and Docker build patterns.
- **IP-002**: E018 depends on E001 via the root `Dockerfile` and single-container runtime contract.
- **IP-003**: Maintainers depend on GHCR for public OCI image distribution.
- **IP-004**: Supply-chain verification depends on GitHub artifact attestations and immutable image digests.

## Requirements *(mandatory)*

### Operational Requirements *(operational specs only)*

- **OR-001**: System MUST publish release images to GHCR only from valid SemVer tag refs.
- **OR-002**: System MUST produce versioned image tags and `latest` for release tags using deterministic metadata.
- **OR-003**: System MUST publish a multi-architecture OCI manifest for `linux/amd64` and `linux/arm64`.
- **OR-004**: System MUST fail the release workflow when Trivy detects fixable HIGH or CRITICAL vulnerabilities in the image.
- **OR-005**: System MUST attach provenance evidence to published image digests.
- **OR-006**: System MUST attach or publish SBOM evidence for published image digests.
- **OR-007**: System MUST use GitHub Actions permissions no broader than required for checkout, package publishing, and attestations.

### Runbook Requirements *(include for operational specs if applicable)*

- **RR-001**: A runbook MUST exist for cutting a release from a SemVer tag and verifying the published GHCR image.
- **RR-002**: A runbook MUST exist for responding to a failed Trivy release gate.

## Assumptions & Risks *(mandatory)*

### Assumptions

- GHCR is enabled for the repository and can be written with `GITHUB_TOKEN`.
- Maintainers will use SemVer tags with a `vMAJOR.MINOR.PATCH` format.
- The existing Dockerfile remains the canonical release image build input.
- GitHub-hosted runners can build both target platforms with Buildx and QEMU.

### Risks

- **Emulated arm64 builds are slow or flaky** *(likelihood: medium, impact: medium)*: Use Buildx cache and keep release workflow isolated from normal CI.
- **Trivy database or registry availability causes release delays** *(likelihood: medium, impact: medium)*: Fail visibly and rerun once the dependency recovers.
- **Mutable tag attestation mistakes reduce verification value** *(likelihood: low, impact: high)*: Bind attestations to the pushed digest and verify as part of QC.

## Implementation Signals *(mandatory)*

- Tag: `NEW-CONFIG` — Add a release workflow under `.github/workflows/` with GHCR, Buildx, Trivy, metadata, and attestation configuration.
- Tag: `EXTERNAL-SERVICE` — Integrate with GHCR, GitHub artifact attestations, Docker Buildx actions, and Trivy vulnerability data.
- Tag: `NEW-WORKER` — GitHub Actions release job performs multi-platform build, scan, publish, and attestation work.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** [OBJ1]: A valid SemVer tag produces GHCR image tags for the exact version and `latest`.
- **SC-002** [OBJ1]: The published image manifest includes both `linux/amd64` and `linux/arm64` platforms.
- **SC-003** [OBJ2]: A fixable HIGH or CRITICAL vulnerability causes the release workflow to fail before the release is accepted.
- **SC-004** [OBJ3]: Provenance and SBOM attestations are associated with the published immutable image digest.
- **SC-005** [OBJ3]: A maintainer can verify the published image attestation using documented commands.

## Glossary *(include when spec introduces 2+ domain-specific terms)*

| Term | Definition |
|------|------------|
| GHCR | GitHub Container Registry for Binocular images. |
| SemVer | Semantic Versioning release tag format. |
| SBOM | Software Bill of Materials for the image. |
| Provenance | Evidence describing how the image was built. |
| OCI manifest | Registry metadata for multi-platform images. |

## Compliance Check

### Instructions Check Report
**Target**: specs/00009-release-publish-pipeline/spec.md
**Status**: PASS

| Principle | Verdict | Notes |
|-----------|---------|-------|
| Honest Failure | PASS | Release gates fail visibly for scan and publication errors. |
| Polite by Default | N/A | No scraping behavior is changed. |
| Data Ownership & Self-Containment | PASS | Publishes the existing self-contained container image; no runtime external dependency is added. |
| Least-Privilege & Explicit Trust Boundary | PASS | Requires least-privilege workflow permissions. |
| Type Safety & Correctness-First | PASS | Preserves existing CI as release input; no code bypass is introduced. |
| Set-and-Forget Reliability | PASS | Provides versioned deployable images for operators. |
| Agent Output Style | PASS | Artifact remains concise and outcome-oriented. |

**Violations**:
None.
