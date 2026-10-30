# T029–T031 Bug-Fix Validation

## Execution Context

- Authorized resume on 2026-10-30; same branch and feature workspace, AUTOPILOT=true. Original validation and halted QC evidence remain unchanged.
- Context Gatherer, Task Tracker and Developer invocations each failed with `Subagent depth limit reached (1). Increase "experimental.subagent_depth" to allow nested subagents.` No delegated results were fabricated. Local fixes and actual validation continue; parent-session independent QC delegation remains required.
- Native browser snapshot actively failed because no drivable OpenChamber client is connected. MCP resource discovery returned no resources/templates. Real Playwright CLI uses the project-local library/font environment documented in [validation-results.md](validation-results.md).

## Fixes and Regression Oracles

- T029: Append-only `0012_v1_check_attempt.sql`; independent attempt time and failed comparison projection, no freshening retained successful time. API exposes attempt time; reloaded cards show failure and reference-only firmware. Six direct/background failed-check cases reopen the migrated file and read the service response; two remount cases include installed-unknown failure. Browser scenarios add real fixture verification failure after successful Current, out-of-band API check, full reload and persisted-state assertions.
- T030: Supplied clock, latest attempt, current config and strict module interval determine fresh/failed/stale eligibility while retaining observations. 28 cases cover current/update/no-firmware outcomes versus failure/unsupported/cancellation/running/expiry/missing schedule, with reopen assertions. A strict freshness-boundary crossing rolls effects and cursor back. Existing config mismatch case now asserts retained stale reference, not erased knowledge.
- T031: Task/process registration UUIDs are host-generated non-init fields; copy/rebind receives a distinct identity, explicitly replacing the UUID is rejected. Two actual blocked-task/blocked-process cases reject unrelated completed execution proof without changing durable state, then allow retry only after the original execution actually terminates.
- No network inside write units, no V1 enqueue activation, no new application workers or runtime queues, no historical SQL edits.

## Initial Failures and Corrections

- Focused run: strict mypy passed; Ruff found two overlong lines, corrected without suppression. Pytest: 276 passed, six failed (three old failed-check oracles expected timestamp freshening/actionable update; three expected ValueError instead of Python 3.13 TypeError for init=False replacement). Corrected those assertions. Initial `tee` used a missing evidence directory because `mkdir` was relative to backend; terminal output is the source of these counts, not a nonexistent log. Removed only the mistakenly created empty directories.
- Initial full backend: 1,378 passed, six failed, coverage 90.41%. Four migration count/version assertions needed the added 0012 migration; failed-check concurrency oracle needed independent attempt time. One pre-existing immediate driver-thread `is_alive` assertion raced aiosqlite's stop future; test now joins that exact stopped thread before asserting termination, without sleeps or changing busy-wait tolerances. [Actual log](../../artifacts/00037-validation/bugfix-r1/backend-pytest-initial-full.log).
- Initial browser: six passed, four failed because test-only failure-control URL was not under Vite's API proxy. Moved fixture-only route and calls under `/api/v1/e2e/`; production application never registers that route. Assertions were not weakened. [Actual log](../../artifacts/00037-validation/bugfix-r1/playwright-initial.log); [initial evidence archive](../../artifacts/00037-validation/bugfix-r1/playwright-initial-evidence.tar.gz).

## Final Validation

