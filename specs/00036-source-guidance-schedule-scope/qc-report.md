# QC Report: Sources

**Date**: 2026-10-07T08:25:29Z
**Feature Directory**: specs/00036-source-guidance-schedule-scope  
**Overall Verdict**: PASS

## Changes from Prior Run
| Metric | Previous | Current | Delta |
|--------|----------|---------|-------|
| Overall verdict | Local PASS (2026-10-07T08:14:43Z); subsequent hosted CI FAIL #37592881715 | Local PASS for T035 repair | Historical Git dependency removed and independently verified; hosted rerun not claimed. |
| Checked tasks / pending bugs | 34 / 0 | 35 / 0 | T035 completed by owning Implement; genuine `.completed` updated at 2026-10-07T08:22:52Z. |
| Backend tests / coverage | 480 / 87.20% | 480 / 87.20% | Unchanged; exact mandatory CI suite rerun. |
| Frontend tests | 83 | 83 | Exact mandatory frontend CI commands independently rerun; unchanged frontend. |
| Frontend statements / branches / functions / lines | 86.91 / 81.29 / 82.57 / 88.24% | Same retained prior scoped evidence | Coverage not rerun: no frontend/production changes. |
| Playwright scenarios / axe states / violations | 6 / 16 / 0 | Same retained prior scoped evidence | Browser/accessibility not rerun: only backend test/fixture changed. |
| Fully verified stories / SC | 4/4 / 6/6 | 4/4 / 6/6 | FR-011/FR-020 and SC-005 portability evidence refreshed; other results retained. |

- Scoped rerun: two changed test/fixture files and one subsequent hosted CI failure. Paths: `backend/tests/test_seeder.py`, `backend/tests/fixtures/sony_alpha/historical_module.txt`. `spec.md`/`plan.md` and frontend/production source unchanged; only T035 added/completed. Inline QC Auditor/Story Verifier review scoped to checkout-portability and preserved provenance/state assertions. Exact backend/frontend CI commands and Docker build independently rerun; prior unaffected browser/coverage/security evidence explicitly retained. No current gate regression; the historical local PASS missed the subsequently observed shallow-checkout defect, now repaired. No hosted CI rerun claimed.

## Summary
| Check | Status | Details |
|-------|--------|---------|
| Entry gates | PASSED | Parent-created `.completed` dated 2026-10-07T08:22:52Z; 35/35 tasks and 60/60 checklist items checked at rerun entry. Prior local PASS/hosted FAIL retained in comparison/log history. |
| Compilation / static analysis | PASSED | Strict mypy, strict TypeScript app/node build, Ruff and ESLint. |
| Tests / coverage | PASSED | New independent runs: five no-Git provenance cases, 480 pytest/87.20%, 83 Vitest. Prior unaffected frontend coverage and six Chromium scenarios retained. |
| Security / image | PASSED | New pip-audit and Docker build pass; rebuilt image has the same manifest as the previously scanned/non-root-verified image. Prior npm audit/Trivy/runtime evidence retained. |
| Requirements | PASSED | FR-011/FR-020 and SC-005 checkout-portability evidence refreshed; all other verified work items/SC retained. |
| Accessibility | PASSED | Retained unchanged-frontend evidence: axe-core 4.14.0, 16 light/dark desktop/375px states, zero violations/incomplete results, no suppressions. |
| QC feedback | PASSED | T033/T034/T035 resolved; no new bugs. Genuine `.completed` retained; stale `.qc-passed` replaced at 2026-10-07T08:28:27Z after final current gate verification. |

