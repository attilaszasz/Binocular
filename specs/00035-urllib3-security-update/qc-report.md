# QC Report: urllib3 Security Update

**Date**: 2026-10-04T06:13:57Z  
**Feature Directory**: specs/00035-urllib3-security-update  
**Overall Verdict**: PASS

## Changes from Prior Run
| Metric | Previous | Current | Delta |
|--------|----------|---------|-------|
| Verdict | FAIL | PASS | Authorized oauthlib remediation verified |
| Dependency audit findings | 1 | 0 | PYSEC-2026-4114 resolved |
| Backend tests | 442 passed | 442 passed | Unchanged |
| Frontend tests | 35 passed | 35 passed | Unchanged |
| Coverage | 86.85% | 86.85% | Unchanged |
| Enforced image vulnerabilities | 0 | 0 | Unchanged |

## Summary
| Check | Status | Details |
|-------|--------|---------|
| Backend tests / coverage | PASSED | 442 tests; 86.85%, threshold 80% |
| Frontend tests | PASSED | 35 tests across 9 files |
| Lint / strict typing | PASSED | Ruff, mypy, ESLint, tsc |
| Dependency audit | PASSED | No known vulnerabilities |
| Docker build / Trivy | PASSED | Image loaded; zero enforced findings |
| Requirements / runtime | PASSED | Fixed dependencies, unchanged other records/policy, healthy non-root app |

- Full rerun: user requested full verification; spec.md and plan.md changed. Initial `.completed` and task-completion gates passed.
- Context Gatherer, QC Auditor and Story Verifier invocations were depth-blocked. All checks were executed directly; no quality gate was skipped because of delegation.
- Evidence: ignored `backend/.venv/qc-evidence-rerun/`. No dependency edits, scanner changes, commit, push or publication performed by QC.

## Test Results — PASSED
- Backend runner: `uv run pytest --cov=binocular --cov-report=term-missing`; total 442, passed 442, failed 0, exit 0. Includes official-module fixtures and notification tests.
- Frontend runner: `npm test -- --run`; total 35, passed 35, failed 0; 9 files, exit 0.
- Additional runtime compatibility: requests-oauthlib OAuth1 signing and OAuth2 authorization/bearer-token preparation passed with oauthlib 4.0.0 without external requests.

## Failure Index
| ID | Category | Severity | File:Line | Description | Bug Task |
|----|----------|----------|-----------|-------------|----------|
| — | — | — | — | No failing gates | — |

## Code Coverage — 86.85%
- Threshold: 80%, project instructions and derived QC policy. Status: PASSED.
- 4,016 statements; 528 uncovered. Paths below are relative to backend/.
| Lowest-coverage file | Coverage | Uncovered statements |
|----------------------|----------|----------------------|
| src/binocular/module_kit/EXAMPLE_MODULE.py | 0% | 72 |
| src/binocular/module_kit/STARTER_TEMPLATE.py | 0% | 23 |
| src/binocular/spa.py | 43% | 12 |
| src/binocular/routes/notifications.py | 69% | 28 |
| src/binocular/official_modules/canon_rf_cameras.py | 77% | 42 |
| src/binocular/official_modules/canon_rf_lenses.py | 77% | 44 |
| src/binocular/services/notifier.py | 77% | 27 |
| src/binocular/services/backup.py | 78% | 9 |
| src/binocular/services/version_compare.py | 79% | 13 |
| src/binocular/routes/devices.py | 82% | 8 |

## Static Analysis — PASSED
- `uv run ruff check .`: exit 0; all checks passed.
- `uv run mypy .` and `uv run mypy --strict .`: exit 0; 116 source files, no issues.
- `npm run lint` and `npm run typecheck`: exit 0; TypeScript strict configuration unchanged.
- `uv lock --check` and `git diff --check`: exit 0.
- Critical issues: 0; command warnings: 0.

## Security Audit — PASSED
- `uv run pip-audit`: exit 0; no known vulnerabilities. Local binocular 0.1.0 is reported as unauditable because it is not on PyPI; application dependencies are audited.
- `trivy image --severity HIGH,CRITICAL --ignore-unfixed --ignorefile .trivyignore --exit-code 1 --format json --output backend/.venv/qc-evidence-rerun/trivy.json binocular:qc-check`: exit 0; zero enforced vulnerabilities and secrets.
- Neither CVE-2026-97687 nor CVE-2026-97689 appears in scan JSON. Scan workflow and ignore-file settings remain unchanged.
- This is a local rebuilt-image scan, not evidence of published-image or remote GitHub Actions results.

