## Research Report

**Context**: Informing the E004 Frontend SPA Shell technical spec — React 19, Vite 6, Tailwind CSS v4 (CSS-first), shadcn/ui with Radix primitives, collapsible sidebar, dark mode, and multi-stage Docker build.

## Tailwind CSS v4 CSS-First Configuration

- **Key findings**: v4 eliminates `tailwind.config.ts` and PostCSS/autoprefixer in favor of `@import "tailwindcss"` and `@theme` directives in CSS. The `@tailwindcss/vite` plugin replaces the PostCSS pipeline entirely. Automatic content detection removes the need for `content` arrays. Dark mode uses `@custom-variant dark (&:is(.dark *))`.
- **Recommended**: Use `@tailwindcss/vite` plugin exclusively. Define design tokens via `@theme { }` in `index.css`. Use CSS-based `@custom-variant` for dark mode toggling `.dark` class on `<html>`.
- **Avoid**: Do not create `tailwind.config.ts`. Do not install `postcss` or `autoprefixer`. Renamed utilities: `shadow-sm`→`shadow-xs`, `rounded-sm`→`rounded-xs`, `outline-none`→`outline-hidden`.
### Sources
- https://tailwindcss.com/docs/v4-beta — Official v4 migration guide
- https://tailwindcss.com/blog/tailwindcss-v4 — Release announcement with CSS-first details

## shadcn/ui Integration with Tailwind v4

- **Key findings**: shadcn/ui generates component source code into your repo (not a dependency). `npx shadcn@latest init` scaffolds `components.json` and installs Radix + CVA + clsx + tailwind-merge. Components use `cn()` utility for class merging. New York style uses smaller sizing and sharper borders.
- **Recommended**: Initialize with `npx shadcn@latest init` selecting New York style, Zinc base, blue primary. Add components individually via `npx shadcn@latest add button card ...`. Keep primitives in `components/ui/`, feature compositions in feature directories.
- **Avoid**: Editing shadcn primitives directly — create wrapper components for project-specific variations.
### Sources
- https://ui.shadcn.com/docs/installation/vite — Official Vite installation guide
- https://ui.shadcn.com/docs/theming — Theme configuration and CSS variables

## React Router SPA with FastAPI Static Serving

- **Key findings**: FastAPI serves `dist/` via `StaticFiles` mount with an SPA catch-all route returning `index.html` for all non-API paths. Vite dev server proxies `/api` to the backend during development. React Router v7 handles client-side routing.
- **Recommended**: Mount `StaticFiles` at `/` with `html=True`. Add catch-all `@app.get("/{path:path}")` returning `index.html`. Configure Vite proxy for `/api` → `http://localhost:8000`.
- **Avoid**: Serving frontend from a separate port in production. Using hash-based routing (unnecessary with catch-all).
### Sources
- https://fastapi.tiangolo.com/tutorial/static-files/ — Static file serving

## Multi-Stage Docker Build for SPA

- **Key findings**: A Node stage runs `npm ci && npm run build` producing `dist/`. The Python stage copies `dist/` to a known location (e.g., `/app/static_dist/`). This keeps the final image small (no Node runtime). `VITE_APP_VERSION` can be injected as a build arg.
- **Recommended**: Add a `frontend-builder` stage using `node:22-slim`. Copy `frontend/` and run build. Copy `dist/` into final image. Pass version via `ARG VITE_APP_VERSION`.
- **Avoid**: Including `node_modules` in the final image. Using `npm install` instead of `npm ci` in CI/Docker contexts.
### Sources
- https://docs.docker.com/build/building/multi-stage/ — Multi-stage build documentation

### Summary

Tailwind v4's CSS-first model with `@tailwindcss/vite` is the canonical setup — no config file, no PostCSS. shadcn/ui provides accessible Radix-based primitives as source code. FastAPI serves the built SPA via StaticFiles with catch-all. A Node multi-stage Docker build keeps the final image lean.

### Sources Index
| URL | Topic | Fetched |
|-----|-------|---------| 
| https://tailwindcss.com/docs/v4-beta | Tailwind v4 | 2026-06-10 |
| https://tailwindcss.com/blog/tailwindcss-v4 | Tailwind v4 | 2026-06-10 |
| https://ui.shadcn.com/docs/installation/vite | shadcn/ui | 2026-06-10 |
| https://ui.shadcn.com/docs/theming | shadcn/ui | 2026-06-10 |
| https://fastapi.tiangolo.com/tutorial/static-files/ | SPA serving | 2026-06-10 |
| https://docs.docker.com/build/building/multi-stage/ | Docker build | 2026-06-10 |
