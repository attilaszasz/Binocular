# QC Report: Self-Hosted Operability (E008)

**Feature**: `specs/00008-self-hosted-operability/`
**Date**: 2026-06-10
**Overall Verdict**: PASS

## Test Results

| Runner | Tests | Passed | Failed | Skipped |
|--------|-------|--------|--------|---------|
| pytest 9.0.3 | 132 | 132 | 0 | 0 |

**Duration**: ~80s

## Static Analysis

| Tool | Issues |
|------|--------|
| ruff 0.8.x | 0 (all resolved) |
| mypy --strict | 0 (success in 30 source files) |

## Security Audit

- Dependency Audit: Checked dependencies using `pip-audit`, no known vulnerabilities found.
- Log Masking: Verified that sensitive log values are successfully masked via `mask_secrets_processor` in console and JSON logs.
- Password/Temporary files: Unsafe directory usage and hardcoded password warnings in test files are annotated and bypassed with `# noqa` comments.

## PI Compliance

Verified all project-instructions principles:
- zerorequired configuration defaults ✓
- database path configurable for custom SQLite volume mount ✓
- `_FILE` loading supports Docker secret injection, keeping passwords out of environment variables ✓
- basic auth middleware is disabled by default and liveness probe is unprotected ✓
- strict type safety with `mypy --strict` passing ✓
- no telemetry or data collection ✓

## Requirements Traceability

| Requirement | Status | Task(s) | Evidence |
|-------------|--------|---------|----------|
| FR-001 | ✅ PASS | T003 | Default paths, host, and port configured in `config.py` |
| FR-002 | ✅ PASS | T003, T007 | Configurable database path and resolution in `connection.py` |
| FR-003 | ✅ PASS | T004 | load_secret_files in `config.py` loads secret files via `_FILE` suffix envs |
| FR-004 | ✅ PASS | T004 | load_secret_files fails fast if path does not exist |
| FR-005 | ✅ PASS | T013, T014, T015 | Optional BasicAuthMiddleware implements HTTP basic authentication |
| FR-006 | ✅ PASS | T013, T015 | BasicAuthMiddleware bypasses /healthz probe requests |
| FR-007 | ✅ PASS | T005 | Settings fails fast on empty basic auth passwords |
| FR-008 | ✅ PASS | T008, T009, T010, T011, T012 | mask_secrets_processor filters logs and nested structures recursively |
| FR-009 | ✅ PASS | T002 | `.env.example` at repository root documents all parameters |

## Traceability Gaps

None.

## Code Coverage

- **Total coverage**: 92.24% (Required coverage target: 80%)
- **Modified / New modules coverage**:
  - `src/binocular/config.py`: 95%
  - `src/binocular/db/connection.py`: 96%
  - `src/binocular/auth.py`: 94%
  - `src/binocular/utils/masking.py`: 100%

## Checklist Fulfillment

Not applicable (Checklist phase skipped by hint).

## Performance

Not applicable — no performance criteria specified.

## Accessibility

Not applicable — backend-only feature.

## Browser Runtime Validation

Not applicable — backend-only feature.

## Manual Testing

Not required.

## Tool Recommendations

None.

## Bug Tasks Generated

None.
