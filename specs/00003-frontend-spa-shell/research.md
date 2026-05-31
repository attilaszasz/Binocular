# Research: Frontend SPA Shell
> Feature | 2026-05-31 | Purpose: frontend shell implementation choices

## Vite React Shell
- **Decision**: Use Vite with React 18, TypeScript, and Vitest.
- **Rationale**: This matches ADR-0003 and gives fast local builds plus CI-friendly scripts.
- **Rejected**: Next.js because the app is served by FastAPI as static files, not by a Node server.
- **Pitfalls**: Avoid SSR-only patterns and browser APIs outside effects or event handlers.
- **Sources**: https://vite.dev/guide/, https://react.dev/

## Styling And Theme
- **Decision**: Use Tailwind CSS with CSS custom properties and a `dark` class on the root element.
- **Rationale**: Tailwind is in the project stack and class-based dark mode supports persisted user preference cleanly.
- **Rejected**: Runtime CSS-in-JS because it adds complexity without value for the shell.
- **Pitfalls**: Avoid dynamically constructed Tailwind class names that purge/content scanning cannot see.
- **Sources**: https://tailwindcss.com/docs/dark-mode, https://tailwindcss.com/docs/content-configuration

## FastAPI Static Serving
- **Decision**: Mount built assets after API routers and use a fallback route that returns `index.html` for non-API paths.
- **Rationale**: Route ordering keeps `/healthz` and `/api/v1/*` reachable while supporting client-side deep links.
- **Rejected**: Serving the SPA from a separate container because the architecture requires one deployable image.
- **Pitfalls**: Do not fail backend startup when `dist/` is absent in development.
- **Sources**: https://fastapi.tiangolo.com/tutorial/static-files/, https://www.starlette.io/staticfiles/

## Summary
| Topic | Decision | Rationale |
|-------|----------|-----------|
| Vite React Shell | React 18 + TypeScript + Vite + Vitest | Matches ADR-0003 and CI needs |
| Styling And Theme | Tailwind class dark mode | First-class persisted theme primitives |
| FastAPI Static Serving | Backend fallback for SPA routes | Single-container deployment and deep links |

## Sources Index
| URL | Topic | Fetched |
|-----|-------|---------|
| https://vite.dev/guide/ | Vite React Shell | 2026-05-31 |
| https://react.dev/ | Vite React Shell | 2026-05-31 |
| https://tailwindcss.com/docs/dark-mode | Styling And Theme | 2026-05-31 |
| https://tailwindcss.com/docs/content-configuration | Styling And Theme | 2026-05-31 |
| https://fastapi.tiangolo.com/tutorial/static-files/ | FastAPI Static Serving | 2026-05-31 |
| https://www.starlette.io/staticfiles/ | FastAPI Static Serving | 2026-05-31 |