## Docker Build Check — PASSED
- Command: `docker build --load -t binocular:qc-check -f Dockerfile .`; exit 0, cached layers reused and image loaded.
- Image manifest: `sha256:8b286d2c72d923bf9c4580bc855d75e3223e8be60e51455e0c92c73f30acb5b7`.
- Frozen production synchronization is retained. Runtime confirms urllib3 2.8.0, oauthlib 4.0.0, requests/requests-oauthlib/Apprise and application-factory imports; pip absent in base and application interpreters.

## Project Instructions Compliance — PASSED
- No violations introduced by this implementation. Backend/frontend strict typing and fixture tests pass; application process UID/GID 1000/1000 verified.
- Application source, centralized HTTP policy, persistence, fault isolation and extension trust boundary are unchanged.
- Pre-existing Alpine-versus-documented-slim discrepancy is unchanged and outside this repair.

## Requirements Traceability — 1/1 work items verified, 2/2 SC verified
| ID | Type | Status | Notes |
|----|------|--------|-------|
| OBJ1 | Work Item | PASSED | Fixed frozen dependencies, pip removal, rebuilt image scan and runtime verified |
| TR-001 | Requirement | PASSED | T001/T004; urllib3>=2.8.0,<3 floor, locked/runtime 2.8.0; vendored pip copy removed |
| TR-002 | Requirement | PASSED | T001/T004/T005; only urllib3, authorized oauthlib 4.0.0 and root metadata changed; enforcement unchanged |
| TR-003 | Requirement | PASSED | T002/T003/T005; lint, strict typing, 442 tests, coverage and enforced image scan pass; dependency audit now passes |
| SC-001 | Success Criteria | PASSED | Frozen production urllib3 2.8.0; neither target CVE in enforced rebuilt-image scan |
| SC-002 | Success Criteria | PASSED | Existing backend gates pass, 86.85% coverage; no unauthorized package upgrades |

## Traceability Gaps
- None. All requirement IDs map to completed tasks and changed files. T005 captures the authorized oauthlib exception.
- Parsed lock comparison against HEAD: only binocular root metadata, oauthlib and urllib3 package records differ; 77 package records are identical. Prior unchanged-record counts must not be reused after the additional authorized upgrade.
- Scanner workflows, `.trivyignore`, frontend manifest and frontend lockfile are unchanged against HEAD.

## Checklist Fulfillment — SKIPPED
- No checklists found; not required for this workspace.

## Performance — SKIPPED
- No performance NFRs in this security-update specification.

## Accessibility — SKIPPED
- No accessibility NFRs or UI changes.

## Browser Runtime Validation — PASSED
- Mode: Terminal/headless supplement. Browser tool: N/A; rendered-UI scenarios are not required by this dependency/container-only specification.
- Active probe: `browser.snapshot` returned no connected OpenChamber client capable of page control. MCP discovery returned no resources/templates; no MCP browser tool is exposed. `BROWSER_RUNTIME_AVAILABLE=false`.
- App start: `docker run -d --name binocular-qc-00035-rerun binocular:qc-check`; default entrypoint. Target: `http://127.0.0.1:8000` inside the disposable container.
- Readiness/health 200 with status ok, SPA HTML 200, unsupported POST health method 405, dependency imports, OAuth client preparation and non-root application process passed.
- Container logs retain the pre-existing `official_module_validation_failed` warning for helper canon_endpoint_cache.py. All eight official modules load and readiness succeeds; this is not a failing CI command or a new regression.
- Disposable container removed; logs captured. Interactive rendering was not tested and is outside this specification.

## Manual Testing — Not Required
- Feature-specific dependency, scan and container checks are automated; no manual-test.md required.

## Tool Recommendations
- None. All required quality tools were available. Delegation/browser orchestration limitations did not leave a feature-specific validation gap.

## Bug Context
| Bug Task | Error Output | Stack Trace | Related Test |
|----------|-------------|-------------|--------------|
| T005 (resolved) | Prior oauthlib 3.3.1 PYSEC-2026-4114; current oauthlib 4.0.0 audit exit 0 | N/A | Dependency audit and OAuth client compatibility checks |

## Bug Tasks Generated
- None. All tasks remain checked; `.completed` retained. Current PASS evidence permits `.qc-passed` creation.
