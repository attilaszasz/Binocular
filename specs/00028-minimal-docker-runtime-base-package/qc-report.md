# QC Report: Minimal Docker Runtime Base Package Update

**Date**: 2026-08-23T07:48:35+03:00
**Feature Directory**: `specs/00028-minimal-docker-runtime-base-package`
**Overall Verdict**: PASS

## Changes from Prior Run
| Metric | Previous | Current | Delta |
|--------|----------|---------|-------|
| Requirements traceability | FAIL — TR-005 scope | PASSED — amended TR-005 permits five paths | Resolved T007 |
| Runtime/named-CVE validation | PASSED | PASSED | Revalidated fresh image |
| CI-equivalent gates | PASSED | PASSED | Revalidated |

## Summary
| Check | Status | Details |
|-------|--------|---------|
| CI-equivalent checks | PASSED | Backend/frontend lint, type checks, tests, coverage, audit, and Buildx image build pass. |
| Runtime and named-CVE validation | PASSED | APT lists empty; named CVEs absent; default/custom non-root IDs and health pass. |
| Requirements scope | PASSED | Only the five paths permitted by amended TR-005 changed. |

## Test Results — PASSED
- Runner: `uv run pytest --cov=binocular --cov-report=term-missing`; Total: 348, Passed: 348, Failed: 0.
- Runner: `npm test -- --run`; Total: 33, Passed: 33, Failed: 0.
- Runtime: default PID 1 `1000:1000`; configured PID 1 `1234:1235`; both `/healthz` responses were `200 {"status":"ok"}`.

## Failure Index
| ID | Category | Severity | File:Line | Description | Bug Task |
|----|----------|----------|-----------|-------------|----------|
| None | — | — | — | No failures. | — |

## Code Coverage — 85.77%
- Threshold: 80% (from project instructions).
- Status: PASSED (at or above threshold).
- Uncovered files: `module_kit/EXAMPLE_MODULE.py` (72), `module_kit/STARTER_TEMPLATE.py` (23), `services/checks.py` (47), `routes/notifications.py` (28).

## Static Analysis — PASSED
- Tool: `uv run ruff check .`, `uv run mypy .`, `npm run lint`, `npm run typecheck`.
- Critical issues: 0, Warnings: 0.

## Security Audit — PASSED
- Tool: `uv run pip-audit`; `trivy image --scanners vuln --pkg-types os --severity HIGH,CRITICAL --ignore-unfixed --format json binocular:qc-check`.
- Vulnerabilities found: 0 by `pip-audit` (the local `binocular` package is not auditable on PyPI).
- Named-CVE assertion: zero HIGH/CRITICAL results for CVE-2026-53612, CVE-2026-53613, CVE-2026-53614, and CVE-2026-53615.

## Docker Build Check — PASSED
- Command: `docker buildx build --pull --no-cache --load -t binocular:qc-check -f Dockerfile .`.
- Status / Log Summary: docker-container Buildx driver completed and loaded the candidate image. The final update layer installed `util-linux 2.41.5-0+deb13u1`.

## Project Instructions Compliance — PASSED
- No violations. Required backend/frontend type checks pass; runtime application process remains non-root; no production dependency, source, release-workflow, or scanner-policy change.

## Requirements Traceability — 1/1 work items verified, 3/3 SC verified
| ID | Type | Status | Notes |
|----|------|--------|-------|
| OBJ1 | Work Item | PASSED (5/5 TR) | Fresh image, scan, filesystem, health, runtime-ID, and scope evidence pass. |
| TR-001 | Requirement | PASSED | Final stage has one `apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*` layer. |
| TR-002 | Requirement | PASSED | `/var/lib/apt/lists` is empty in `binocular:qc-check`. |
| TR-003 | Requirement | PASSED | Trivy OS scan found zero named HIGH/CRITICAL CVE matches. |
| TR-004 | Requirement | PASSED | Entrypoint application PID 1 ran as default `1000:1000` and configured `1234:1235`; health passed. |
| TR-005 | Requirement | PASSED | Diff contains only `Dockerfile`, `backend/pyproject.toml`, `backend/uv.lock`, `.github/agents/_qc-auditor.md`, and `.github/skills/quality-control/SKILL.md`; dependency and guidance changes match the amended allowance. |
| SC-001 | Success Criteria | PASSED | Named-CVE Trivy assertion returned zero matches. |
| SC-002 | Success Criteria | PASSED | Final-image APT package-list directory is empty. |
| SC-003 | Success Criteria | PASSED | Default and configured non-root process IDs and health endpoint verified. |

## Traceability Gaps
- None.

## Checklist Fulfillment — SKIPPED
- No checklists found.

## Performance — SKIPPED
- No performance NFRs in scope.

## Accessibility — SKIPPED
- No accessibility NFRs in scope.

## Browser Runtime Validation — SKIPPED
- Mode: Terminal/headless supplement.
- Browser tool: No controllable browser client was available during the active probe.
- App start: `docker run --rm binocular:qc-check`.
- Target: `http://127.0.0.1:8000/healthz` inside the running container.
- Browser behavior is not in scope; terminal validation covered startup, health, and privilege behavior.

## Manual Testing — Not Required
- Automated terminal validation covers the scoped Docker runtime behavior.

## Tool Recommendations
- None. All configured quality-gate tools were available and executed.

## Bug Context
| Bug Task | Error Output | Stack Trace | Related Test |
|----------|-------------|-------------|--------------|
| None | — | — | — |

## Bug Tasks Generated
- None.
