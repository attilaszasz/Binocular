# QC Report: Release & Publish Pipeline

**Date**: 2026-05-31T12:54:26Z  
**Feature Directory**: specs/00009-release-publish-pipeline  
**Overall Verdict**: PASS

## Summary

| Check | Status | Details |
|-------|--------|---------|
| Tests | PASSED | Backend 65/65, frontend 9/9. |
| Coverage | PASSED | Backend total coverage 90.99%, threshold 80%. |
| Static Analysis | PASSED | Ruff, mypy strict, ESLint, and TypeScript all passed. |
| Security Audit | PASSED | pip-audit and npm audit found 0 known vulnerabilities. |
| Docker Build | PASSED | `docker build -t binocular:release-check .` completed. |
| Release Workflow | PASSED | YAML parsed; SemVer guard, GHCR publish, Trivy gate, SBOM, and provenance steps present. |
| Requirements Traceability | PASSED | 3/3 objectives and 5/5 success criteria verified. |
| Project Instructions | PASSED | No violations. |

## Test Results — PASSED

- Runner: pytest, Total: 65, Passed: 65, Failed: 0
- Runner: Vitest, Total: 9, Passed: 9, Failed: 0
- Runner: Vite build, Total: 1, Passed: 1, Failed: 0
- Runner: Docker build, Total: 1, Passed: 1, Failed: 0

## Failure Index

| ID | Category | Severity | File:Line | Description | Bug Task |
|----|----------|----------|-----------|-------------|----------|
| — | — | — | — | No failures. | — |

## Code Coverage — 90.99%

- Threshold: 80% from `.github/sddp-config.md`
- Status: PASSED
- Uncovered files: Existing backend uncovered lines reported by pytest; total coverage remains above threshold.

## Static Analysis — PASSED

- Tool: Ruff, mypy, ESLint, TypeScript
- Critical issues: 0, Warnings: 0

## Security Audit — PASSED

- Tool: pip-audit, npm audit
- Vulnerabilities found: 0
- Note: local Trivy CLI is not installed; the implemented release workflow runs Trivy in GitHub Actions before publication.

## Project Instructions Compliance — PASSED

- No violations.
- Release changes preserve self-contained runtime, least-privilege permissions, visible failure behavior, type-check/test gates, and single-container deployment.

## Requirements Traceability — 3/3 work items verified, 5/5 SC verified

| ID | Type | Status | Notes |
|----|------|--------|-------|
| OBJ1 | Work Item | PASSED | Release workflow is tag-triggered, validates SemVer, logs in to GHCR, generates metadata, and publishes amd64/arm64 image. |
| OBJ2 | Work Item | PASSED | Trivy gate scans the local release candidate before GHCR publication. |
| OBJ3 | Work Item | PASSED | Workflow generates SBOM and provenance attestations for the pushed digest. |
| SC-001 | Success Criteria | PASSED | metadata-action emits version and latest tags for release tags. |
| SC-002 | Success Criteria | PASSED | Buildx publish step targets `linux/amd64,linux/arm64`. |
| SC-003 | Success Criteria | PASSED | Trivy gate uses HIGH/CRITICAL, ignore-unfixed, and exit code 1. |
| SC-004 | Success Criteria | PASSED | Attestation steps use `steps.build.outputs.digest`. |
| SC-005 | Success Criteria | PASSED | docs/release.md documents `gh attestation verify` and imagetools inspection. |

## Traceability Gaps

None.

## Checklist Fulfillment — SKIPPED

- No checklist files generated; project-plan hint skipped checklist phase.

## Performance — SKIPPED

- No runtime performance requirement in this operational workflow feature.

## Accessibility — SKIPPED

- No UI or browser-facing change.

## Browser Runtime Validation — SKIPPED

- Mode: Not required
- Browser tool: N/A
- App start: Not needed
- Target: N/A
- Reason: Feature modifies GitHub Actions release automation and documentation only.

## Manual Testing — Not Required

- No manual-test.md generated.

## Tool Recommendations

- Optional: install `actionlint` locally or in CI for deeper GitHub Actions linting.
- Optional: install Trivy locally for pre-push image vulnerability checks; release workflow runs Trivy in CI.

## Bug Context

| Bug Task | Error Output | Stack Trace | Related Test |
|----------|--------------|-------------|--------------|
| — | — | — | — |

## Bug Tasks Generated

None.
