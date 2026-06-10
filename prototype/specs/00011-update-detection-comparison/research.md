# Research: Update Detection & Comparison
> Feature | 2026-05-31 | Inform comparison semantics, failure handling, and shared check-result contract.

## Version Comparison Semantics
- **Decision**: Use deterministic structured version comparison with explicit invalid-version failure.
- **Rationale**: Firmware strings often resemble semantic or PEP 440 versions, but unsafe comparisons must not be guessed.
- **Rejected**: Plain lexicographic string comparison because `1.10` sorts before `1.2` incorrectly.
- **Pitfalls**: Do not coerce unparseable vendor strings into a successful up-to-date result.
- **Sources**: https://packaging.python.org/en/latest/specifications/version-specifiers/, https://semver.org/

## Honest Failure and Check Results
- **Decision**: Persist each check as `up_to_date`, `update_available`, or `check_failed`, preserving previous `last_success_at` on failure.
- **Rationale**: Project principles require visible failures and prohibit silent missed updates.
- **Rejected**: Dropping failed module runs or clearing last successful evidence on failure.
- **Pitfalls**: Module errors, timeouts, invalid output, and unsafe versions must return structured failure without crashing the core.
- **Sources**: project-instructions.md, specs/sad.md

## Contract Shape for Downstream Workflows
- **Decision**: Define one typed backend `CheckResult` service/API shape consumed by future manual, scheduled, notification, and activity-log workflows.
- **Rationale**: E009 produces the shared contract for E010, E011, E012, and E014.
- **Rejected**: Workflow-specific status shapes because they invite contradictory comparison behavior.
- **Pitfalls**: Keep notification and activity-log concerns out of the comparison core.
- **Sources**: specs/project-plan.md, backend/src/binocular/extensions/contract.py

## Summary
| Topic | Decision | Rationale |
|-------|----------|-----------|
| Version Comparison Semantics | Structured comparison with explicit failure | Prevent false positives and false negatives |
| Honest Failure and Check Results | Persist visible status per attempt | Preserve unattended trust |
| Contract Shape for Downstream Workflows | One typed result shape | Stabilize dependent epics |

## Sources Index
| URL | Topic | Fetched |
|-----|-------|---------|
| https://packaging.python.org/en/latest/specifications/version-specifiers/ | Version Comparison Semantics | 2026-05-31 |
| https://semver.org/ | Version Comparison Semantics | 2026-05-31 |
| project-instructions.md | Honest Failure and Check Results | 2026-05-31 |
| specs/sad.md | Honest Failure and Check Results | 2026-05-31 |
| specs/project-plan.md | Contract Shape for Downstream Workflows | 2026-05-31 |
| backend/src/binocular/extensions/contract.py | Contract Shape for Downstream Workflows | 2026-05-31 |