| Working directory | Command | Exit | Result | Evidence |
|---|---|---:|---|---|
| `backend/` | `uv run ruff check .` | 0 | Clean after final line wrap | [Ruff](../../artifacts/00037-validation/bugfix-r1/backend-ruff-verified.log) |
| `backend/` | `uv run mypy --strict .` | 0 | 150 source files clean | [mypy](../../artifacts/00037-validation/bugfix-r1/backend-mypy-verified.log) |
| `backend/` | `uv run pytest -W error --cov=binocular --cov-report=term-missing --cov-report=xml:../artifacts/00037-validation/bugfix-r1/backend-coverage-verified.xml --cov-fail-under=80` | 0 | 1,385 passed in 160.16s; 90.41% (5,938/6,568 statements); warnings-as-errors | [Regression](../../artifacts/00037-validation/bugfix-r1/backend-pytest-verified.log), [coverage](../../artifacts/00037-validation/bugfix-r1/backend-coverage-verified.xml) |
| `backend/` | `uv run pip-audit` | 0 | No known vulnerabilities; unpublished local binocular package unauditable | [Audit](../../artifacts/00037-validation/bugfix-r1/backend-pip-audit.log) |
| `backend/` | `uv run pytest -W error tests/test_official* -q` | 0 | 163 passed | [Fixtures](../../artifacts/00037-validation/bugfix-r1/backend-official-fixtures.log) |
| `backend/` | `uv run pytest -W error tests/db/test_catalog_performance.py -v --durations=10` | 0 | Seven passed; 10,000-model/device bounds | [Performance](../../artifacts/00037-validation/bugfix-r1/backend-performance.log) |
| `backend/` | `uv run pytest -W error tests/db/test_catalog_security.py -q` | 0 | 235 passed | [Security regressions](../../artifacts/00037-validation/bugfix-r1/backend-security.log) |
| `frontend/` | `npm run lint`; `npm run typecheck` | 0 each | Clean | [Lint](../../artifacts/00037-validation/bugfix-r1/frontend-lint-final.log), [typecheck](../../artifacts/00037-validation/bugfix-r1/frontend-typecheck-final.log) |
| `frontend/` | `npm test -- --run --coverage` | 0 | 17 files / 120 passed; statements 88.46%, branches 84.47%, functions 84.96%, lines 89.77%; each ≥80% | [Vitest](../../artifacts/00037-validation/bugfix-r1/frontend-vitest.log), [coverage](../../artifacts/00037-validation/bugfix-r1/frontend-coverage.xml) |
| `frontend/` | `npm run build` | 0 | Production SPA built | [Build](../../artifacts/00037-validation/bugfix-r1/frontend-build.log) |
| `frontend/` | `npm audit --json` | 0 | Zero known dependency vulnerabilities | [Audit](../../artifacts/00037-validation/bugfix-r1/frontend-audit.json) |
| `frontend/` | `npx playwright test` with documented local LD_LIBRARY_PATH/FONTCONFIG_FILE | 0 | 10 passed; 40 axe audits, zero violations/incomplete | [Browser](../../artifacts/00037-validation/bugfix-r1/playwright-final.log), [summary](../../artifacts/00037-validation/bugfix-r1/playwright-evidence-summary.json), [raw evidence](../../artifacts/00037-validation/bugfix-r1/playwright-final-evidence.tar.gz) |
| Root | `docker build --load -t binocular:qc-check -f Dockerfile .` | 0 | Actual image built/loaded; manifest `sha256:03b596fb2abab2bd649a7a9e1d231ea13eaab1a98320bf2bdd1586fbdea74671` | [Docker](../../artifacts/00037-validation/bugfix-r1/docker-build-verified.log), [inspection](../../artifacts/00037-validation/bugfix-r1/docker-image-inspect-verified.json) |
| Root | `trivy image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 binocular:qc-check` | 0 | Zero applicable fixable HIGH/CRITICAL vulnerabilities; not a claim about excluded severities/unfixed findings | [Trivy](../../artifacts/00037-validation/bugfix-r1/trivy-verified.log) |
| Root | `git diff --check` | 0 | Clean | [Diff](../../artifacts/00037-validation/bugfix-r1/diff-check.log) |

- Second full backend run passed 1,385 tests with warnings-as-errors. Its coverage reported 90.13% after the final Ruff line-wrap changed source line mapping while that run was active. Preserve [that run](../../artifacts/00037-validation/bugfix-r1/backend-pytest-final.log), but use the subsequent unchanged-source verified rerun for authoritative coverage. No product-source changes are made during that final rerun.
- Four ordinary-form network records retain vendor counts 0→0, 8→8, 17→17 and 24→24, with zero external browser requests or firmware actions. Four new persisted-failure reload axe audits are included in the total of 40. Browser-owned ports 8001/5173 were confirmed closed after Playwright cleanup.
- Existing Vite future-native-loader advisory, Node 26 DEP0205/color environment notices, Trivy severity-source notice and pip-audit local-package limitation are retained in logs; no warning suppression or behavioral waiver was added. These are not silently omitted from QC consideration.
- Final validated production-source hashes: [SHA-256](../../artifacts/00037-validation/bugfix-r1/validated-source-sha256.txt).

## Workflow State

Independent QC delegation is required from the parent session because nested agents cannot run here. No QC PASS or E032 completion is claimed by this implementation validation report. Existing `qc-report.md` remains the historical FAIL until the genuine QC workflow replaces it.

All 31 tasks are checked only after actual validation; Implement recreated `.completed` at 2026-10-30T12:04:08+02:00. `.qc-passed` remains absent. No manual-test artifact, deferred bug, commit, push or publication was created. E032 remains unchecked pending independent QC.
