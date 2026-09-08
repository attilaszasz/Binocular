# QC Report: Canon Endpoint Discovery Cache

**Date**: 2026-09-08T06:16:00Z
**Feature Directory**: `specs/00033-canon-endpoint-discovery-cache`
**Overall Verdict**: PASS

## Changes from Prior Run
| Metric | Previous | Current | Delta |
|--------|----------|---------|-------|
| Trivy CRITICAL/HIGH | 7 HIGH | 0 | -7 |
| Lease coordination | Missing | Fenced SQLite lease | Fixed |

## Summary
| Check | Status | Details |
|-------|--------|---------|
| Backend tests | PASSED | 441/441 |
| Frontend tests | PASSED | 35/35 |
| Coverage | PASSED | 86.86% ≥ 80% |
| Static analysis | PASSED | Ruff and mypy strict |
| Security | PASSED | pip-audit clean; Trivy CRITICAL/HIGH clean |
| Docker build | PASSED | `binocular:qc-check` |

## Test Results — PASSED
- Runner: `uv run pytest --cov=binocular --cov-report=term-missing`, Total: 441, Passed: 441, Failed: 0.
- Frontend: `npm test -- --run`, Total: 35, Passed: 35, Failed: 0.

## Failure Index
| ID | Category | Severity | File:Line | Description | Bug Task |
|----|----------|----------|-----------|-------------|----------|
| None | — | — | — | — | — |

## Code Coverage — 86.86%
- Threshold: 80% (project instructions)
- Status: PASSED
- Uncovered files: no coverage threshold failures.

## Static Analysis — PASSED
- Tool: `uv run ruff check .`, `uv run mypy .`, `npm run lint`, `npm run typecheck`
- Critical issues: 0, Warnings: 0

## Security Audit — PASSED
- Tool: `uv run pip-audit`, `trivy image --severity CRITICAL,HIGH --exit-code 1 binocular:qc-check`
- Vulnerabilities found: 0 at CRITICAL/HIGH severity.

## Docker Build Check — PASSED
- Command: `docker build --load -t binocular:qc-check -f Dockerfile .`
- Status / Log Summary: Alpine 3.23 runtime rebuilt with `apk upgrade`; image built successfully.

## Project Instructions Compliance — PASSED
- No violations. Cache metadata excludes firmware results, uses SQLite, retains scoped `ScrapeClient`, and has fenced lease lifecycle.

## Requirements Traceability — 3/3 work items verified, 3/3 SC verified
| ID | Type | Status | Notes |
|----|------|--------|-------|
| OBJ1 | Work Item | PASSED | Migration, restart persistence, strict 24-hour boundary. |
| OBJ2 | Work Item | PASSED | Cached endpoint remains a centralized live request with fallback. |
| OBJ3 | Work Item | PASSED | Fenced lease acquire/heartbeat/detach/close and cancellation tests. |
| SC-001 | Success Criteria | PASSED | Deterministic boundary tests. |
| SC-002 | Success Criteria | PASSED | Scoped client paths and fixtures pass. |
| SC-003 | Success Criteria | PASSED | Lease and cancellation coverage passes. |

## Traceability Gaps
- None.

## Checklist Fulfillment — 3/3 spot-checked
- CHK001 — PASSED — append-only SQLite schema.
- CHK101 — PASSED — centralized live request path.
- CHK201 — PASSED — deterministic cache tests.

## Performance — PASSED
- Injected-clock cache checks have no real sleeps.

## Accessibility — SKIPPED
- No accessibility NFR applies.

## Browser Runtime Validation — SKIPPED
- Mode: N/A
- Browser tool: N/A
- App start: Not needed
- Target: N/A
- No browser behavior changed.

## Manual Testing — Not Required
- No `manual-test.md` generated.

## Tool Recommendations
- None.

## Bug Context
| Bug Task | Error Output | Stack Trace | Related Test |
|----------|--------------|-------------|--------------|
| None | — | — | — |

## Bug Tasks Generated
- None.
