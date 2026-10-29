<!-- template-version: 2 -->
# Binocular Project Instructions

## Core Principles

### I. Honest Failure

The system MUST surface failures visibly and MUST NOT silently miss an update. Catalog enumeration and model firmware verification MUST record separate attempt outcomes and last-success timestamps. Failed or unverified units of partial refreshes MUST NOT advance verification timestamps or present retained firmware as newly verified; successfully verified models advance their own timestamps independently. Last-known results MAY remain visible with freshness and failure labels; an unknown installed version or an incomparable version MUST NOT be reported as current. — Unattended monitoring depends on distinguishing verified knowledge from uncertainty.

### II. Polite by Default

All outbound scraping MUST flow through the centralized host-provided HTTP client and MUST honor robots.txt (RFC 9309), send an identifiable User-Agent, and apply per-origin pacing and exponential backoff. The client MUST honor valid source-declared crawl delays as non-standard politeness hints without reducing the conservative default for sources that omit or declare a shorter delay. Pacing MUST be shared across concurrent refreshes/checks and applied before every network attempt, including retries. Modules MUST NOT perform direct outbound requests. Catalog refreshes MUST reuse shared indexes where possible and MUST NOT repeat manufacturer discovery for each owned device. Opening, searching, browsing, or selecting local catalog models MUST NOT trigger manufacturer requests; only explicit refresh/check actions or background jobs may do so. — One enforcement point and shared discovery protect sources without coupling UI interaction to scraping.

### III. Data Ownership & Self-Containment

All state, including catalog identities, verified firmware snapshots, reusable source-discovery metadata, inventory, and notification delivery state, MUST live in a single backup-able SQLite volume. “Global” or “shared” MUST mean within this self-hosted instance, never a cloud catalog. Module-scoped catalog models MUST remain distinct from owned devices, preserving firmware compatibility variants and allowing multiple devices per model. Both Add Device and Modules-page “Add to inventory” MUST use one catalog-backed creation flow with stable selected identity; Modules MUST preselect the source and model without restricting multiple physical devices. Verified firmware snapshots MUST retain provenance, verification time, and explicit freshness/status; they are local observations, not claims of a live manufacturer check. Endpoint-discovery metadata remains fresh only while younger than 24 hours and MUST be invalidated on transport, status, parsing, or model-identity failure; an invalid endpoint MUST NOT manufacture a successful verification. The system MUST NOT depend on an external database server, message broker, cloud service, account system, or telemetry/analytics. — Local shared observations reduce duplicate work while preserving ownership and honest freshness.

### IV. Least-Privilege & Explicit Trust Boundary

The container MUST run as a non-root user. Extension modules execute unsandboxed, in-process, with full application privileges, and this MUST be treated and documented as an explicit user-vetted trust boundary — the system MUST NOT claim or imply that modules are sandboxed. — Honest framing of the arbitrary-code-execution boundary lets operators make informed decisions; non-root execution limits blast radius without pretending the risk is eliminated.

### V. Type Safety & Correctness-First

Backend code MUST pass `mypy --strict` and frontend code MUST pass `tsc` in strict mode. Officially shipped modules MUST be validated for enumeration, compatibility identity, and firmware-detection correctness against captured page fixtures (zero false positives/negatives within verified coverage) before release. Contract version and catalog capability MUST be negotiated explicitly; legacy V1 modules MUST retain a labeled manual-entry/per-model-check fallback without implied enumeration support. — Static typing, compatibility negotiation, and fixture validation protect trustworthy detection without field telemetry.

### VI. Set-and-Forget Reliability

The application MUST start with zero required configuration, persist all state to one defined volume, and survive container restarts and image upgrades with no data loss. Every active, unpaused catalog-capable module MUST refresh independently of inventory count, honoring module-wide frequency and pause controls; pause governs automatic scheduling, not the validity of successful explicit manual verification. A broken or timed-out module MUST NOT crash the core process. Multi-request refreshes/checks MUST accommodate source-specific crawl delays within bounded end-to-end budgets; timeout/cancellation MUST stop pending waits, retries, and background requests, while sources without a longer valid delay retain existing budgets. Successful model verification and device add/edit/update-confirmation MUST reevaluate linked devices through shared comparison logic. Durable per-device/version/channel notification intents and exclusive claims MUST prevent duplicate application dispatch from repeated refreshes or concurrent actions; failed delivery MUST remain visible and retryable without resending successful channels. Ambiguous external acceptance MUST remain visibly uncertain, MUST NOT retry automatically, and MUST warn of duplicate risk before explicit retry; external exactly-once delivery MUST NOT be promised. — Shared discovery must remain restart-safe, bounded, and independent of inventory or alert dispatch.

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
- **Required QC Categories**: linting, static analysis, security scanning, coverage, accessibility, performance
- **Test Strategy**: Test-after — unit + integration (pytest + pytest-asyncio, Vitest + React Testing Library), one Playwright end-to-end smoke test, and golden/fixture correctness tests for official modules. Deterministic HTTP tests use injected clocks/sleepers and scripted transports for shared pacing, every retry, bounded work, timeout, and cancellation without real sleeps. Endpoint caches require migration, 24-hour freshness, restart, invalidation, fallback, and single-flight tests; live verification always uses the centralized HTTP client. Catalog tests MUST cover stable variant identity/aliases, partial/failed refreshes, inventory-independent scheduling, shared-index request counts, bounded per-model work, V1/V2 negotiation, safe inventory linking/migration, freshness and unknown-version semantics, atomic fan-out/outbox work, concurrent deduplication, restart recovery, and channel-specific delivery failure/retry. Accessibility tests MUST cover keyboard/screen-reader semantics of the shared model combobox and Modules catalog; performance tests MUST prove bounded local pagination/rendering for a 10,000-model fixture and zero manufacturer requests from browse/search/form interaction. Security scanning uses Trivy on the built image in CI.
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

## Amendment Changelog

- 2026-10-29 v2.0.0: Replaced live-only/per-device discovery policy with instance-local catalog observations, inventory-independent refresh, explicit legacy capability negotiation, concurrent delivery deduplication, and catalog accessibility/performance validation. Stack, layout, trust boundary, and registered document paths are unchanged.
- 2026-09-07 v1.3.0: Added 24-hour source-discovery cache freshness, invalidation, and deterministic validation policy.

**Version**: 2.0.0 | **Last Amended**: 2026-10-29
