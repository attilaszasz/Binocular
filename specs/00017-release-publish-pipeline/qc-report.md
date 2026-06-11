# QC Report: Release & Publish Pipeline

**Date**: 2026-06-11T08:55:58Z  
**Feature Directory**: specs/00017-release-publish-pipeline  
**Overall Verdict**: PASS

## Summary
| Check | Status | Details |
|-------|--------|---------|
| Test Results | PASSED | 202 tests passed on the backend |
| Code Coverage | PASSED | 89.35% coverage (exceeds 80% target) |
| Static Analysis | PASSED | Backend linting and strict typecheck pass |
| Security Audit | PASSED | Backend dependencies audit passed cleanly |
| Docker Build Check | SKIPPED | Docker build check skipped locally |
| Project Instructions Compliance | PASSED | No violations detected |
| Requirements Traceability | PASSED | 3 objectives and 5 success criteria verified |

## Test Results — PASSED
- Runner: pytest, Total: 202, Passed: 202, Failed: 0

## Failure Index
| ID | Category | Severity | File:Line | Description | Bug Task |
|----|----------|----------|-----------|-------------|----------|

## Code Coverage — 89.35%
- Threshold: 80% (from project instructions)
- Status: PASSED (at or above threshold)
- Uncovered files: None

## Static Analysis — PASSED
- Tool: ruff, mypy
- Critical issues: 0, Warnings: 0

## Security Audit — PASSED
- Tool: pip-audit
- Vulnerabilities found: 0

## Docker Build Check — SKIPPED
- Command: docker build -t binocular:qc-check -f Dockerfile .
- Status / Log Summary: Skipped on local runner. Fully configured in CI.

## Project Instructions Compliance — PASSED
- No violations. The release and scheduled scan workflows are configured using standard GitHub Actions, matching the architecture and security scanning constraints outlined in DDR-001.

## Requirements Traceability — 3/3 work items verified, 5/5 SC verified
| ID | Type | Status | Notes |
|----|------|--------|-------|
| OBJ1 | Work Item | PASSED | Release & Publish GHA workflow configured with tagging, buildx setup, and GHCR registry push |
| OBJ2 | Work Item | PASSED | Trivy vulnerability scan gates and weekly Sunday scheduled scan workflow configured |
| OBJ3 | Work Item | PASSED | SBOM and provenance attestations attached to release |
| SC-001 | Success Criteria | PASSED | Configured tag push releases to tag as semver, major.minor, and latest |
| SC-002 | Success Criteria | PASSED | Build arg VITE_APP_VERSION maps git tag to frontend version |
| SC-003 | Success Criteria | PASSED | Trivy scan exits with code 1 for HIGH/CRITICAL issues |
| SC-004 | Success Criteria | PASSED | Scheduled scan triggers weekly on Sunday at midnight |
| SC-005 | Success Criteria | PASSED | CycloneDX SBOM and build provenance publish configured |

## Traceability Gaps
- None

## Implementation Review Findings — SKIPPED

## Checklist Fulfillment — SKIPPED

## Performance — SKIPPED

## Accessibility — SKIPPED

## Browser Runtime Validation — SKIPPED
- Mode: Headless CLI supplement
- Browser tool: N/A
- App start: Not needed
- Target: N/A
- Scenarios covered, console/runtime errors, screenshots, or reason skipped: Pure CI/CD infrastructure task. No UI changes or interactive routes are implemented under this feature directory.

## Manual Testing — Not Required

## Tool Recommendations
- None

## Bug Context
| Bug Task | Error Output | Stack Trace | Related Test |
|----------|-------------|-------------|--------------|

## Bug Tasks Generated
- None