## Test Results — PASSED
- Runner: pytest 9.1.1; Total: 480, Passed: 480, Failed: 0. Command: `uv run pytest --cov=binocular --cov-report=term-missing` in `backend/`.
- Targeted runner: `uv run pytest tests/test_seeder.py -k provenance -v`: all five current/historical/unknown/missing/custom cases passed with `subprocess.check_output` patched to raise. Evidence: `.validation/qc-t035-no-git.log`. Historical case reads the checked-in `.txt` fixture; no Git history lookup remains.
- Runner: Vitest 4.1.11; Total: 83 across 17 files, Passed: 83, Failed: 0. Exact mandatory `npm run lint`, `npm run typecheck`, `npm test -- --run` independently rerun; `.validation/qc-t035-frontend.log`. Prior unchanged-frontend coverage/clean-install evidence retained: `.validation/qc-rerun-frontend-coverage.log` (347 packages installed, zero audit vulnerabilities).
- Retained prior runner: Playwright real Chromium; Total: 6, Passed: 6, Failed: 0. Not rerun for test-only T035. Prior `npx playwright test` used documented project-local font/library environment; desktop/375px workflow plus light/dark accessibility scenarios. Evidence: `.validation/qc-rerun-browser.log`, `frontend/test-results/source-guidance-{desktop,mobile}.png`, 16 `frontend/test-results/**/*-axe.json` results.
- New backend full rerun evidence: `.validation/qc-t035-backend.log`: 480 passed in 25.61s, no failed assertions, 87.20% coverage. Prior saved axe result verification retained; no new browser/axe execution represented by this report.
- SHA-256 independently checked for canonical capture and fixture: `ee30f81150e86c4b437cdb8f756100d950c8fe49fc96e6b975776c353ebaf319`, matching unchanged `HISTORICAL_SHIPPED["sony_alpha"]`. Existing five cases, state/schedule/provenance/byte-protection assertions preserved. This proves the repaired test does not require historical Git objects; no hosted CI success is asserted.

## Failure Index
| ID | Category | Severity | File:Line | Description | Bug Task |
|----|----------|----------|-----------|-------------|----------|
| None | All required categories | None | — | No current failures; historical A11Y-001/A11Y-002 and shallow-checkout test failure resolved by T033/T034/T035. | None |

## Code Coverage — Backend 87.20%; Frontend 86.91% statements
- Threshold: 80% from project instructions and derived QC policy; PASSED.
- Backend: 4,265 statements, 546 missed, 87.20%. Includes module-kit production files; no exclusion added by QC.
- Frontend retained prior evidence (not rerun): statements 86.91% (691/795), branches 81.29% (565/695), functions 82.57% (218/264), lines 88.24% (638/723). All four configured 80% thresholds passed; no frontend/production changes.
- Lowest backend coverage: module_kit/EXAMPLE_MODULE.py 0/72; module_kit/STARTER_TEMPLATE.py 0/27; spa.py 9/21; routes/notifications.py 62/90; services/notifier.py 91/118; official_modules/canon_rf_cameras.py 144/186; services/backup.py 32/41; official_modules/canon_rf_lenses.py 154/198; services/version_compare.py 48/61; services/checks.py 169/208. Paths relative to `backend/src/binocular/`.
- Frontend uncovered lines include main.tsx:6; components/inventory/device-card.tsx:36–41,73–82; components/modules/ModuleCard.tsx:40–51,133; pages/inventory.tsx and pages/logs.tsx. Aggregate coverage does not establish accessibility conformance.

## Static Analysis — PASSED
- Commands in `backend/`: `uv run mypy .` (strict configuration, 123 files, zero issues), `uv run ruff check .` (including configured security rules, zero issues).
- New commands in `frontend/`: `npm run lint`, `npm run typecheck`; zero compiler/lint issues. Prior `npm run build` strict app/node/production-build evidence retained; current Docker build also successfully reuses the identical Node22-built image.
- `git diff --check` passed before QC artifact generation. Compiler remains TypeScript 5.9.3; no policy waiver or source modification during QC. Source diff and repair tests reviewed inline under QC Auditor/Story Verifier role instructions; no nested agents.
- Supplemental local build/browser commands emit host Node DEP0205 and Playwright FORCE_COLOR/NO_COLOR environment notices; exact mandatory CI lint/typecheck/test commands emitted no warnings. The image's Node 22 build passed. These host-tool notices are retained, not application/runtime failures.

## Security Audit — PASSED
- New `uv run pip-audit`: no known vulnerabilities; `.validation/qc-t035-pip-audit.log`. Local `binocular 0.1.0` distribution is not on PyPI and cannot itself be dependency-audited. Ruff security rules and retained unchanged-image scanning supplement this explicit limitation.
- Retained prior `npm audit`: zero vulnerabilities; prior clean `npm ci` independently confirmed the unchanged lockfile installation and zero findings. No dependency changes in T035.
- Retained prior `trivy image --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed binocular:qc-check`: zero fixable HIGH/CRITICAL findings; no secrets detected. Unfixed/lower-severity findings are outside this release gate, not a claim of universal absence. Scanner severity-selection notice is metadata. Evidence: `.validation/qc-rerun-trivy.log`; current and prior Docker build manifests independently match `sha256:acdde9724752815dd393a2f3dd01259b11593f1fb1e876a928713ac98644890b`.
- Source URL actions validate absolute HTTP(S), forbid credentials/control characters, omit unsafe/absent links and use `noopener noreferrer`. Custom provenance requires host origin/hash proof; uploads do not inherit official claims. Warning explicitly states unsandboxed in-process full application privileges before upload/import.

