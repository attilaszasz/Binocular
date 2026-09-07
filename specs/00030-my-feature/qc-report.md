# QC Report: Source-Aware HTTP Pacing

**Date**: 2026-09-07T03:35:51Z
**Feature Directory**: `specs/00030-my-feature`
**Overall Verdict**: PASS

## Changes from Prior Run
| Metric | Previous | Current | Delta |
|--------|----------|---------|-------|
| Backend tests | 389/389 | 395/395 | +6 passing |
| Frontend tests | 33/33 | 33/33 | — |
| Coverage | 86.91% | 87.22% | +0.31 pp |
| Requirement gaps | 5 | 0 | -5 |

## Summary
| Check | Status | Details |
|-------|--------|---------|
| Tests | PASSED | Backend 395/395; frontend 33/33 |
| Coverage | PASSED | 87.22% ≥ 80% |
| Static analysis | PASSED | Ruff, strict mypy, ESLint, strict tsc clean |
| Security | PASSED | pip-audit clean; Trivy HIGH/CRITICAL 0 |
| Docker | PASSED | `binocular:qc-check` built and loaded |
| Requirements | PASSED | 3/3 objectives and 8/8 success criteria verified |

## Test Results — PASSED
- Runner: pytest, Total: 395, Passed: 395, Failed: 0
- Runner: Vitest, Total: 33, Passed: 33, Failed: 0

## Failure Index
| ID | Category | Severity | File:Line | Description | Bug Task |
|----|----------|----------|-----------|-------------|----------|
| — | — | — | — | No failures | — |

## Code Coverage — 87.22%
- Threshold: 80% (from project instructions)
- Status: PASSED
- Lowest covered: module-kit templates 0% (distributed examples), SPA fallback 43%, notifications 69%, checks 74%.

## Static Analysis — PASSED
- `uv run ruff check .`: exit 0, no issues.
- `uv run mypy .`: exit 0, 110 source files clean under strict configuration.
- `npm run lint`: exit 0, no issues.
- `npm run typecheck`: exit 0, strict TypeScript clean.

## Security Audit — PASSED
- `uv run pip-audit`: exit 0, no known vulnerabilities; local unpublished `binocular` package not auditable through PyPI.
- `trivy image --quiet --scanners vuln --pkg-types os,library --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 binocular:qc-check`: exit 0.
- Trivy findings: Debian 0; Python/library 0 HIGH/CRITICAL.

## Docker Build Check — PASSED
- Command: `docker build --load -t binocular:qc-check -f Dockerfile .`
- Status / Log Summary: exit 0; frontend production build, backend environment, final image export, and Docker load completed.

## Project Instructions Compliance — PASSED
- No violations. Centralized scoped client, fail-visible outcomes, SQLite ownership, unsandboxed extension disclosure, strict typing, cancellation cleanup, and non-root container boundary verified.

## Requirements Traceability — 3/3 work items verified, 8/8 SC verified
| ID | Type | Status | Notes |
|----|------|--------|-------|
| OBJ1 | Work Item | PASSED | Canonical origins, shared policy/pacing, four attempts, Retry-After, and safe ten-hop redirects verified. |
| OBJ2 | Work Item | PASSED | Absolute deadlines, exact capped credit, invalidation, force-close ownership, and bounded cleanup verified. |
| OBJ3 | Work Item | PASSED | Deterministic runtime traces, compatibility, visible outcomes, docs, static transport proof, and all gates pass. |
| SC-001 | Success Criteria | PASSED | Equivalent origins share stable pacing; distinct origins remain independent. |
| SC-002 | Success Criteria | PASSED | Robots, retry, redirect, and capacity matrices pass. |
| SC-003 | Success Criteria | PASSED | Baseline preserved; exact own excess is credited and capped. |
| SC-004 | Success Criteria | PASSED | Expiry ends authority; active work cancels; survivors remain owned and cannot send. |
| SC-005 | Success Criteria | PASSED | Regressions pass and trust boundary is documented. |
| SC-006 | Success Criteria | PASSED | Three fresh runtime-derived traces match exactly without live HTTP or real sleeps. |
| SC-007 | Success Criteria | PASSED | Layout, Ruff, strict mypy/tsc, coverage, audits, image build, and Trivy pass. |
| SC-008 | Success Criteria | PASSED | Scope rejection, credential isolation, and zero alternate official-module transports verified. |

## Traceability Gaps
- None.

## Checklist Fulfillment — 20/20 spot-checked
- Security CHK001-CHK014: PASSED for centralized paths, robots/redirect policy, lifecycle, and trust disclosure.
- Security CHK018/CHK023/CHK031-CHK036: PASSED for credential, ownership, trace, and static evidence.
- Testing CHK001-CHK010: PASSED for controlled inputs and boundary matrices.
- Testing CHK011/CHK026-CHK032: PASSED for exact runtime traces and deterministic outcomes.

## Performance — PASSED
- Controlled-time tests verify origin independence, stable sequences, policy updates, protected LRU capacity, pending/active counts, and exact deadline credit without live waits.

## Accessibility — SKIPPED
- No UI or accessibility behavior changed.

## Browser Runtime Validation — SKIPPED
- Mode: N/A
- Browser tool: unavailable in active harness probe.
- App start: Not needed
- Target: N/A; feature has no browser-runtime scenarios.

## Manual Testing — Not Required
- All acceptance behavior is covered by deterministic unit/integration/static/image checks.

## Tool Recommendations
- None.

## Bug Context
| Bug Task | Error Output | Stack Trace | Related Test |
|----------|-------------|-------------|--------------|
| — | No remaining bugs | — | — |

## Bug Tasks Generated
- None.
