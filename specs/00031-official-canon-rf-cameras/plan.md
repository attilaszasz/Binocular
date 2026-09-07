# Implementation Plan: E028 — Official Canon RF Cameras

**Branch**: `00031-official-canon-rf-cameras` | **Date**: 2026-09-07 | **Spec**: [spec.md](spec.md)

## Summary

**Goal**: Ship an exact, model-only official Canon EOS R camera firmware module.  
**Approach**: Parse captured Canon Asia catalogue/product/firmware HTML through the existing scoped ScrapeClient and module contract.  
**Key Constraint**: Follow source links/actions verbatim and share Canon's 30-second origin pacing across every attempt.

## Technical Context

**Language/Version**: Python 3.13  
**Primary Dependencies**: BeautifulSoup4; host-injected ScrapeClient; existing extension loader, runner, and seeder  
**Storage**: N/A — existing module upsert only  
**Testing**: pytest, pytest-asyncio, pytest-cov, injected clocks and scripted transports  
**Target Platform**: Linux Docker container (`python:3.13-slim`)  
**Project Type**: web  
**Project Mode**: brownfield  
**Performance Goals**: Bounded three-stage source flow; no real sleeps in tests  
**Constraints**: mypy strict; Ruff; no direct HTTP; exact model match; Canon delay; cancellation-safe  
**Scale/Scope**: One module covering exact bodies in the captured EOS R catalogue

## Instructions Check

| Principle | Status | Plan Evidence |
|-----------|--------|---------------|
| Honest Failure | PASS | Typed failures for unsupported, no-firmware, drift, denial, timeout, and cancellation |
| Polite by Default | PASS | Every request uses scoped ScrapeClient; shared origin policy applies before retries |
| Data Ownership | PASS | No new state, server, telemetry, or dependency |
| Trust Boundary | PASS | Existing unsandboxed in-process module boundary is documented and unchanged |
| Type Safety | PASS | mypy strict, Ruff, and fixture correctness are required |
| Set-and-Forget | PASS | Bounded scope prevents post-cancellation requests; errors remain isolated |
| Source Layout | PASS | Source under `backend/src/`; tests under `backend/tests/` |

**Gate Result**: PASS before research and after design; no complexity exception.

## Architecture

```mermaid
C4Container
  title Canon RF Cameras Module
  Person(user, "Operator", "Monitors EOS R")
  System_Boundary(app, "Binocular") {
    Container(server, "App Server", "FastAPI", "Runs checks")
    Container(runner, "Module Runner", "Python", "Invokes module")
    Container(seeder, "Module Seeder", "Python", "Registers module")
    Container(module, "Canon Module", "Python", "Parses source chain")
    Container(client, "Scrape Client", "httpx", "Enforces policy")
  }
  System_Ext(catalog, "EOS R Catalogue", "HTML", "Lists bodies")
  System_Ext(product, "Product Page", "HTML", "Declares action")
  System_Ext(firmware, "Firmware Fragment", "HTML", "Lists releases")
  Rel(user, server, "Checks")
  Rel(server, runner, "Runs")
  Rel(server, seeder, "Seeds")
  Rel(runner, module, "Invokes")
  Rel(seeder, module, "Loads")
  Rel(module, client, "Fetches")
  Rel(client, catalog, "Gets")
  Rel(client, product, "Gets")
  Rel(client, firmware, "Gets")
```

## Architecture Decisions

| ID | Decision | Options Considered | Chosen | Rationale |
|----|----------|--------------------|--------|-----------|
| AD-001 | How to resolve models? | Exact normalized / aliases / hardcoded map | Trimmed case-folded exact catalogue name | Prevents near-name false positives while tolerating harmless input differences |
| AD-002 | How to locate firmware content? | Construct URL / discover action | Catalogue link then product form action | Source links are authoritative and encoded irregularly |
| AD-003 | How to select releases? | First row / OS package / grouped version | Group by normalized version, select newest | Prevents OS duplicates and preserves version semantics |
| AD-004 | How to parse HTML? | Regex / BeautifulSoup4 | BeautifulSoup4 | Existing dependency supports structural validation at all three stages |

## Data Model Summary

N/A — no persistent data changes; existing automatic module upsert is reused.

## API Surface Summary

N/A — no API changes; existing version-search and check endpoints invoke the module contract.

## Testing Strategy

| Tier | Tool | Scope | Mock Boundary | Install |
|------|------|-------|---------------|---------|
| Unit | pytest | Exact matching, action discovery, release grouping, typed failures | Captured HTML fixtures | configured |
| Integration | pytest-asyncio | Module load/seed, version search/check, shared pacing, timeout/cancellation | Scripted httpx transport + injected time | configured |
| Security | Ruff + pip-audit | Unsafe imports, source and dependency scan | — | configured |
| Coverage | pytest-cov | Backend suite and module branches; ≥80% | — | configured |
| Static | mypy --strict | Backend source typing | — | configured |

