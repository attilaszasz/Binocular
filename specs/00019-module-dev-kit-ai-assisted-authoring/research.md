## Research Report

**Context**: Best practices for module/plugin developer kits, AI-assisted authoring guidance, and in-app developer onboarding patterns for a self-hosted extension-based application.

## Developer Kit Structure & Content

- **Key findings**: Effective dev kits include a quickstart guide, contract reference, starter template, and a working example. Copy-pasteable code is the #1 adoption driver. Structure as: getting-started → contract reference → template → example.
- **Recommended**: Ship a minimal but complete starter template alongside a real working example (Sony Alpha). Include inline comments explaining each contract requirement. Keep the template under 50 lines to minimize cognitive load.
- **Avoid**: Wall-of-text documentation without code. Organizing by API surface instead of use cases. Documentation drift from code changes.

### Sources
- https://diataxis.fr/ — Diátaxis framework for docs structure

## AI-Assisted Module Authoring

- **Key findings**: AI coding assistants work best with structured prompts that include: exact interface contract, constraints, a working example for pattern matching, and explicit error formats. Downloadable prompt kits eliminate the need for codebase knowledge.
- **Recommended**: Bundle AI instructions as a structured markdown file with clear sections: contract, constraints, template skeleton, example output. Include validation error format so the AI can self-correct from copy-pasted errors.
- **Avoid**: Embedding AI instructions in code comments (invisible to download). Assuming the AI has project context.

### Sources
- https://github.blog — GitHub Copilot customization patterns

## In-App Developer Onboarding

- **Key findings**: In-app guidance sections with clear call-to-action outperform external docs for conversion. Show the path: "download kit → edit template → upload module" as a step-by-step flow. Link validation errors directly to fix guidance.
- **Recommended**: Add a collapsible "Create a Module" section on the Modules page with numbered steps and download links. Surface the AI kit as a primary path alongside manual authoring.
- **Avoid**: Hiding dev guidance behind multiple navigation levels. Requiring users to leave the app for basic authoring instructions.

### Sources
- https://auth0.com — SDK onboarding patterns

### Summary
Ship a self-contained kit (template + example + AI instructions + contract reference) as static files served by the backend. Surface via in-app guidance on the Modules page. The copy-errors-for-AI utility already exists inline; extract it as a reusable utility. The standalone test harness should document how to run a module locally against the real contract.

### Sources Index
| URL | Topic | Fetched |
|-----|-------|---------| 
| https://diataxis.fr/ | Dev kit structure | 2026-06-11 |
| https://github.blog | AI-assisted authoring | 2026-06-11 |
| https://auth0.com | In-app onboarding | 2026-06-11 |
