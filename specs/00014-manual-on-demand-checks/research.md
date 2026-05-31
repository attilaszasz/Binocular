# Research: Manual On-Demand Checks
> E010 | 2026-05-31 | Inform manual check architecture and UX-supporting implementation

## Manual Check UX
- **Decision**: Provide one-device and all-device controls with a module selector and per-device result cards.
- **Rationale**: Operators need immediate side-by-side stored/latest visibility without leaving inventory.
- **Rejected**: Separate manual-check page because it duplicates inventory context and slows repeated use.
- **Pitfalls**: Avoid replacing domain failures with generic transport errors.
- **Sources**: specs/prd.md, specs/00011-update-detection-comparison/spec.md

## Bulk Execution
- **Decision**: Use bounded async concurrency inside the existing FastAPI process.
- **Rationale**: The workload is I/O-bound and must remain self-contained without an external broker.
- **Rejected**: Background queue infrastructure because it violates the small single-process increment.
- **Pitfalls**: Do not let one device failure cancel the entire batch.
- **Sources**: specs/sad.md, backend/src/binocular/services/checks.py

## Integration Context
- **Decision**: Extend E009 `CheckService`, `/api/v1/checks`, and typed frontend API clients.
- **Rationale**: Reusing the shared `CheckResult` contract prevents status drift across manual and scheduled workflows.
- **Rejected**: New manual-only result model because E009 already owns detection semantics.
- **Pitfalls**: Existing single-device checks require `moduleId`; E010 should expose module selection instead of inventing hidden association.
- **Sources**: backend/src/binocular/routes/checks.py, frontend/src/api/inventory.ts

## Summary
| Topic | Decision | Rationale |
|-------|----------|-----------|
| Manual Check UX | Inventory-local controls and result cards | Keeps stored/latest comparison in context |
| Bulk Execution | Bounded async concurrency | Preserves single-process self-hosted model |
| Integration Context | Extend E009 contracts | Avoids duplicate status semantics |

## Sources Index
| URL | Topic | Fetched |
|-----|-------|---------|
| specs/prd.md | Manual Check UX | 2026-05-31 |
| specs/sad.md | Bulk Execution | 2026-05-31 |
| specs/00011-update-detection-comparison/spec.md | Integration Context | 2026-05-31 |
