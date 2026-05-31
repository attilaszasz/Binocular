# Research: Module Lifecycle Management
> E008 | 2026-05-31 | Inform lifecycle API, upload validation, and UI feedback decisions.

## Upload Gating
- **Decision**: Stage uploads outside the active modules directory, enforce `.py` and 1..256 KiB limits, then validate before install.
- **Rationale**: Reject-before-save prevents invalid trusted code from becoming runnable.
- **Rejected**: Direct writes to `/app/modules` because failed validation could leave active bad files.
- **Pitfalls**: Do not trust client filenames or paths for active module placement.
- **Sources**: https://fastapi.tiangolo.com/tutorial/request-files/, specs/00007-module-engine-contract/spec.md

## Lifecycle Feedback
- **Decision**: Return stored module metadata plus structured static/runtime validation summaries.
- **Rationale**: Operators need phase-level failure detail to repair modules without silent misses.
- **Rejected**: Generic upload errors because they hide whether static or runtime proof failed.
- **Pitfalls**: Avoid stale UI state after upload, update, or delete actions.
- **Sources**: specs/00007-module-engine-contract/data-model.md, frontend/src/App.tsx

## Safe Replacement And Deletion
- **Decision**: Treat duplicate module IDs as updates, preserve the previous active file until replacement validates, and delete metadata plus source together.
- **Rationale**: Manufacturer pages change, so repairs must not corrupt a working module.
- **Rejected**: Duplicate installed copies because they create ambiguous module selection.
- **Pitfalls**: Do not delete metadata while leaving file-removal failures invisible.
- **Sources**: specs/sad.md, project-instructions.md

## Summary

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Upload Gating | Stage and validate before active install | Invalid trusted code must never become runnable. |
| Lifecycle Feedback | Return phase summaries | Honest failure requires actionable feedback. |
| Safe Replacement And Deletion | Update by module ID and preserve previous file on failure | Operators need safe module repairs. |

## Sources Index

| URL | Topic | Fetched |
|-----|-------|---------|
| https://fastapi.tiangolo.com/tutorial/request-files/ | Upload Gating | 2026-05-31 |
| specs/00007-module-engine-contract/spec.md | Upload Gating | 2026-05-31 |
| specs/00007-module-engine-contract/data-model.md | Lifecycle Feedback | 2026-05-31 |
| frontend/src/App.tsx | Lifecycle Feedback | 2026-05-31 |
| specs/sad.md | Safe Replacement And Deletion | 2026-05-31 |
| project-instructions.md | Safe Replacement And Deletion | 2026-05-31 |