## Docker Build Check — PASSED
- Command: `docker build --load -t binocular:qc-check -f Dockerfile .`.
- New status / Log Summary: successful build/load using policy-aligned Python 3.13-slim and Node 22; `.validation/qc-t035-docker.log`. Manifest `sha256:acdde9724752815dd393a2f3dd01259b11593f1fb1e876a928713ac98644890b` matches `.validation/qc-rerun-docker.log`; test-only fixture change is outside image production copy.
- Retained prior independent runtime commands on this unchanged image: default uid/gid 1000/1000; custom 1234/2345; `PUID=0` and `PUID=000` refused, each exit 1. Evidence: `.validation/qc-rerun-runtime.json`. Backend's 12 entrypoint regressions passed again in the new full suite.

## Project Instructions Compliance — PASSED
- No project-instruction violations identified. Visible scrape/save/count failures and last-success preservation; local SQLite migrations/provenance; existing centralized polite HTTP/cache controls; explicit unsandboxed trust warning and runtime non-root identities; strict Python/TypeScript and eight golden fixture suites; pause-generation fault isolation and persistence; production source roots and required quality gates remain intact.
- FR-018 repairs preserve type safety, source identity, source-wide scope and explicit unsandboxed trust boundaries; axe-core is development-only. No source changes, commits, pushes, PRs or deployments performed by QC.

## Requirements Traceability — 4/4 work items fully verified, 6/6 SC verified
| ID | Type | Status | Notes |
|----|------|--------|-------|
| US1 | Work Item P1 | PASSED | T007–T010: all eight fixture-backed declarations, evidence-matched labels/types/exclusions; source cards disclose stable internals separately. |
| US2 | Work Item P1 | PASSED | T011–T014: source-before-model in add/edit, describedby local help, Nikon XML/human distinction, safe links, stale generations, visible near-match error; RTL and Chromium evidence. |
| US3 | Work Item P1 | PASSED | T015–T022/T031: exact query member snapshots, zero/one/many tests, external membership refresh browser regression, all-current/future scope wording, truthful writes, deterministic pause/worker/restart/manual tests. |
| US4 | Work Item P2 | PASSED | T023–T028/T032–T034: custom/legacy state, omission/limits, kit/upload/AI-copy/sharing/trust workflows pass; persistent navigation names/current state and accessible light/dark status colors independently verified by RTL and real axe/Chromium. |
| SC-001 | Success Criteria | PASSED | Eight declarations and golden module suites match `official-guidance.md`; Canon boundaries and RF-S caveat retained. |
| SC-002 | Success Criteria | PASSED | Both rendered forms and RTL source/model/in-flight reset tests; unsafe links omitted and opener protection. |
| SC-003 | Success Criteria | PASSED | Scope API count equals exact member list; create/relink/delete and external browser refresh covered. |
| SC-004 | Success Criteria | PASSED | Deterministic dispatch/query/worker pause barriers, stale generation rejection, running work completion and manual paused checks/search; restart/edit/upload/seeding do not resume. |
| SC-005 | Success Criteria | PASSED | Additive migration/state snapshots and current/historical/unknown/missing/custom seeding matrix; T035 reruns all five provenance cases without Git history and preserves exact historical digest/state assertions. Prior legacy browser upload evidence retained. |
| SC-006 | Success Criteria | PASSED | Keyboard disclosures, 375px layout, invalid/omission feedback and workflows pass; original mobile navigation/status presentation gaps repaired. Six browser scenarios and 16 unsuppressed axe states pass. |
| FR-001 | Requirement | PASSED | T003; readable display projection distinct from name/file/ID; guidance/parser tests. |
| FR-002 | Requirement | PASSED | T007/T009; eight shipped declarations, golden fixtures and evidence table. |
| FR-003 | Requirement | PASSED | T007/T009; Panasonic lenses type corrected; Sony/Viltrox mixed coverage visible. |
| FR-004 | Requirement | PASSED | T007/T009; unchanged Canon matchers, exclusions and RF-S caveat. |
| FR-005 | Requirement | PASSED | T012/T013; both forms source-first/free-text/describedby. |
| FR-006 | Requirement | PASSED | T013/T014; generation guards cover stale success/error/finally/unmount. |
| FR-007 | Requirement | PASSED | T003/T011/T014; HTTP(S) validation, omission and opener protection; canonical source preserved. |
| FR-008 | Requirement | PASSED | T012; local metadata-only render; tests assert no new render requests. |
| FR-009 | Requirement | PASSED | T003/T006/T026; omitted V1 metadata and explicit type/length/count validation tested. |
| FR-010 | Requirement | PASSED | T005/T006/T026; host-controlled origin/hash projection, collision/direct-change protection. |
| FR-011 | Requirement | PASSED | T004/T008/T023/T026/T035; additive migration, protected bytes/state, omission clears official claim. T035 five-case provenance regression passes with Git subprocess forbidden and exact historical fixture digest preserved. |
| FR-012 | Requirement | PASSED | T015/T019/T022/T031; summary/scope refresh and membership tests, browser external change. |
| FR-013 | Requirement | PASSED | T020/T022/T031; all-current/future membership beside controls, no required inspection. |
| FR-014 | Requirement | PASSED | T013/T020; automatic-off/manual-available text in selections/cards; browser manual search while paused. |
| FR-015 | Requirement | PASSED | T016–T018/T021; DB recheck/thread-safe worker generation, neutral automatic skip and explicit resume. |
| FR-016 | Requirement | PASSED | T010/T027; guidance first, details disclosure, visible health/last-success. |
| FR-017 | Requirement | PASSED | T024/T025/T027/T032; kit/upload/validation/AI-copy manual fallback/sharing/trust warning regressions. |
| FR-018 | Requirement | PASSED | T025/T028/T029/T033/T034: named/current mobile navigation; theme-specific Official/active/Healthy/amber-failure colors; 16 axe states explicitly pass link-name and color-contrast with no incomplete findings; keyboard/help/layout regressions pass. |
| FR-019 | Requirement | PASSED | T019/T020 plus form/page tests; loading/empty/error/unknown counts and failed writes distinguished. |
| FR-020 | Requirement | PASSED | T009/T014/T021/T029/T030/T035; new independent backend full/targeted suites, frontend mandatory checks and Docker build pass. Historical golden fixture no longer requires old Git objects. Prior unchanged browser/axe evidence retained; hosted rerun not claimed. |

