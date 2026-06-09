## Research Report

**Context**: UX patterns for AI-assisted module authoring, downloadable developer kits, and AI-friendly error copy-paste for the Binocular extension module system.

## AI-Assisted Authoring UX

- **Key findings**: Structured prompt scaffolding outperforms raw instructions. Provide pre-written prompt templates and reference material that scope AI output to the project's exact contract. Self-contained kits (contract + template + example + instructions) allow any AI tool to produce valid output without project context.
- **Recommended**: Bundle the authoring contract reference, a starter template, a working example, and a structured AI prompt file as individually downloadable files plus a single .zip. Keep the AI instructions file tool-agnostic (works with ChatGPT, Claude, Cursor, etc.).
- **Avoid**: Embedding AI interaction into the app UI itself; keep the kit downloadable and offline-usable.
### Sources
- https://aiuxpatterns.com — structured prompt patterns for AI-assisted creation
- https://uxplanet.org — collaborative AI authoring UX patterns

## Error Copy-Paste for AI Tools

- **Key findings**: Developers frequently copy error messages into AI tools. Structured error blocks with error codes, messages, phase context, and fix instruction preambles are far more effective than raw error text. A single "Copy for AI" button should produce a pre-formatted block with all diagnostic context.
- **Recommended**: Format copied text as a structured block: error codes, messages, failed phase (static/runtime), the module contract summary, and a preamble instructing the AI to fix the errors. Include both human-readable and machine-parseable information.
- **Avoid**: Copying raw JSON; instead use a text format optimized for AI chat input.
### Sources
- https://medium.com — error message copy UX patterns
- https://temporal.io — structured error handling best practices

## Downloadable Kit Serving Strategy

- **Key findings**: Static file serving from FastAPI is straightforward via `StaticFiles` mount or direct file-response endpoints. Zip bundles can be generated at build time or on first request and cached. Individual file downloads are preferred for quick access; a .zip bundle for bulk download.
- **Recommended**: Serve kit files at `/api/v1/module-kit/` with individual endpoints per file and a `/api/v1/module-kit/bundle` endpoint for the .zip. Generate the .zip at startup or on first request.
- **Avoid**: Adding new backend dependencies; use stdlib `zipfile` module.
### Sources
- https://fastapi.tiangolo.com/advanced/custom-response/ — FastAPI file response patterns

### Summary
Self-contained AI kits with structured prompts produce higher-quality module output than documentation alone. AI-friendly error copy-paste should use a structured text format (not raw JSON) with error codes, phase context, and fix instruction preambles. Serve kit files as static content with no new dependencies.

### Sources Index
| URL | Topic | Fetched |
|-----|-------|---------|
| https://aiuxpatterns.com | AI authoring UX | 2026-06-09 |
| https://uxplanet.org | AI authoring UX | 2026-06-09 |
| https://medium.com | Error copy UX | 2026-06-09 |
| https://temporal.io | Error handling | 2026-06-09 |
| https://fastapi.tiangolo.com/advanced/custom-response/ | Kit serving | 2026-06-09 |