## Error Handling Strategy

| Error Category | Pattern | Response | Retry |
|----------------|---------|----------|-------|
| Input/unsupported | Fail fast after exact catalogue lookup | `product_not_found` visible failure | No |
| No firmware | Distinguish explicit source message | `firmware_not_available` visible failure | No |
| Source drift | Require catalogue link, unique action, valid rows/link | `firmware_index_not_found` visible failure | No |
| Network/denial | Preserve scoped client error | Existing activity/check failure | Client policy only |
| Timeout/cancellation | Propagate scope termination | Visible failure; no later requests | No |

## Risk Mitigation

| Risk (from spec) | Likelihood | Impact | Mitigation | Owner |
|------------------|------------|--------|------------|-------|
| Source drift | H | H | Stage-specific structural checks plus captured malformed fixtures | Canon module |
| Coverage overstatement | M | H | Exact EOS R catalogue membership and explicit R5 C rejection tests/docs | Canon module |
| Long source pacing | M | M | Reuse source-aware scope credit and deterministic timing/cancellation tests | ScrapeClient integration |

## Requirement Coverage Map

| Req ID | Component(s) | File Path(s) | Notes |
|--------|--------------|--------------|-------|
| FR-001 | Module + Seeder | `backend/src/binocular/official_modules/canon_rf_cameras.py`; `backend/src/binocular/services/seeder.py` | Auto-discovery; no seeder code expected |
| FR-002 | Catalogue resolver | `backend/src/binocular/official_modules/canon_rf_cameras.py`; `backend/tests/fixtures/canon_rf_cameras/` | Exact normalized names and exclusions |
| FR-003 | Source discovery | `backend/src/binocular/official_modules/canon_rf_cameras.py` | Verbatim product link and unique form action |
| FR-004 | Release parser | `backend/src/binocular/official_modules/canon_rf_cameras.py` | Normalize, deduplicate, newest, detail link |
| FR-005 | Failure mapping | `backend/src/binocular/official_modules/canon_rf_cameras.py`; `backend/tests/test_official_canon_rf_cameras_module.py` | Full failure matrix |
| FR-006 | Scraping integration | `backend/src/binocular/official_modules/canon_rf_cameras.py`; `backend/tests/scraping/` | Injected client only; E027 shared pacing |
| FR-007 | Scope integration | `backend/tests/scraping/`; `backend/tests/test_official_canon_rf_cameras_module.py` | Deadline and cancellation assertions |
| FR-008 | Existing flows | `backend/tests/routes/test_checks_routes.py`; `backend/tests/test_official_canon_rf_cameras_module.py` | Search and normal runner paths |
| FR-009 | Fixture correctness | `backend/tests/fixtures/canon_rf_cameras/`; `backend/tests/test_official_canon_rf_cameras_module.py` | Golden + negative matrix |
| FR-010 | Documentation | `backend/src/binocular/official_modules/README.md` | Region, boundaries, semantics, exclusions |

## Project Structure

### Source Code

```text
~ backend/src/binocular/official_modules/README.md
+ backend/src/binocular/official_modules/canon_rf_cameras.py
+ backend/tests/fixtures/canon_rf_cameras/
  + catalog.html
  + eos_r5_product.html
  + eos_r5_firmware.html
  + no_firmware.html
  + malformed_*.html
+ backend/tests/test_official_canon_rf_cameras_module.py
~ backend/tests/routes/test_checks_routes.py
```

**Patterns to reuse**: Official-module constants/entry point; FakeScrapeClient fixtures; Seeder auto-discovery; E027 scoped pacing tests.  
**Tests to extend**: Module loading/seeding, check service, version search, deterministic scrape scope.  
**Naming conventions**: `snake_case` module/helpers, uppercase constants, typed `ValueError("code: detail")` failures.

## Implementation Hints

- **[HINT-001]** Order: Parse catalogue, exact-match model, follow product link, discover one firmware action, then parse releases.
- **[HINT-002]** Gotcha: Do not URL-decode/rebuild source links or action paths before `urljoin`.
- **[HINT-003]** Constraint: Reject R5 C explicitly even if a fixture mentions RF mount.
- **[HINT-004]** Compatibility: Preserve the synchronous official-module entry point while all HTTP uses the injected async client.
- **[HINT-005]** Performance: Timing tests use the existing virtual clock; never wait 30 real seconds.
