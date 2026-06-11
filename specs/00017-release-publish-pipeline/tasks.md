# Tasks: Release & Publish Pipeline

**Project Mode**: brownfield
**Epic**: E017 | **Capability**: DDR-001 (Release & Publish Pipeline)

## Phase 1: Workflow Setup

- [X] T001 [OR-001,OR-002,OR-003,OR-004] Configure release workflow in `.github/workflows/release.yml` with push trigger on `v*.*.*`, strict SemVer tag regex validation, multi-arch setup using QEMU and Buildx, and metadata tagging (`{{version}}`, `{{major}}.{{minor}}`, `latest`).
- [X] T002 [OR-008] Inject version info by passing the build argument `VITE_APP_VERSION` from the GHA git tag reference name to the Buildx compilation step.

## Phase 2: Vulnerability Gate Setup

- [X] T003 [OR-005,OR-006] Integrate pre-push Trivy vulnerability scan in `.github/workflows/release.yml` that builds a single-arch candidate image, scans it, and exits with code 1 if HIGH or CRITICAL issues with available fixes are detected.
- [X] T004 [OR-009] Create scheduled weekly scan workflow in `.github/workflows/scheduled-scan.yml` running on Sunday at midnight to scan the latest published image on GHCR.

## Phase 3: Attestation and SBOM Setup

- [X] T005 [OR-007] Configure CycloneDX SBOM generation using Trivy and attach SLSA build provenance and SBOM attestations to the published GHCR image in `.github/workflows/release.yml`.

## Phase 4: Documentation and Validation

- [X] T006 [RR-001] Create runbook documentation file `specs/00017-release-publish-pipeline/runbook.md` describing manual release, emergency hotfixes, and rollback/override procedures.

## Phase 5: QC & Verification

- [X] T007 Run `actionlint` or syntax check on the GHA workflow files to ensure validity.
- [X] T008 Run the full project test suite and verify that the release configurations apply cleanly, ending with `.qc-passed` creation.
