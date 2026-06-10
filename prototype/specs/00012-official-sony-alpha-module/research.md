# Research: Official Sony Alpha Module
> E015 | 2026-05-31 | Plan fixture-backed official module implementation

## Module Contract Integration
- **Decision**: Implement Sony support as a bundled Python module conforming to `binocular.extensions.contract`.
- **Rationale**: Existing module runner/check service already owns timeout, failure mapping, and ScrapeClient injection.
- **Rejected**: Adding a Sony-specific core service because official modules should remain reference extensions.
- **Pitfalls**: Do not bypass the host scraping client or rely on live network access in CI.
- **Sources**: specs/00007-module-engine-contract/plan.md, specs/00011-update-detection-comparison/plan.md

## Fixture Correctness
- **Decision**: Use captured Alpha Universe firmware-index fixtures and tests that assert exact latest-version results for cameras and lenses.
- **Rationale**: Project policy requires official modules to prove zero false positives/negatives without telemetry.
- **Rejected**: Live Sony page tests because CI would become flaky and impolite.
- **Pitfalls**: Keep missing catalog, unlisted product, and no-firmware cases visible as failures rather than defaulting to no update.
- **Sources**: specs/prd.md, project-instructions.md

## Summary
| Topic | Decision | Rationale |
|-------|----------|-----------|
| Module Contract Integration | Bundled contract-compatible module | Reuses existing trusted extension path. |
| Fixture Correctness | Captured Alpha Universe golden tests | Deterministic release validation. |

## Sources Index
| URL | Topic | Fetched |
|-----|-------|---------|
| specs/00007-module-engine-contract/plan.md | Module Contract Integration | 2026-05-31 |
| specs/00011-update-detection-comparison/plan.md | Module Contract Integration | 2026-05-31 |
| specs/prd.md | Fixture Correctness | 2026-05-31 |
| project-instructions.md | Fixture Correctness | 2026-05-31 |