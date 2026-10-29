---
adr_id: ADR-0016
status: accepted
date: 2026-10-29
tags: [modules, contract, compatibility, catalog, validation]
supersedes: [ADR-0005]
superseded_by: ""
related_artifacts: [specs/prd.md#CAP-002, specs/prd.md#CAP-003, specs/prd.md#CAP-011, specs/prd.md#CAP-013, specs/prd.md#CAP-015, specs/prd.md#CAP-016, specs/project-plan.md, E033, E035, E038]
---

# ADR-0016: Versioned catalog-capable module contract with V1 compatibility

## Status

Accepted. Supersedes [ADR-0005](0005-unsandboxed-extension-module-engine-with-two-phase-validation.md).

## Context

The V1 `check_firmware(url, model, http_client)` contract verifies an explicitly supplied model but cannot enumerate a manufacturer's supported models. ADR-0015 requires stable module-scoped compatible models and verified local firmware observations independently of owned devices. Catalog discovery and firmware verification must therefore become distinct operations, supporting shared manufacturer indexes as well as source-specific per-model detail pages. Enumeration cannot be invented from V1 checks, existing inventory, callable names, or display-name guesses.

Existing valid custom modules must continue working through a visibly legacy manual-entry/per-model-check path. Explicitly unsupported protocol versions must fail visibly rather than be reinterpreted as V1. Compatible updates must preserve module identity, linked models/devices, module-wide frequency and pause controls, and existing source coverage. Contract documentation, validation, fixtures, templates, and the AI Module Kit must teach the same negotiated interface.

The application remains a trusted-LAN, single-user, SQLite-backed local instance. Modules remain unsandboxed and in-process, with full application privileges and a user-vetted trust boundary. Every outbound manufacturer request still passes through the existing centralized host HTTP client; no new service, independent networking stack, or sandbox is introduced. Local catalog browsing and shared device creation consume persisted data, not module execution.

## Decision Drivers

- Preserve valid V1 modules without pretending they support enumeration.
- Establish verifiable, stable firmware-compatible variant identity independently of ownership.
- Reuse shared source requests and bound polite per-model work.
- Keep the negotiated contract, documentation, validator, harness, and authoring kit aligned.
- Preserve the explicit unsandboxed trust boundary and visible validation/runtime failures.

## Considered Options

### Option A: Explicit V2 catalog protocol plus V1 adapter

Negotiate protocol version and catalog capability explicitly; adapt V1 checks only to their existing manual/per-model behavior.

- **Pros**: Honest capabilities, an explicit upgrade path, and support for heterogeneous shared-index/detail sources.
- **Cons**: Two supported contracts and migration/documentation overhead during transition.

### Option B: Duck-type V1 and infer catalog

Infer enumeration support from existing functions, returned data, or inventory inputs without a declared catalog protocol.

- **Pros**: Smaller initial interface changes.
- **Cons**: False capability claims, ambiguous identity, and loss of compatibility distinctions; V1 cannot actually enumerate.

### Option C: Break all V1 modules

Require the new catalog interface for every installed and uploaded module immediately.

- **Pros**: One interface to maintain.
- **Cons**: Breaks valid custom modules and existing monitoring instead of preserving an explicit compatibility path.

## Decision Outcome

Chosen option: **A Explicit V2 catalog protocol plus V1 adapter** — introduce explicit V2 catalog capability negotiation while preserving unsandboxed execution, two-phase validation, and V1 manual-entry/per-model checking.

**Version and capability negotiation.** `MODULE_VERSION` remains the author's implementation revision, not the host protocol selector. Independently, integer `MODULE_API_VERSION = 2` together with `MODULE_CAPABILITIES` containing `"catalog"` declares V2 catalog support. An omitted API declaration or explicit integer `1` selects V1. An unsupported declared value, including a malformed/non-integer declaration, or a catalog capability declared on V1 produces a structured validation failure; it must not silently fall back. Callable existence never implies a capability. A V2 module without a declared catalog capability is not presented as enumerating. Preserve module metadata including `SUPPORTED_DEVICE_TYPE`, `MODULE_AUTHOR`, and optional `SOURCE_URL`/source guidance without retroactively rejecting previously valid V1 modules for new V2 requirements.

**Catalog entrypoints and host-owned context.** V2 catalog support requires synchronous `discover_models(http_client, context) -> CatalogPage` and `get_firmware(model, http_client, context) -> FirmwareResult`. These result types are standardized, host-validated mappings, not arbitrary module objects. The host supplies the model's stable source identity and canonical compatibility variant to firmware verification; the returned result must match them.

`context` is owned by the host and scoped to one bounded refresh. It provides bounded continuation/cursor state, deadlines, cancellation, and shared response/index access. It is not owned inventory and does not authorize independent networking. Shared index responses are coalesced within the refresh, and detail work is performed once per unique compatible model, not once per owned copy. Enumeration can use one shared index while verification uses source-specific details; sources need not manufacture a single combined endpoint.

**Discovery mapping.** `CatalogPage` includes model entries with stable `source_model_key`, `display_name`, aliases/source identifiers, source/product/help URLs, and canonical compatibility distinctions for region, mount, and hardware revision, plus a continuation cursor and explicit completeness. Together, the source key and canonical variant establish identity within the module; display names and aliases do not. Continuation and partial outcomes must remain explicit rather than disguising a truncated scan as complete.

A discovered entry may include a validated inline `FirmwareResult` when the same fetched authoritative source verifies that model's firmware outcome. Inline firmware is optional: enumeration can succeed without firmware, and the host invokes per-model details when needed. Discovery alone does not establish firmware verification or advance its successful timestamp. Missing, invalid, or ambiguous identity, changed source structure, denied access, network errors, and deadline/cancellation failures remain visible errors or partial outcomes, never an invented complete empty catalog or an authoritative no-firmware result.

**Firmware mapping and freshness.** `FirmwareResult` contains the matching source model key/variant, a verified version or explicit authoritative `firmware_not_available` outcome, applicable release date/release/download links, and provenance. An error, unsupported identity, or unparsed page is not `firmware_not_available`. The host supplies attempt and verification timestamps. Only validated authoritative identity-matching results advance successful firmware verification; failed/partial work preserves last-known observations with their original provenance and visible freshness/failure status under ADR-0015.

**Centralized and bounded retrieval.** Every network attempt uses the existing centralized HTTP client, including index and detail requests, retries, and cached-endpoint validation. Context sharing and persistent discovery metadata do not bypass robots.txt, identifiable User-Agent, shared per-origin pacing, valid source-declared delay hints, or exponential backoff. ADR-0012 governs bounded end-to-end budgets and cancellation, and ADR-0015 retains the separate less-than-24-hour endpoint validity/invalidation policy. Timeout/cancellation must stop pending client waits, retries, and further background requests; exhausted work is visibly partial/failed rather than silently complete.

**Two-phase validation and execution trust.** Mandatory AST validation checks the negotiated contract, declarations/constants, required entrypoints, and signatures without executing uploaded code. Optional runtime proof uses supplied fixtures and host context to exercise variant enumeration, continuation/completeness, partial results, inline results, per-model details, firmware/no-firmware outcomes, and errors. Validation results identify the contract and failing phase and remain copyable for AI-assisted correction. Merely opening the validator, authoring guidance, or AI Module Kit makes no manufacturer requests; any live runtime proof must be an explicit check action through the centralized client.

Retain in-process loading through `importlib.util.spec_from_file_location()`, without inserting modules into `sys.modules` or using `exec`/`eval`. Import and invocation boundaries catch `Exception` and `SystemExit`, not `KeyboardInterrupt`, and isolate reported failures so the core and other module jobs continue. Synchronous work remains host-managed with timeouts and cooperative cancellation through the context/client. A timed-out thread is not a sandbox or proof that arbitrary Python has stopped: no security containment is claimed. Uploaded/runtime code still executes with full application privileges; operator vetting and non-root execution remain mandatory trust-boundary documentation.

**V1 compatibility and recommended migration.** V1 retains `check_firmware(url, model, http_client)`, labeled manual model/URL entry, explicit per-model version checks, and existing interval scheduling for owned legacy devices. It has no zero-inventory enumeration. Existing valid customs keep operating until explicitly upgraded, and protocol validation never reinterprets an unsupported declared version as V1.

Authors should keep their V1 checker until supported source-index enumeration is verified, then declare API `2`/`catalog`, establish stable keys and compatible variants, factor shared discovery from per-model details, and supply fixtures plus validator/harness/kit coverage. Update the installed module under the same module ID. Backfill inventory links only for exact, unambiguous compatible matches. For unresolved inventory on a migrated catalog-capable module, a legacy checker may be used only if it actually remains exported; otherwise show “needs model selection.” Never invent a fallback checker or silently bind by display name.

Compatible updates and official seeding preserve module IDs, model identities, foreign-key associations, refresh interval, and pause state. Capability downgrades with linked catalog models require visible preservation/relink handling, never silent unbinding. Block module deletion while inventory references it unless the user explicitly reassigns that inventory; never cascade deletion into inventory loss.

**Coordinated future delivery.** Migrate every official module to the explicit V2 catalog contract while preserving identity and verified coverage. Canon cameras and lenses remain separate selectable modules restricted to the verified Canon Asia English EOS R and RF/RF-S catalogues. Preserve exact matching, variant boundaries, OS-package deduplication, endpoint validity, and exclusions for Cinema EOS/EOS R5 C, cinema lenses, adapters, extenders, unrelated mounts, regional fallback, and firmware-binary retrieval; RF-S catalogue support does not imply a verified positive release. Update module documentation/README, validator/harness, templates/examples, AI Module Kit, migration guidance, and copyable phase errors together. This accepted architectural decision authorizes no implementation edits in this amendment.

**Integration boundaries.** Under ADR-0015, active unpaused catalog-capable modules refresh independently of inventory, while Add Device and bounded accessible Modules browsing use the same local catalog and stable preselected creation flow without source calls. Installed firmware remains independently entered or explicitly unknown, never populated from available firmware. Successful shared model verification fans out to linked devices; add/edit/confirmation use shared local comparison. Durable per-device/version/channel deduplication and retry without resending successful channels belong to the successor to ADR-0007, not module-returned notification state. Modules neither enumerate from inventory nor dispatch alerts directly.

## Consequences

### Positive

- Explicit standardized enumeration and verification support stable compatibility identities, shared indexes, and source-specific details without invented V1 capabilities.
- Existing valid custom modules retain working manual/per-model monitoring and an explicit, identity-safe migration path.
- Version-aligned validation, fixtures, documentation, and authoring tools make capability and failure handling verifiable.

### Negative

- Dual V1/V2 paths increase host, documentation, fixture, and validation maintenance during migration.
- Custom-source authors must verify enumeration, stable variants, continuation, and firmware outcomes before claiming catalog support.
- Ambiguous inventory links and capability downgrades require visible operator resolution rather than silent automatic migration.

### Neutral

- Modules remain unsandboxed and in-process within the existing trusted-LAN/non-root boundary; no external service or isolation runtime is introduced.
- SQLite persistence, local observations, source coverage restrictions, and centralized polite-scraping policy remain unchanged.
- Contract and official-module implementation changes are future delivery work, not claims of completion by this record.

## Links

- [PRD capabilities CAP-002, CAP-003, CAP-011, CAP-013, CAP-015, and CAP-016](../prd.md#product-capability-map)
- [Project instructions v2.0.0](../../project-instructions.md)
- [Project plan](../project-plan.md) — future E033, E035, and E038.
- [ADR-0005: Unsandboxed extension module engine with two-phase validation](0005-unsandboxed-extension-module-engine-with-two-phase-validation.md) — superseded; execution trust and two-phase validation retained.
- [ADR-0015: Instance-local model catalog and verified firmware observations](0015-instance-local-model-catalog-and-verified-firmware-observations.md)
- [ADR-0012: Source-aware centralized scraping](0012-source-aware-centralized-scraping-with-shared-per-origin-pacing-and-bounded-cancellation.md)
- [ADR-0011: Real-time module validation and upload progress streaming](0011-real-time-module-validation-and-upload-progress-streaming.md)
- [ADR-0013: Module-Declared Source URL for Device-Creation Lookup](0013-module-declared-source-url-for-device-creation-lookup.md)
- [ADR-0007: In-process scheduling with APScheduler and Apprise notifications](0007-in-process-scheduling-with-apscheduler-and-apprise-notifications.md) — shared fan-out/delivery coordination is assigned to its successor.
- [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) — implementation release versioning is distinct from explicit integer API negotiation.
- [RFC 9309: Robots Exclusion Protocol](https://www.rfc-editor.org/rfc/rfc9309.html)