## Traceability Gaps
- No unmapped FR-001–FR-020 or US1–US4. T033/T034 remain resolved; T035 refreshes FR-011/FR-020 and SC-005 evidence. No remaining traceability gap. All 35 task IDs/states, phase headers and Dependencies preserved.

## Checklist Fulfillment — 20/20 security items spot-checked
- `checklists/security.md` CHK001–CHK006 PASSED: AST/runtime bounds, plain-text escaped output, safe actions and opener protection; metadata/URL tests.
- CHK007–CHK012 PASSED: pre-import unsandboxed/full-privilege warning, trusted-LAN boundary and host-derived provenance/collision tests.
- CHK013–CHK017 PASSED: canonical URL preservation, custom-claim clearing, local help, parameterized SQLite and development-only tooling.
- CHK018–CHK020 PASSED: offline metadata/provenance/security tests, independent audits/image scan and strict TS5/reproducible install.
- No separate `[Testing]` checklist category found. All three existing requirement-quality checklists remain 20/20 checked; actual FR-018 automation, not checkbox completion alone, establishes repair verification.

## Performance — PASSED
- No quantified performance NFR or required latency threshold found. Retained unchanged-runtime prior diagnostic: 20 successful local API calls, median 7.50 ms, p95 10.11 ms, max 32.91 ms; `.validation/qc-rerun-runtime.json`. Not rerun for a backend test/fixture-only repair; no SLA certification claimed.

## Accessibility — PASSED
- Scoped evidence retained from prior actual QC; frontend/production source unchanged. No new axe execution in T035 rerun.
- Owning Implement added axe-core 4.14.0 as a development dependency and committed-test-source regression in `frontend/e2e/source-accessibility.spec.ts`; QC made no source/dependency edits.
- Actual real Chromium audits: 16 states = desktop/mobile × light/dark × sources, scope/details/authoring, upload warning, add/source help. Zero violations and zero incomplete findings in independently parsed JSON results. Scan uses WCAG2/2.1/2.2 A/AA tags; no disabled rules or suppressions.
- Tests explicitly require both `link-name` and `color-contrast` to appear in passes and not incomplete. Names persist without tooltip opening; `aria-current=page` marks the current route. Official/active/Healthy/amber-failure presentation uses explicit light/dark semantic foreground tokens; browser scans cover both themes.
- Prior failure evidence remains in `.validation/qc-axe.json`; current raw evidence is 16 `frontend/test-results/**/*-axe.json` files and `.validation/qc-rerun-browser.log`. Existing keyboard/help/live-error/no-horizontal-overflow and add/edit functional assertions pass. Targeted automation is not a full-product WCAG or human screen-reader certification; no manual fallback substituted for valid automation.

