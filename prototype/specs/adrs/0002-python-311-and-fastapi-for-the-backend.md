---
adr_id: ADR-0002
status: accepted
date: 2026-05-31
tags: [backend, language, framework]
supersedes: []
superseded_by: ""
related_artifacts: [specs/prd.md#CAP-002, specs/prd.md#CAP-006, specs/prd.md#CAP-008]
---

# ADR-0002: Python 3.13 and FastAPI for the backend

## Status

Accepted.

## Context

The backend must run dynamically loaded user-authored scraper modules, scrape heterogeneous manufacturer firmware pages, perform concurrent checks without blocking the UI, and serve a JSON API plus static frontend from a single port. The core business value (scraping + dynamic module loading) drives language choice. A backend language/runtime and web framework must be selected before any component work.

## Decision Drivers

- First-class dynamic loading of user-dropped `.py` modules at runtime (core extensibility requirement)
- Best-in-class scraping ecosystem (BeautifulSoup, httpx, Playwright available if needed)
- High-performance async I/O for concurrent multi-site checks
- Strong typing and request/response validation for a maintainable single-maintainer OSS project
- Auto-generated OpenAPI docs to support a typed frontend client

## Considered Options

### Option A: Python 3.13+ with FastAPI

- **Pros**: Trivial `importlib` runtime module loading; dominant scraping ecosystem; async I/O via ASGI/Uvicorn; Pydantic validation; auto OpenAPI; mypy `--strict` typing.
- **Cons**: GIL limits CPU parallelism (irrelevant for I/O-bound scraping); packaging/runtime heavier than Go.

### Option B: Node.js with TypeScript (e.g., Fastify/NestJS)

- **Pros**: Shared language with frontend; good async.
- **Cons**: User-authored scraper modules in JS less natural for the target audience; weaker scraping ecosystem than Python; dynamic module loading possible but less idiomatic for the "drop a script" UX.

### Option C: Go

- **Pros**: Single static binary; excellent concurrency.
- **Cons**: No ergonomic runtime loading of user-authored plugin scripts (plugins are painful); poor fit for the user-writes-a-script extension model that is the product's differentiator.

## Decision Outcome

Chosen option: **A: Python 3.13+ with FastAPI** — the extension model (users author and drop in `.py` scraper modules loaded at runtime) is the product's core differentiator and is natively and idiomatically supported only by Python. Python also brings the strongest scraping ecosystem and, via FastAPI, async I/O, Pydantic validation, and auto-generated OpenAPI that feeds the typed frontend client.

Python 3.13 is selected as a current, mature, fully ecosystem-supported release — all key dependencies (FastAPI, Pydantic, aiosqlite, APScheduler, Apprise, httpx) support it — chosen over the older 3.11 for a longer security-support runway, with no impact on the I/O-bound workload.

## Consequences

### Positive

- Idiomatic runtime module loading via `importlib`.
- Rich scraping libraries (BeautifulSoup, httpx, Playwright).
- Async concurrency for multi-site checks.
- Pydantic validation at the API boundary.
- Auto-generated OpenAPI feeding the typed frontend client.
- mypy `--strict` for type safety.

### Negative

- Python runtime/image larger than a Go binary.
- GIL limits CPU-bound parallelism (acceptable for the I/O-bound workload).

### Neutral

- Backend code organized under `backend/src/` (api, services, repositories, db, models, utils); served by Uvicorn on port 8000.

## Links

- [specs/prd.md](../prd.md) — CAP-002 (Extension Module Engine)
- [specs/prd.md](../prd.md) — CAP-006 (Update Detection)
- [specs/prd.md](../prd.md) — CAP-008 (Responsible Scraping)
- [ADR-0001](0001-self-hosted-single-container-monolith-with-core-extension-separation.md) — Single-container monolith architecture
