<!-- template-version: 2 -->
# Binocular Project Instructions

## Core Principles

### I. Honest Failure

The system MUST surface failures visibly and MUST NOT silently miss an update. Every check records its outcome with a last-success timestamp; a changed or unparseable source produces a visible "scrape failed" status, never an absent result. — A silently missed firmware update is the most damaging possible failure for an unattended watcher; visible failure is the core safeguard of user trust.

### II. Polite by Default

All outbound scraping MUST flow through the centralized host-provided HTTP client and MUST honor robots.txt (RFC 9309), send an identifiable User-Agent, and apply per-domain rate limiting and exponential backoff. Modules MUST NOT perform direct outbound requests. — Responsible-scraping behavior protects third-party sources and the project's legal/reputational standing, and a single enforcement point is the only way to guarantee it.

### III. Data Ownership & Self-Containment

All state MUST live in a single backup-able SQLite volume. The system MUST NOT depend on an external database server, message broker, cloud service, account system, or any telemetry/analytics. — Self-hosters choose this tool for data ownership and privacy; external dependencies or data collection would break that promise.

### IV. Least-Privilege & Explicit Trust Boundary

The container MUST run as a non-root user. Extension modules execute unsandboxed, in-process, with full application privileges, and this MUST be treated and documented as an explicit user-vetted trust boundary — the system MUST NOT claim or imply that modules are sandboxed. — Honest framing of the arbitrary-code-execution boundary lets operators make informed decisions; non-root execution limits blast radius without pretending the risk is eliminated.

### V. Type Safety & Correctness-First

Backend code MUST pass `mypy --strict` and frontend code MUST pass `tsc` in strict mode. Officially shipped modules MUST be validated for detection correctness against captured page fixtures (zero false positives/negatives) before release. — With no field telemetry available, static typing and fixture-based correctness are the primary defenses against regressions in a tool whose entire value is trustworthy detection.

### VI. Set-and-Forget Reliability

The application MUST start with zero required configuration, persist all state to one defined volume, and survive container restarts and image upgrades with no data loss. A broken or timed-out module MUST NOT crash the core process. — The product promise is unattended operation for months; reliability across restarts/upgrades and fault isolation between modules and core are what make that promise real.

### VII. Agent Output Style

All agent output MUST be concise and outcome-oriented. This principle supersedes any verbose defaults.

- **Progress reports**: Facts and outcomes only — no narration, no restating the task.
- **Artifacts**: Emit required sections only — no preamble paragraphs, no summary epilogues.
- **Reasoning**: Omit unless the user asks "why" or the decision is non-obvious.
- **Errors / blockers**: State the problem, the attempted fix, and the result — nothing else.
- **Phase-boundary reports**: ≤ 5 bullet points.
- **Preserve without compressing**: Artifact template structure and required sections; explicit decision / registration / validation guidance in shared skills; delegation constraints and sub-agent role definitions; existing size limits (spec ≤ 10 KB, research ≤ 4 KB, stories ≤ 200 words).

## Technology Stack

<!-- Downstream phases (Plan, QC, Autopilot) read this section as the authoritative tech-stack reference. -->

- **Language/Runtime**: Python 3.13 (backend); TypeScript 5.x / React 19 on Node (frontend)
- **Frameworks**: FastAPI, Uvicorn, Pydantic, APScheduler, Apprise, httpx, structlog (backend); React, Vite, Tailwind CSS 4.x (CSS-first config via `@tailwindcss/vite`), shadcn/ui, Radix UI primitives, React Router, TanStack Query, React Hook Form, class-variance-authority, clsx, tailwind-merge, tw-animate-css (frontend)
- **Storage**: SQLite single file via aiosqlite, raw parameterized SQL with a numbered-migration runner — no ORM, no external database server
- **Infrastructure**: Single non-root Docker container (`python:3.13-slim`), one port, two volumes (`/app/data`, `/app/modules`); GitHub Actions CI/CD publishing multi-arch images to GHCR

## Testing & Quality Policy

<!-- QC extracts enforcement rules from this section. Keywords: lint, static analysis, code quality, coverage, security, vulnerability, OWASP, WCAG, accessibility, benchmark, performance -->

- **Coverage Target**: 80%
- **Required QC Categories**: linting, static analysis, security scanning, coverage
- **Test Strategy**: Test-after — unit + integration (pytest + pytest-asyncio, Vitest + React Testing Library), one Playwright end-to-end smoke test, and golden/fixture-based correctness tests for shipped modules. Security scanning via vulnerability scanning of the built image (Trivy) in CI.
- **Linting / Formatting**: Ruff (backend), Biome/ESLint (frontend), `mypy --strict` and `tsc` strict for static analysis

## Source Code Layout

- **Policy**: ENFORCE_SRC_ROOT
- **Convention**: Project source code MUST live under a `/src` root within each application root — backend code under `backend/src/`, frontend code under `frontend/src/`. Frontend components follow a feature-based layout with shadcn/ui primitives under `frontend/src/components/ui/`. Tests live alongside their application; numbered SQL migrations under `backend/src/db/migrations/`; config at repo root.

## Development Workflow

- **Branching**: GitHub Flow — short-lived branches off `main`, merged via pull request once CI is green.
- **Commit Convention**: Free-form, descriptive commit messages.
- **CI Requirements**: Before merge, all tests MUST pass, linting and static analysis (Ruff, Biome, `mypy --strict`, `tsc`) MUST be clean, and the Docker image MUST build. Published release images MUST additionally pass vulnerability scanning.

## Governance

- Project instructions supersede all other documentation and practices.
- Amendments require a version bump with ISO-dated changelog entry.
- All implementations MUST pass the Instructions Check gate during planning.
- Complexity beyond these principles MUST be justified and documented.
- The trusted-LAN single-user threat model is assumed; exposing the application to untrusted networks is outside the supported security posture and MUST be documented as such wherever relevant.

**Version**: 1.1.1 | **Last Amended**: 2026-06-10
