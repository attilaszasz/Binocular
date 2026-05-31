# QC Report: Self-Hosted Operability

**Date**: 2026-05-31T12:42:59Z  
**Feature Directory**: specs/00008-self-hosted-operability  
**Overall Verdict**: PASS

## Summary
| Check | Status | Details |
|-------|--------|---------|
| Backend lint | PASSED | `.venv/bin/python -m ruff check src tests` |
| Backend type-check | PASSED | `.venv/bin/python -m mypy` |
| Backend tests/coverage | PASSED | 65 passed; 90.99% coverage; threshold 80% |
| Backend security audit | PASSED | `pip-audit`; no known vulnerabilities found |
| Frontend lint | PASSED | `npm run lint` |
| Frontend type-check | PASSED | `npm run typecheck` |
| Frontend tests | PASSED | 4 files, 9 tests passed |
| Docker image build | PASSED | `docker build -t binocular:e013-qc .` |

## Test Results — PASSED
- Runner: pytest, Total: 65, Passed: 65, Failed: 0
- Runner: Vitest, Total: 9, Passed: 9, Failed: 0

## Failure Index
| ID | Category | Severity | File:Line | Description | Bug Task |
|----|----------|----------|-----------|-------------|----------|
| — | — | — | — | No failures. | — |

## Code Coverage — 90.99%
- Threshold: 80% from project instructions / derived QC policy
- Status: PASSED
- Uncovered files: `src/binocular/main.py` 0%, `src/binocular/repositories/inventory.py` 78%, `src/binocular/repositories/modules.py` 79%, `src/binocular/extensions/loader.py` 81%, all above total threshold context.

## Static Analysis — PASSED
- Tool: Ruff, mypy strict, TypeScript `tsc -b`, ESLint
- Critical issues: 0, Warnings: 0

## Security Audit — PASSED
- Tool: pip-audit
- Vulnerabilities found: 0
- Note: local editable package `binocular` is not on PyPI and was skipped by pip-audit as expected.

## Project Instructions Compliance — PASSED
- No violations.
- Data remains SQLite/local-volume only.
- Optional auth is documented as trusted-LAN light protection, not sandboxing or public-internet hardening.
- Type and lint gates passed for backend and frontend.

## Requirements Traceability — 4/4 work items verified, 6/6 SC verified
| ID | Type | Status | Notes |
|----|------|--------|-------|
| US1 | Work Item | PASSED | No-env health and SQLite persistence recreation tests passed. |
| US2 | Work Item | PASSED | Direct env, `_FILE`, missing, empty, and conflict settings tests passed. |
| US3 | Work Item | PASSED | Auth-off, auth-on challenge, valid credentials, health bypass, and static/API protection tests passed. |
| US4 | Work Item | PASSED | Compose, `.env.example`, and README deployment docs tests passed. |
| SC-001 | Success Criteria | PASSED | `test_no_env_startup_reaches_healthz`. |
| SC-002 | Success Criteria | PASSED | `test_sqlite_state_survives_app_recreation`. |
| SC-003 | Success Criteria | PASSED | `tests/test_config.py` secret cases. |
| SC-004 | Success Criteria | PASSED | `tests/test_auth.py` request behavior cases. |
| SC-005 | Success Criteria | PASSED | `test_compose_declares_single_port_and_volumes`. |
| SC-006 | Success Criteria | PASSED | `test_env_example_documents_auth_and_secret_defaults`. |

## Traceability Gaps
- None.

## Checklist Fulfillment — 11/11 spot-checked
- Security checklist: PASSED, 6/6 checked.
- Testing checklist: PASSED, 5/5 checked.
- Data Integrity checklist also present and complete, 5/5 checked.

## Performance — SKIPPED
- No performance NFRs in spec.

## Accessibility — SKIPPED
- No accessibility NFRs or UI changes in scope.

## Browser Runtime Validation — SKIPPED
- Mode: Not required
- Browser tool: N/A
- App start: Not needed
- Target: N/A
- Reason: E013 behavior is covered by ASGI request tests and deployment artifact checks; no new browser workflow or visual UI behavior.

## Manual Testing — Not Required
- No manual-test.md generated.

## Tool Recommendations
- None.

## Bug Context
| Bug Task | Error Output | Stack Trace | Related Test |
|----------|-------------|-------------|--------------|
| — | — | — | — |

## Bug Tasks Generated
- None.
