# Implementation Validation Results — T028

## Execution Context

- Date: 2026-10-30. Repository: `/workspace/Binocular`; feature `00037-catalog-persistence-and-write-ownership`.
- Real local execution; Python 3.13.18, Node 26.13.0, npm 11.20.0. No system installs, waived behavioral gates, fabricated results, task-state edits, completion markers or QC markers.
- Evidence paths below are relative to this document. Full output: [validation artifacts](../../artifacts/00037-validation/).
- Exact tool/image-scanner database versions: [tool versions](../../artifacts/00037-validation/tool-versions.log). Docker's real daemon is reachable through the configured proxy; image build/load and scanning were executed, not simulated.

## Gate Results

| Working directory | Command | Exit | Count / coverage / outcome | Evidence |
|---|---|---:|---|---|
| `backend/` | `uv run ruff check .` | 0 | No findings | [Ruff](../../artifacts/00037-validation/backend-ruff-final.log) |
| `backend/` | `uv run mypy --strict .` | 0 | 150 source files; no issues | [mypy](../../artifacts/00037-validation/backend-mypy-final.log) |
| `backend/` | `uv run pytest -W error --cov=binocular --cov-report=term-missing --cov-report=xml:../artifacts/00037-validation/backend-coverage-final.xml --cov-fail-under=80` | 0 | 1,350 passed in 153.62s; 90.43% coverage (5,923/6,550 statements); warnings treated as errors | [Final regression](../../artifacts/00037-validation/backend-pytest-final.log); [coverage XML](../../artifacts/00037-validation/backend-coverage-final.xml); [initial regression](../../artifacts/00037-validation/backend-pytest.log) |
| `backend/` | `uv run pip-audit` | 0 | No known vulnerabilities; local unpublished `binocular` is reported as unauditable, not silently ignored | [Audit](../../artifacts/00037-validation/backend-pip-audit-final.log) |
| `backend/` | `uv run pytest -W error tests/extensions/test_runner.py tests/routes/test_checks_routes.py -q` | 0 | 20 passed | [Runner/search regressions](../../artifacts/00037-validation/backend-runner-regression.log) |
| `backend/` | `uv run pytest -W error tests/test_official* -q` | 0 | 163 passed in 1.63s; full suite also retains Canon/source fixture regressions outside this filename glob | [Official fixtures](../../artifacts/00037-validation/backend-official-fixtures-final.log) |
| `backend/` | `uv run pytest -W error tests/db/test_catalog_performance.py -v --durations=10` | 0 | 7 passed in 5.68s; 10,000-model/device bounds, WAL, restart and budgets | [Performance](../../artifacts/00037-validation/backend-performance-final.log) |
| `backend/` | `uv run pytest -W error tests/db/test_catalog_security.py -q` | 0 | 235 passed in 25.90s; real SQL/identity/credential persistence regressions | [Security regressions](../../artifacts/00037-validation/backend-security-final.log) |
| `frontend/` | `npm run lint` | 0 | ESLint clean | [Lint](../../artifacts/00037-validation/frontend-lint-final.log) |
| `frontend/` | `npm run typecheck` | 0 | Strict project build (`tsc -b`) clean | [Typecheck](../../artifacts/00037-validation/frontend-typecheck-final.log) |
| `frontend/` | `npm test -- --run --coverage` | 0 | 17 files / 118 tests passed; statements 88.46% (721/815), branches 84.21% (624/741), functions 84.96% (226/266), lines 89.77% (667/743); every threshold ≥80% | [Vitest](../../artifacts/00037-validation/frontend-vitest-final.log); [coverage XML](../../artifacts/00037-validation/frontend-coverage.xml) |
| `frontend/` | `npm run build` | 0 | Production SPA built | [Build](../../artifacts/00037-validation/frontend-build-final.log) |
| `frontend/` | `npm audit --json` | 0 | Zero vulnerabilities at every severity | [Audit](../../artifacts/00037-validation/frontend-audit-final.log); [resolved versions](../../artifacts/00037-validation/frontend-patched-dependencies.log) |
| `frontend/` | `npx playwright test` (local library/font environment below) | 0 | 10 passed (desktop/mobile, light/dark); 36 axe audits, zero violations and zero incomplete checks | [Playwright](../../artifacts/00037-validation/playwright-final.log); [axe/network summary](../../artifacts/00037-validation/playwright-evidence-summary.json); [raw browser evidence](../../artifacts/00037-validation/playwright-evidence.tar.gz) |
| repository root | `docker build --load -t binocular:qc-check -f Dockerfile .` | 0 | Actual image built and loaded; manifest `sha256:54c83a271ce6f218cae54dc1c93445d686dc81ccb039c04012b8fa57576d70a4` | [Build](../../artifacts/00037-validation/docker-build-final.log); [image inspection](../../artifacts/00037-validation/docker-image-inspect.json) |
| repository root | `trivy image --severity HIGH,CRITICAL --ignore-unfixed --exit-code 1 binocular:qc-check` | 0 | Zero applicable fixable HIGH/CRITICAL findings in built image | [Trivy](../../artifacts/00037-validation/trivy-final.log) |
| repository root | `git diff --check` | 0 | No whitespace errors | [Diff check](../../artifacts/00037-validation/diff-check.log) |

