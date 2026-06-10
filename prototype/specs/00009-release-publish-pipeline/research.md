## Research Report

**Context**: Release pipeline guidance for Binocular E018: SemVer-only GHCR publishing, multi-arch OCI images, vulnerability gates, SBOM, and provenance.

## SemVer Tags, GHCR Publishing, and Image Metadata
- **Key findings**: GitHub Actions can run only on tag pushes, and GHCR supports repository-owned OCI images with `GITHUB_TOKEN`. `docker/metadata-action` derives SemVer tags, `latest`, labels, and annotations from release refs.
- **Recommended**: Publish only from protected `v*.*.*` SemVer tags; use metadata-action for `{{version}}`, `latest`, and OCI labels.
- **Avoid**: Publishing from branches or PRs; using PATs when least-privilege `GITHUB_TOKEN` permissions work.
### Sources
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#push
- https://github.com/docker/metadata-action

## Multi-Architecture OCI Image Build
- **Key findings**: Docker Buildx supports `linux/amd64,linux/arm64` builds in GitHub Actions with QEMU and can push a multi-arch manifest to GHCR.
- **Recommended**: Publish one GHCR manifest for both platforms, capture the pushed digest, and use that digest for later verification.
- **Avoid**: Treating local single-platform loads as release-equivalent; ignoring slower emulated arm64 builds.
### Sources
- https://docs.docker.com/build/ci/github-actions/multi-platform/
- https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry

## Trivy Vulnerability Gate
- **Key findings**: Trivy Action can fail workflows with `exit-code: 1` for selected severities and can ignore unfixed vulnerabilities.
- **Recommended**: Scan the release image for `HIGH,CRITICAL`, `vuln-type: os,library`, `ignore-unfixed: true`, and fail on findings.
- **Avoid**: Blocking on unfixed CVEs when policy is fixable-only; hiding scan evidence.
### Sources
- https://github.com/aquasecurity/trivy-action
- https://aquasecurity.github.io/trivy/latest/docs/

## SBOM and Provenance Attestations
- **Key findings**: GitHub artifact attestations can bind provenance and SBOM evidence to OCI image digests and push attestations to the registry.
- **Recommended**: Generate SBOM and provenance attestations for the Buildx digest, with `id-token`, `attestations`, `contents`, and `packages` permissions scoped to release jobs.
- **Avoid**: Attesting mutable tags; omitting required permissions; producing SBOMs not bound to the published digest.
### Sources
- https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations
- https://github.com/in-toto/attestation/tree/main/spec/predicates

### Summary
Release should be tag-driven, digest-centered, and evidence-producing: SemVer tags create version and `latest` image tags, Buildx publishes one amd64/arm64 OCI manifest, Trivy blocks fixable high/critical CVEs, and attestations bind provenance plus SBOM to the immutable image digest.

### Sources Index
| URL | Topic | Fetched |
|-----|-------|---------|
| https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#push | SemVer Tags | 2026-05-31 |
| https://github.com/docker/metadata-action | Metadata | 2026-05-31 |
| https://docs.docker.com/build/ci/github-actions/multi-platform/ | Multi-Arch | 2026-05-31 |
| https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry | GHCR | 2026-05-31 |
| https://github.com/aquasecurity/trivy-action | Trivy | 2026-05-31 |
| https://aquasecurity.github.io/trivy/latest/docs/ | Trivy | 2026-05-31 |
| https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations | Attestations | 2026-05-31 |
| https://github.com/in-toto/attestation/tree/main/spec/predicates | Attestations | 2026-05-31 |