## Browser Runtime Validation — PASSED
- Scoped evidence retained from prior actual QC; backend production/browser factory/frontend unchanged. Native/MCP probe and Chromium scenarios below describe the prior run, not new browser actions in T035 rerun.
- Mode: Headless CLI supplement.
- Browser tool: native `browser.snapshot` probe failed (no connected drivable OpenChamber client); MCP resource discovery returned no resources/templates or browser tools. `BROWSER_RUNTIME_AVAILABLE=false`; actual Playwright/Chromium available.
- App start: Playwright independently started isolated backend via `uv run --directory ../backend uvicorn tests.e2e_app:create_e2e_app --factory --host 127.0.0.1 --port 8001` and frontend via `npm run dev -- --host 127.0.0.1` with `VITE_API_TARGET=http://127.0.0.1:8001`; runner cleaned its servers after completion.
- Target: independent workflow/accessibility suites `http://127.0.0.1:5173`; supplemental API timing against parent's already-running isolated backend port 8002. Existing parent servers not stopped; no supplemental device mutations in this rerun.
- Scenarios: evidence labels/Canon caveat; source-first add/edit; stale near-match error reset; manual fixture search while paused; exact zero/one/two member inspection and external add/delete refresh; keyboard Details/Create a Module; kit download; trust warning; excessive metadata rejection; omission upload/custom provenance; 375px no horizontal clipping.
- Backend browser factory uses temporary SQLite/modules, stopped automatic scheduler, scripted transport rejecting unscripted requests and mocked notification delivery. Functional smoke restricts frontend requests to localhost; accessibility state projection is test-only and does not alter stored state. Workflow scenarios pass 2/2 and accessibility scenarios 4/4; no runtime failures in runner output. Earlier independent console/page-error check remains unchanged prior evidence, not a new console assertion claim.

## Manual Testing — Not Required
- Valid real Chromium and axe automation available; no `manual-test.md` generated. Original bugs genuinely repaired and automated checks rerun successfully.

## Tool Recommendations
- No required tool skipped. Scoped permanent accessibility regression now exists. Align optional host build runtime to CI Node 22 to avoid DEP0205 environment notices; image Node 22 build and all exact mandatory CI checks pass.

## Bug Context
| Bug Task | Error Output | Stack Trace | Related Test |
|----------|-------------|-------------|--------------|
| T033 (resolved) | Historical axe link-name failures retained in `.validation/qc-axe.json`; current audits zero violations and explicit link-name passes. | N/A: DOM audit; persistent aria-label/aria-current now present. | nav-item.test.tsx and source-accessibility.spec.ts; 83 RTL/Vitest tests and all six Chromium scenarios pass. |
| T034 (resolved) | Historical Official/active/Healthy contrast failures retained in `.validation/qc-axe.json`; current audits zero violations and explicit color-contrast passes, including amber-failure status in light/dark. | N/A: computed color audit; index.css semantic tokens used by ModuleCard/ModuleStatusBadge. | source-accessibility.spec.ts; 16 axe states pass without suppressions/incomplete findings. |
| T035 (resolved) | Hosted CI #37592881715 on 5a223df: exit 128, `fatal: invalid object name 'b1b8b99'`; `.validation/issue12-ci-failed.log`. Checked-in exact historical `.txt` bytes now used. | Historical Git check_output in former test_seeder.py:68; no production failure. | `.validation/qc-t035-no-git.log`: all five cases pass while subprocess.check_output raises; `.validation/qc-t035-backend.log`: 480 tests/87.20%. |

## Bug Tasks Generated
- None. T033/T034/T035 resolved; 35/35 tasks checked, no unchecked/deferred bugs. Genuine owning `.completed` retained. Stale `.qc-passed` from 2026-10-07T08:17:00Z replaced by owning QC at 2026-10-07T08:28:27Z after confirming this actual PASS report, final current task/fixture gates and clean git diff --check. Parent owns any subsequent commit/push/hosted CI rerun; no external action performed here.
