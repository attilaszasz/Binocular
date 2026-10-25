# QC Report: certifi Security Update

**Date**: 2026-10-25T08:36:01Z  
**Feature Directory**: specs/00036-certifi-security-update  
**Overall Verdict**: PASS

## Summary
| Check | Status | Details |
|-------|--------|---------|
| Phase gates | PASSED | .completed exists; T001–T004 checked; first QC run |
| Backend | PASSED | Frozen sync, Ruff, strict mypy, pytest and pip-audit independently rerun |
| Frontend | PASSED | ESLint, TypeScript and Vitest independently rerun |
| Dependency scope | PASSED | Only certifi and filelock changed; unrelated package records identical to HEAD |
| Image | PASSED | Local build and enforced Trivy scan independently rerun |
| Historical advisories | WARNING | Original npm ci reported 24 existing frontend advisories; unchanged dependencies, separate triage |

## Test Results — PASSED
- Runner: pytest 9.1.1; Total: 442, Passed: 442, Failed: 0.
- Runner: Vitest 4.1.11; Total: 35, Passed: 35, Failed: 0; 9 test files.
- Commands: `uv run --frozen pytest --cov=binocular --cov-report=term-missing --cov-report=json:/tmp/opencode/00036-qc/coverage.json`; `npm test -- --run`.
- Logs: `/tmp/opencode/00036-qc/backend-tests.log`, `/tmp/opencode/00036-qc/frontend.log`.

## Failure Index
| ID | Category | Severity | File:Line | Description | Bug Task |
|----|----------|----------|-----------|-------------|----------|
| — | — | — | — | No failures | — |

## Code Coverage — 86.85%
- Threshold: 80% (project instructions and derived QC policy).
- Status: PASSED; 4,016 statements, 528 missing.
- Lowest-coverage files (coverage; missing lines):
  - `src/binocular/module_kit/EXAMPLE_MODULE.py`: 0%; 72.
  - `src/binocular/module_kit/STARTER_TEMPLATE.py`: 0%; 23.
  - `src/binocular/spa.py`: 43%; 12.
  - `src/binocular/routes/notifications.py`: 69%; 28.
  - `src/binocular/official_modules/canon_rf_cameras.py`: 77%; 42.
  - `src/binocular/services/notifier.py`: 77%; 27.
  - `src/binocular/official_modules/canon_rf_lenses.py`: 77%; 44.
  - `src/binocular/services/backup.py`: 78%; 9.
  - `src/binocular/services/version_compare.py`: 79%; 13.
  - `src/binocular/routes/devices.py`: 82%; 8.

## Static Analysis — PASSED
- Commands: `uv run --frozen ruff check .`, `uv run --frozen mypy .`, `npm run lint`, `npm run typecheck`.
- Ruff: clean. mypy: 116 source files; `tool.mypy.strict = true`. ESLint and TypeScript: clean.
- Critical issues: 0; warnings from these verification commands: 0.

## Security Audit — PASSED
- `uv sync --frozen`: PASSED. Installed certifi 2026.10.23 and filelock 4.2.1 verified using importlib.metadata.
- `uv run --frozen pip-audit`: exit 0; no known vulnerabilities. The local unpublished application `binocular` is explicitly unauditable on PyPI; third-party dependency audit passed.
- `trivy image --quiet --severity HIGH,CRITICAL --ignore-unfixed --ignorefile .trivyignore --exit-code 1 --format json --output /tmp/opencode/00036-qc/trivy.json binocular:qc-check`: exit 0, zero reported vulnerabilities under the enforced policy. This does not assert absence of lower-severity or unfixed findings.
- Inspected real parent evidence `/tmp/opencode/binocular-certifi-filelock-trivy.json` and independently generated JSON; both identify the same rebuilt image and contain zero reported vulnerabilities.
- `uv export --frozen --no-dev --no-emit-project -o /tmp/opencode/00036-qc/production-requirements.txt`: certifi==2026.10.23 present, filelock absent. Runtime image independently confirms the same conditions.
- Historical warning retained: original Docker frontend-builder npm ci reported 24 existing advisories (8 moderate, 15 high, 1 critical). No frontend dependency changes; no fresh npm audit clearance is claimed. Independent cached Docker build and current CI-equivalent verification commands emitted no such warnings. These pre-existing builder/frontend findings remain separate triage, not concealed or repaired by this scoped update.

