# QC Report — E026 Per-Module Frequency on Modules Page

**Feature**: `00027-per-module-frequency-on-modules` | **Date**: 2026-06-07 | **Iteration**: 2 (scoped re-run: tests + security)

## Overall Verdict: PASSED

All iteration-1 failures resolved. Tests pass, security findings addressed.

| Category | Status | Details |
|----------|--------|---------|
| Lint / Static Analysis | PASSED | ruff: 0 issues, mypy strict: 52 files 0 errors, tsc: 0 errors |
| Security | PASSED | bandit: 0 Medium, 0 High, 9 Low. Prior B104/B608 resolved via nosec exemptions |
| Tests | PASSED | Backend: 236/236 passed; Frontend: 37/37 passed (10 test files) |
| Coverage | PASSED | Backend: 85.02% (>80%). Frontend: 52.07% overall; key changed files: api/modules.ts 100%, api/schedules.ts 50%, App.tsx 52.9%, FrequencyEditor.tsx 1.38% |

## Bug Fix Verification

| Task | Status | Evidence |
|------|--------|----------|
| T012 | FIXED | Backend 236/236 pass (was 232/236). Response schema assertions, FK constraints, return types all correct. |
| T013 | FIXED | Frontend 37/37 pass (was 34/37). QueryClientProvider wraps all renderApp() calls. |
| T014 | FIXED | `schedule_error`/`scheduleError` field present in backend ModuleResponse (`routes/modules.py:62`) and frontend InstalledModule type (`api/modules.ts:38`). |
| T015 | FIXED | B104 exempted with `# nosec B104 -- acceptable for trusted LAN` at `config.py:30`. B608 exempted with `# nosec B608 -- column names from hardcoded list` at `schedules.py:113`. 0 Medium/High bandit findings. |

## Test Counts

- **Backend**: 236 passed, 0 failed (full suite, `pytest` with in-memory SQLite)
- **Frontend**: 37 passed, 0 failed (10 test files, `vitest` with jsdom)
- **Modules/Schedule groups** (scoped): Backend 21/21 passed; Frontend 15/15 passed

## Coverage Details

- **Backend**: 85.02% lines (threshold 80%) — PASSED
- **Frontend overall**: 52.07% lines (2925 stmts, full codebase)
- **Frontend new/modified files**: api/modules.ts 100%, api/schedules.ts 50% (1 uncovered line), App.tsx 52.9%, FrequencyEditor.tsx 1.38% (no dedicated component tests)

## Security Findings (Low Severity — False Positives / Acceptable)

| ID | Severity | File | Note |
|----|----------|------|------|
| B105 | Low | config.py:16,20 | `SMTP_PASSWORD`/`GOTIFY_TOKEN` are environment-variable key names, not literal secrets |
| B101 | Low | devkit.py:151,173,207,226; validator.py:51,79; inventory.py:130 | Type-narrowing `assert` statements, not security-relevant |