## Browser and Acceptance Evidence

Playwright used existing project-local extracted libraries/fonts; no system packages installed:

```sh
# cwd: /workspace/Binocular/frontend
export LD_LIBRARY_PATH="$PWD/node_modules/.cache/playwright-deps/root/usr/lib/x86_64-linux-gnu:$PWD/node_modules/.cache/playwright-deps/root/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export FONTCONFIG_FILE="$PWD/node_modules/.cache/playwright-deps/fonts.conf"
npx playwright test
```

- Existing Playwright configuration starts the real fixture-backed backend and Vite server; `/healthz` is the configured startup readiness endpoint. Official Sony HTML is served through the centralized injected HTTP transport, not a fabricated firmware result. Unscripted outbound requests fail closed; notifications use the existing test dispatcher.
- Keyboard/error/form/search-reference/inventory unknown and incomparable states pass existing assertions without weakening expectations. Axe runs WCAG 2/2.1/2.2 A/AA; link-name and color-contrast rules must pass without incomplete findings.
- Four ordinary-form network records show unchanged backend vendor-request counts (0→0, 7→7, 15→15, 21→21), zero external browser requests and zero firmware-check actions. Explicit user-triggered searches are tested separately and must increase vendor counts.
- Raw axe and network JSON are preserved in the compressed browser evidence archive; duplicate Playwright attachment copies are omitted. Frontend coverage XML is copied from the actual final Vitest output.
- Performance source oracles use 10,000 catalog models and 10,000 linked devices in real migrated SQLite, default-50/max-100 pagination, complete duplicate-free cursor traversal, bounded 50/100-device atomic chunks, independent WAL reads during writes, rollback, deadline/budget persistence across reopen, and fail-closed socket/HTTP guards. This backend foundation introduces no catalog-rendering UI; existing inventory UI is covered by browser smoke.

## Findings and Fixes

- Initial `npm audit --json`: exit 1, six vulnerable development packages (three high, three moderate). Installed exact Vite 8.3.5 and matching Vitest/coverage 4.1.12, updated lock-resolved undici to 7.30.1 and zod to 4.6.7. Commands: `npm install --save-dev --save-exact vite@8.3.5 vitest@4.1.12 @vitest/coverage-v8@4.1.12` and `npm update undici zod`, both successful. No audit exclusions, threshold reductions or forced major upgrades. [Initial audit](../../artifacts/00037-validation/frontend-audit.log).
- Initial `uv run pip-audit`: exit 1, msgpack 1.2.1 / CVE-2026-114613 (fixed ≥1.2.3). `uv lock --upgrade-package msgpack` and `uv sync --frozen` updated the project lock/environment to 1.2.4, exit 0. Final audit clean. [Initial audit](../../artifacts/00037-validation/backend-pip-audit.log); [update](../../artifacts/00037-validation/backend-dependency-update.log).
- Initial browser run: exit 1, six failed / four passed. Sanitization had erased the existing missing-product label, returning only `Module runner failed`. Runner now retains only three code-owned ValueError labels, never raw provider text; stateless search propagates only those labels. Added five credential/prefix-lookalike regressions. Existing browser assertions remain unchanged. The official Sony fixture assertion now requires the safe missing-product label while still requiring generic exception text. [Initial browser failure](../../artifacts/00037-validation/playwright.log); [intermediate fixture failure](../../artifacts/00037-validation/backend-official-fixtures.log).
- A new 90-character line failed Ruff during focused verification; wrapped before final Ruff rerun. No suppression added.
- Updated [data model](data-model.md) and [write ownership audit](write-ownership-audit.md) with as-built exact execution-registration/stoppage matching and origin-only URL/allowlisted error/redacted receipt/release-note policies. IDs, constraints, no-worker and no-V1-enqueue boundaries are preserved.

## Limitations

- No mandatory gate remains blocked or unexecuted. Initial/intermediate failures above are retained as history, not substituted for final passes.
- Browser tooling emits existing NO_COLOR/FORCE_COLOR and Node DEP0205 warnings, plus Vite's future native-config-loader advisory about `__dirname`; browser assertions pass. Backend full regression explicitly treats warnings as errors. Existing frontend DEP0205 test-script setting was not changed.
- Trivy evidence applies to fixable HIGH/CRITICAL vulnerabilities under the required `--ignore-unfixed` command; it is not a claim that lower severities or unfixed issues do not exist.
- This is implementation validation, not QC approval or a release-ready claim. No `.completed`, `.qc-passed` or `qc-report.md` created.

## Authorized T029–T031 Resume

- Original results above remain historical. Current repairs, regressions, command logs and lifecycle state are recorded in [bug-fix-results.md](bug-fix-results.md) and [bug-fix evidence](../../artifacts/00037-validation/bugfix-r1/).
- The three original QC findings are not waived by previous passing suites. Independent QC must verify the repaired failed-attempt/reload, observation freshness and exact execution-binding oracles before E032 can pass.