## Docker Build Check — PASSED
- Command: `docker build --load -t binocular:qc-check -f Dockerfile .`.
- Status / Log Summary: exit 0; cached build loaded successfully. Log: `/tmp/opencode/00036-qc/docker-build.log`.
- Manifest/image identifier: `sha256:41aa53c1f4fe843e27ca62b73225ca9085e8ffe08900cb01dcd0d52729ddbf23`.
- Exported image config: `sha256:63d86a64110df39e63f89efb5c8e0db85d3ba3aa74ea93d8f30cb0eb865811a9`.
- `docker run --rm --entrypoint python binocular:qc-check` metadata assertions passed: certifi 2026.10.23 installed; filelock not installed.

## Project Instructions Compliance — PASSED
- No violations introduced by this change. Runtime TLS dependency repair and development tooling floor only; no application, persistence, module, HTTP-client, privilege, UI or source-layout changes.
- Strict typing, required security checks, tests and coverage gates pass. Dockerfile, scanner workflow and .trivyignore match HEAD.
- Existing Alpine-versus-documented-slim discrepancy is unchanged; no new architecture change is approved or implied.
- No commit, push, publication, deployment, merge or pull request performed.

## Requirements Traceability — 1/1 work items verified, 2/2 SC verified
| ID | Type | Status | Notes |
|----|------|--------|-------|
| OBJ1 | Work Item | PASSED | Fixed frozen runtime certifi and enforced rebuilt-image scan; T001–T004 |
| TR-001 | Requirement | PASSED | T001 → backend/pyproject.toml runtime floor >=2026.10.19 → backend/uv.lock 2026.10.23 → frozen installed and image versions |
| TR-002 | Requirement | PASSED | T001,T004 → certifi 2026.6.17 → 2026.10.23; filelock 3.29.4 → 4.2.1; development floor >=4.2.1,<5; all other complete package records unchanged; scanner configuration unchanged |
| TR-003 | Requirement | PASSED | T002,T003,T004 → independent backend lint, strict typing, tests, coverage, full dependency audit, image build and enforced HIGH/CRITICAL scan |
| SC-001 | Success Criteria | PASSED | Frozen production export and runtime image contain fixed certifi; enforced rebuilt-image scan exits 0 |
| SC-002 | Success Criteria | PASSED | Backend checks pass; 86.85% >=80%; only authorized package changes |

## Traceability Gaps
- None. All requirements map to checked tasks, dependency artifacts and executed checks.
- Package comparison accounted for duplicate interpreter-specific package names using complete package records keyed by name, version and source; an initial name-only comparison was unsuitable and was corrected before verdict.

## Checklist Fulfillment — SKIPPED
- No checklists directory exists; not applicable.

## Performance — SKIPPED
- No performance NFR or behavior change in this dependency-only specification.

## Accessibility — SKIPPED
- No accessibility NFR or UI change in this specification.

## Browser Runtime Validation — SKIPPED
- Mode: Not required.
- Browser tool: Native `openchamber_web` actively probed with browser.snapshot; unavailable because no connected client can control a page. MCP resource discovery returned no resources or templates; no MCP browser tool exposed.
- BROWSER_RUNTIME_AVAILABLE: false.
- App start: Not needed. Target: N/A.
- No browser behavior or browser-dependent acceptance scenarios changed; automated dependency, backend, frontend and image checks cover the specified outcomes. No browser validation is claimed.

## Manual Testing — Not Required
- No uncovered runtime scenario requires manual verification; manual-test.md not generated.

## Tool Recommendations
- No required tooling missing. Separately triage the documented historical frontend advisories without expanding this dependency repair.

## Bug Context
| Bug Task | Error Output | Stack Trace | Related Test |
|----------|-------------|-------------|--------------|
| — | None | — | — |

## Bug Tasks Generated
- None.
