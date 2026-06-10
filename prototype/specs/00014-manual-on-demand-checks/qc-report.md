# QC Report: Manual On-Demand Checks

**Date**: 2026-05-31T15:02:49Z  
**Feature Directory**: specs/00014-manual-on-demand-checks  
**Overall Verdict**: PASS

## Summary
| Check | Status | Details |
|-------|--------|---------|
| Implementation Gate | PASSED | `.completed` exists and all 19 tasks are checked. |
| Backend Static Analysis | PASSED | `uv run ruff check .`; `uv run mypy`. |
| Frontend Static Analysis | PASSED | `npm run typecheck`; `npm run lint`. |
| Backend Tests | PASSED | 112/112 passed. |
| Frontend Tests | PASSED | 20/20 passed. |
| Coverage | PASSED | Backend 91.15%; frontend 81.91%; threshold 80%. |
| Security | PASSED | `pip-audit` no known vulnerabilities; `npm audit --audit-level=critical` found 0 vulnerabilities. |
| Build | PASSED | `npm run build`; `docker build -t binocular:e010-qc .`. |

## Test Results — PASSED
- Runner: pytest, Total: 112, Passed: 112, Failed: 0.
- Runner: Vitest, Total: 20, Passed: 20, Failed: 0.
- Focused regression evidence: backend manual/single check slice 14/14 passed; frontend checks/App slice 11/11 passed.

## Failure Index
| ID | Category | Severity | File:Line | Description | Bug Task |
|----|----------|----------|-----------|-------------|----------|
| — | — | — | — | No failures. | — |

## Code Coverage — PASSED
- Threshold: 80% from `.github/sddp-config.md` derived QC policy.
- Backend: 91.15% total coverage via `uv run pytest --cov=binocular --cov-report=term-missing -q`.
- Frontend: 81.91% statements via `npm test -- --run --coverage`.
- Status: PASSED.

## Static Analysis — PASSED
- Backend tools: Ruff and mypy strict; critical issues: 0, warnings: 0.
- Frontend tools: TypeScript project build and ESLint; critical issues: 0, warnings: 0.

## Security Audit — PASSED
- Python tool: `pip-audit`; vulnerabilities found: 0 known vulnerabilities. Local package `binocular` was skipped because it is not on PyPI.
- Node tool: `npm audit --audit-level=critical`; vulnerabilities found: 0.

## Project Instructions Compliance — PASSED
- Honest Failure: PASSED — manual failures stay visible per-device with diagnostics.
- Polite by Default: PASSED — checks flow through `CheckService`, `ModuleRunner`, and `ScrapeClient`.
- Data Ownership & Self-Containment: PASSED — no external worker, database, broker, or telemetry added.
- Least-Privilege & Explicit Trust Boundary: PASSED — module trust boundary unchanged; no sandbox claim added.
- Type Safety & Correctness-First: PASSED — mypy strict, TypeScript, backend/frontend tests, and coverage passed.
- Set-and-Forget Reliability: PASSED — bulk partial failures are isolated and archived devices are excluded.

## Requirements Traceability — 3/3 work items verified, 5/5 SC verified
| ID | Type | Status | Notes |
|----|------|--------|-------|
| US1 | Work Item | PASSED | Single-device check API/UI tested; stored/latest/status/diagnostics displayed. |
| US2 | Work Item | PASSED | All-device endpoint tested for success, empty inventory, partial failure, missing module, archived exclusion. |
| US3 | Work Item | PASSED | Bulk running state tested; frontend remains usable while request is pending. |
| SC-001 | Success Criteria | PASSED | `runDeviceCheck` UI flow calls `/api/v1/checks/devices/{id}` and displays one result. |
| SC-002 | Success Criteria | PASSED | Manual result shows stored and latest versions with status. |
| SC-003 | Success Criteria | PASSED | Bulk endpoint returns independent per-device results and counts. |
| SC-004 | Success Criteria | PASSED | Backend partial-failure test verifies one failed result does not block success. |
| SC-005 | Success Criteria | PASSED | Delayed bulk UI test verifies running state and usable per-device controls. |

## Traceability Gaps
- None.

## Checklist Fulfillment — 3/3 spot-checked
- API Quality: PASSED — endpoints, payloads, error semantics, and traceability are implemented and tested.
- UX: PASSED — inventory-local module selector, single/bulk controls, empty/error/result states are covered.
- Performance: PASSED — bounded backend concurrency and delayed UI running-state behavior are implemented.

## Performance — PASSED
- Bulk execution uses a server-side concurrency clamp (`1..8`) with default 4.
- Backend and frontend automated tests cover partial failure and delayed bulk UI state.

## Accessibility — SKIPPED
- No explicit accessibility NFR was introduced by this feature.

## Browser Runtime Validation — PASSED
- Mode: Headless CLI supplement.
- Browser tool: React Testing Library with jsdom.
- App start: Not needed.
- Target: Inventory route rendered under `MemoryRouter`.
- Scenarios covered: single-device manual check, all-device check, delayed bulk running state, module route regression, inventory CRUD regression.

## Manual Testing — Not Required
- No `manual-test.md` generated.

## Tool Recommendations
- None.

## Bug Context
| Bug Task | Error Output | Stack Trace | Related Test |
|----------|-------------|-------------|--------------|
| — | — | — | — |

## Bug Tasks Generated
- None.
