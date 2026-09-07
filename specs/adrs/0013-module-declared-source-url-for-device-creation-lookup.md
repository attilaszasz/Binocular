---
adr_id: ADR-0013
status: accepted
date: 2026-09-07
tags: []
supersedes: []
superseded_by: ""
related_artifacts: [specs/prd.md#CAP-001, specs/prd.md#CAP-002, specs/sad.md, specs/project-plan.md, backend/src/binocular/extensions/contract.py]
---

# ADR-0013: Module-Declared Source URL for Device-Creation Lookup

## Status

Accepted.

## Context

On the Inventory > Add Device form, a user selects an extension module but must then enter the exact model name the module expects. Each module scrapes a known manufacturer support page, but that URL is currently hardcoded inside each module's Python source (e.g. Sony alphauniverse firmware page, Canon Asia catalogue, Panasonic firmware page, Viltrox download center) and is not surfaced anywhere in the UI or persisted in the data model. There is no `source_url` column on the `modules` table (migrations end at `0007_module_health.sql`). The module authoring contract (`backend/src/binocular/extensions/contract.py`) only declares `MODULE_VERSION` and `SUPPORTED_DEVICE_TYPE` constants plus the `check_firmware(url, model, http_client)` entrypoint; the canonical source page is not declared. Users cannot easily look up the exact model name a module expects, which is a recurring friction point during device creation.

## Decision Drivers

- Help users find the exact model name a module expects, without leaving the app.
- Keep the source URL accurate for user-authored/custom modules (not just the handful of official ones), avoiding drift.
- Keep the change backward-compatible and low-risk: an absent URL must not break loading, validation, seeding, or checks.
- Avoid network work just to learn the URL (no running a check).

## Considered Options

### Option A: Module-declared `SOURCE_URL` constant

Add an optional module-level `SOURCE_URL` string constant to the V1 authoring contract (alongside `MODULE_VERSION` and `SUPPORTED_DEVICE_TYPE`). The loader extracts it (default empty), a new `modules.source_url` column persists it via a numbered migration, the modules API returns it in `ModuleResponse`, and the Add Device form renders it as a clickable link when present.

- **Pros**: single source of truth in the module file; works for custom modules; cheap; backward-compatible (optional constant, empty default); no network work.
- **Cons**: requires a DB migration and one small contract extension; official modules must be updated to declare their source URLs.

### Option B: Frontend-only hardcoded map from module name/ID to URL

- **Pros**: no backend or schema change.
- **Cons**: breaks for custom modules; drift/duplication; maintainers must keep the map in sync; not authoritative.

### Option C: Derive the source URL at runtime from a check result

- **Pros**: reflects the actually-scraped URL.
- **Cons**: requires executing a network-bound check just to display a link; slow, side-effectful, and unavailable before a first successful check.

## Decision Outcome

Chosen option: **Option A (Module-declared `SOURCE_URL` constant)** — it is the only option that is authoritative for both official and custom modules, requires no network work, and stays backward-compatible with the existing V1 contract.

## Consequences

### Positive

- Users can click through to the exact page a module scrapes from the Add Device form, directly solving the model-name lookup friction.
- Works uniformly for official and user-authored modules.
- Single source of truth in the module file.
- No change to check execution.

### Negative

- New numbered SQL migration (`modules.source_url`) and a small V1 contract addition.
- Official modules need their source URLs declared.
- The field is advisory (empty for modules that don't declare it).

### Neutral

- The field is display-only metadata and does not alter scraping, pacing, or detection behavior.

## Links

- [PRD capability CAP-001 — Device Inventory & Lifecycle](../prd.md#CAP-001)
- [PRD capability CAP-002 — Extension Module Engine & Authoring Contract](../prd.md#CAP-002)
- [Software Architecture Document](../sad.md)
- [Project plan — epic E030](../project-plan.md)
- [Module authoring contract](../../backend/src/binocular/extensions/contract.py)
