# Product Requirements Document: Binocular

> Date: 2026-10-29 | Status: Draft

## Product Overview

Binocular is a self-hosted, single-user web application that automates firmware-update discovery for high-value **offline** devices — cameras, lenses, and homelab hardware that manufacturers never auto-update. It periodically discovers supported models and verifies their firmware through each active catalog-capable module, persisting a shared local model catalog independently of the user's inventory. Owned devices reference catalog models while retaining independent names, installed versions, and notification state. Shared results are compared against every linked device; newer firmware produces configurable responsive HTML Email/SMTP and Gotify alerts. “Global” means shared within this self-hosted instance, never a cloud service or central database.

It runs on a private, trusted LAN with no login, stores all data self-contained (no external database server), and is distributed primarily as a Docker container. The value: replace a manual, easy-to-forget, fragmented chore with reliable, unattended monitoring that surfaces only when action is needed.

## Vision and Why Now

Owners of valuable offline gear — photographers, homelab enthusiasts, tech-savvy hobbyists — must manually police dozens of disparate manufacturer support pages to stay current on firmware. Missing an update can mean lost functionality, unfixed bugs, or an unpatched security issue. Binocular's vision is to make firmware currency a **solved, automated, set-and-forget concern** for self-hosters who value data ownership and privacy.

Why now: the self-hosting / homelab movement has normalized running small, single-purpose containers on a private LAN, and the audience already expects "batteries-included" tools they can deploy once and trust for months. Binocular fills a gap left by vendor ecosystems that assume always-connected devices.

## Problem Statement

Ensuring offline hardware runs the latest firmware is inefficient and fragmented. Users become manual librarians, repeatedly visiting distinct manufacturer support pages, each with its own layout and versioning scheme.

This manual process is:

- **Inefficient** — repetitive checking across multiple, unrelated support websites.
- **Error-prone** — easy to miss critical updates, bug fixes, or security patches.
- **Fragmented** — manufacturers differ widely in page structure and versioning per product line.
- **Duplicated** — checking each owned item independently repeats source discovery for identical models and makes device creation depend on manufacturer availability. A local catalog makes supported models discoverable before ownership and shares verified results without conflating individual devices.

The cost of not solving it: degraded device functionality, missed security fixes, and recurring wasted time for people who own and care about expensive equipment.

## Background and Evidence

Evidence is observational and domain-driven rather than formal market research, consistent with an open-source prosumer tool:

- Manufacturers (e.g., Sony Alpha, Panasonic Lumix, Godox Flashes) publish firmware on heterogeneous, frequently-changing support portals with no unified update feed for offline devices.
- The homelab/self-hosting community has well-documented, consistent product expectations: zero-config first run, single-volume data persistence, non-root containers, dark mode, and honest failure signaling. These expectations are treated as product requirements here, not nice-to-haves.
- Responsible-scraping norms (RFC 9309 robots.txt protocol; descriptive User-Agent identifying the tool; rate limiting and backoff) are established and expected of any tool that fetches third-party pages. Public-data scraping has favorable but **not** absolute legal standing (e.g., *hiQ v. LinkedIn*); ToS and cease-and-desist risk remain.
- Because the product cannot collect telemetry, success must be validated as correctness (right version, no missed updates, no false alerts) before release rather than measured in the field.

## Target Users, Stakeholders, and Core Personas

### Target Users

- Homelab enthusiasts, professional photographers, and tech-savvy hobbyists who own and manage a portfolio of valuable offline devices (roughly 5–50+ items).

### Stakeholders

- **Self-hosting operator** (also the primary user) — deploys, backs up, and maintains the container on a private LAN.
- **Module authors** — users (and potentially a community) who write or share extension modules against the authoring contract.
- **Open-source maintainers** — responsible for the core system and the officially shipped modules.

### Core Personas

- **The Homelabber** — Runs a rack of self-hosted services; expects a single Docker container, one data volume to back up, non-root execution, and a tool that runs untouched for months and only speaks up when there's something to do.
- **The Pro Photographer** — Owns multiple camera bodies and many lenses across a system (e.g., Sony E-mount); wants assurance that none of their gear is silently behind on firmware, without manually trawling support sites.
- **The Tinkerer / Module Author** — Comfortable writing small scripts; wants a clear, documented contract to add support for a new device type and to share that script with others.

## User Needs / Jobs To Be Done

- When I acquire or already own devices, I want to record them and their current firmware version so I have a single inventory of what I need to keep current.
- When I'm adding a device, I want to search the selected module's locally discovered model names and aliases, choose a compatible model, and see source guidance and links without waiting for a manufacturer request.
- When I'm browsing a module, I want to see all discovered models, their latest known firmware and verification freshness, then add a physical device through the same form with its module/model preselected.
- When I own several copies of one model, I want separate names, installed versions, and alerts without repeating manufacturer discovery.
- When I do not know my installed version, I want to record that honestly rather than have the latest available version assumed for me.
- When a manufacturer releases new firmware, I want to be told automatically so I don't have to remember to check.
- When I physically update a device, I want to confirm the new version in one click so alerts reset cleanly.
- When I'm unsure, I want to request a background refresh for a source or the models linked to one/all devices, then compare installed vs. latest known firmware with freshness visible.
- When my gear isn't yet supported, I want to add support myself by writing/importing a module against a documented contract.
- When I want to create a module but don't know the codebase, I want to hand a ready-made prompt kit to my AI coding assistant and get back a valid module with zero prior knowledge.
- When a module I upload fails validation, I want to copy the errors in a format my AI tool can understand so I can iterate to a fix without manual translation.
- When something goes wrong (a page changed, a network error), I want to see honest status and a log rather than silent failure.
- When a shipped official module consistently fails, I want to be notified in the app so I know to check for a project update.
- When I deploy this, I want it to start with sane defaults, persist everything in one place, and survive restarts and upgrades with no data loss.

## Product Principles or UX Principles

- **Data ownership & portability**: All state lives in one backup-able volume; no external backend, no account, no cloud dependency.
- **Honest failure**: Never silently miss. Surface last-success timestamps and errors in the activity log; a broken check must be visible, not invisible.
- **Polite by default**: Identifiable User-Agent, robots.txt respect, source-declared crawl delays, and conservative per-origin pacing/backoff are built in, not optional add-ons. Concurrent checks and retries share the same source pacing automatically, while sources without a longer declared delay retain the default behavior.
- **Least-privilege & explicit trust boundary**: Non-root container; user-supplied/imported modules are explicitly the user's responsibility to vet — the product does not pretend they are sandboxed.
- **Set-and-forget reliability**: Zero-config start, survives restarts and upgrades; correctness is valued over feature breadth.
- **Local extensibility without a marketplace**: A clear authoring contract plus import/export enables sharing; an in-app registry/marketplace is intentionally out of scope. An AI-assisted authoring path (downloadable prompt kit) lowers the barrier to creating valid modules.
- **Responsive & accessible**: Fully usable on mobile and desktop; dark mode is a first-class requirement for this audience.
- **Catalog first, inventory separate**: Model discovery serves the whole local instance, including sources with no owned devices. Browsing, searching, opening forms, and selecting models read local data only; explicit refresh/retry is a separate background action.
- **Installed is not available**: Latest known firmware is reference information, never an automatic installed-version default. Unknown installed or incomparable versions cannot be labeled current.

## Scope Summary

The product scope equals the full product brief: a complete detect → compare → notify loop built on a user-extensible module engine, delivered as a self-hosted container with a responsive UI. Capabilities are prioritized P1–P2 to distinguish the minimum useful loop from supporting and convenience capabilities.

### In-Scope Capabilities

- Module-scoped catalog models with stable identity, display names, source-specific identifiers/aliases, source links, latest verified firmware when available, verification timestamps/status, and compatibility distinctions including region, mount, and hardware revision. Catalog models are not owned inventory; multiple physical devices may reference one model.
- Catalog-driven inventory lifecycle: select a source/module, use an accessible searchable local model dropdown, and save stable identity rather than display text. Show latest known firmware separately from independently entered installed firmware, with an explicit unknown option and no automatic latest-version fill. Preserve source guidance and links, one-click update confirmation, and independent per-device state.
- Modules-page local browsing/search for all discovered models, including unowned models, with latest known firmware, freshness, source links/status, and inventory presence/count. “Add to inventory” opens the shared creation form with module/model preselected and asks for name and installed firmware; presence never prevents adding another physical device. Both entry points use the same catalog, validation, comparison, and notification behavior.
- Both catalog entry points distinguish loading, no discovered models, no search matches, stale data, failed/partial refresh, and unsupported legacy catalog capability. Explicit background refresh/retry exposes progress without coupling ordinary interaction to manufacturer requests. Large catalogs use bounded pages/results and rendering rather than unbounded lists.
- A pluggable module engine with an explicitly versioned catalog-capable contract for model enumeration and firmware verification, supporting shared indexes and per-model details. Upload/update validation, authoring docs, templates, and the AI Module Kit expose the same capabilities. Existing V1 custom modules remain visibly legacy/non-enumerating, with transitional manual entry and per-model checks until explicitly migrated.
- Automated refresh of every active, unpaused catalog-capable module, including those with zero inventory; module-wide frequency and pause controls govern discovery/verification. Single/bulk manual checks refresh unique linked catalog models and reuse source discovery rather than repeat it per owned device; manual requests remain available while automatic work is paused.
- Shared-result comparison after successful model firmware refresh and on device addition, installed-version changes, or update confirmation. Preserve reliable version comparison and responsive HTML Email/SMTP and Gotify. Deduplicate per owned device and verified version across repeated refreshes/concurrent actions; only a newer-than-last-notified version permits a follow-up. Delivery failures remain visible and retryable per channel without resending successful channels. Both channels retain environment-variable initialization/sync.
- Responsible-scraping enforcement provided centrally by the host: robots.txt and valid source-declared crawl delays, identifiable User-Agent, shared per-origin pacing across concurrent requests and retries, and exponential backoff. Multi-request checks adapt without required user configuration, remain bounded, and stop outbound work after timeout or cancellation; sources without a longer declared delay retain default pacing and execution budgets.
- Activity logging with in-UI visibility and rolling/size-bounded retention.
- Official starter modules for Sony Alpha, Panasonic Lumix MFT Cameras, Panasonic Lumix Lenses, Godox Flashes, Viltrox Lenses, Nikon Z-Series, Canon EOS R cameras, and Canon RF/RF-S lenses are automatically seeded and migrated to explicit catalog support within their verified source boundaries. Canon modules remain independently selectable and exact-match Canon Asia English catalogues. Verified firmware is persisted as timestamped local observations; endpoint mappings retain their separate less-than-24-hour validity and visible invalidation/rediscovery policy. A warm live model verification needs one firmware request, not one per owned copy; UI catalog reads need none.
- Self-hosted operability: Docker distribution, single data volume, zero-config startup, non-root execution, configurable container UID/GID (PUID/PGID), responsive UI with dark mode and collapsible navigation.
- Local module sharing enablement: an authoring contract and import/export, plus authoring guidance for module creators — including a downloadable AI Module Kit and AI-friendly validation error output for assisted module creation.
- Official module health monitoring: in-app notification when a shipped official module consistently fails scraping, signaling the need for a project update.

### Out-of-Scope Items

- In-app community module **registry/marketplace** or discovery service (local upload/import/export only).
- Multi-user accounts, authentication beyond optional basic protection, role-based access, or tenancy.
- Any usage telemetry, analytics, or central data collection.
- Automatic application of firmware to devices (Binocular detects and notifies; it never flashes hardware).
- Support for always-online devices that already auto-update through vendor ecosystems.
- External/managed database servers (Postgres, MySQL) or cloud-hosted SaaS deployment.
- A centrally hosted firmware/model database, cross-instance catalog synchronization, or cloud discovery service. Local catalog browsing is not a module marketplace.
- Sandboxed/isolated execution of extension modules (explicitly a user-vetted trust boundary).
- Canon coverage outside the verified Canon Asia English EOS R, RF, and RF-S catalogues, including Cinema EOS/EOS R5 C, cinema lenses, adapters, extenders, unrelated mounts, regional fallback, and firmware-binary retrieval. EOS R5 C may be added only after a separate official catalogue/product/firmware-action flow is verified.

## Product Capability Map

Project-level execution anchors used by `specs/project-plan.md`. These are capability clusters, not feature-level user stories.

| Capability ID | Capability | Priority | Outcome |
|---------------|------------|----------|---------|
| CAP-001 | Device Inventory & Lifecycle | P1 | Both Add Device and model-specific Modules-page actions use one catalog-backed form, save stable module/model identity, allow multiple physical devices, and keep name, installed version/explicit unknown, and one-click confirmation independent of latest known firmware. |
| CAP-002 | Extension Module Engine & Authoring Contract | P1 | Explicit contract-version/capability negotiation supports enumeration and shared/per-model firmware retrieval, with source guidance. Existing V1 custom modules retain labeled manual-entry/per-model checks without invented catalog support. |
| CAP-003 | Module Lifecycle Management | P1 | Upload/update/delete with real-time validation progress identifies V1/V2 capabilities and unsupported versions, preserves model/device identity and module-wide controls on compatible updates, and prevents deletion from silently orphaning inventory. |
| CAP-004 | Automated Scheduled Checking | P1 | Every active, unpaused catalog-capable module discovers models and refreshes shared firmware independently of inventory count; frequency and pause are module-wide, with bounded polite work. |
| CAP-005 | Manual On-Demand Checking | P1 | Explicit source/model/single/bulk background refresh coalesces shared work; local browsing/typing/selection never initiates requests. Installed/latest comparison and stale/failed progress remain visible. |
| CAP-006 | Update Detection & Comparison | P1 | Successful shared model verification fans out to all linked devices; add/edit/confirmation reevaluates locally. Unknown installed or incomparable versions never imply current, and stale/failed observations are labeled rather than treated as new verification. |
| CAP-007 | Notification & Alerting | P1 | Reliable HTML Email/SMTP and Gotify alerts deduplicate per device/version/channel under concurrent/repeated reevaluation. Only newer-than-last-notified releases create follow-ups; failures stay visible/retryable without resending successful channels. Environment configuration remains supported. |
| CAP-008 | Responsible Scraping Enforcement | P1 | All outbound checks automatically honor robots.txt and valid source-declared crawl delays, use an identifiable User-Agent, and share conservative per-origin pacing across concurrent requests and every retry with exponential backoff. Multi-request checks remain bounded and cancellation-safe, while sources without a longer declared delay retain default pacing and execution budgets. |
| CAP-009 | Self-Hosted Operability | P1 | Single-container, single-volume, zero-config, non-root deployment with PUID/PGID support that survives restarts and upgrades with no data loss. Settings, authentication, and notification channels can be configured or updated via container environment variables. |
| CAP-010 | Activity Logging & Visibility | P2 | All check activity and errors are recorded in a size-bounded, in-UI viewable log. |
| CAP-011 | Official Starter Modules | P2 | Sony Alpha, Panasonic Lumix MFT Cameras, Panasonic Lumix Lenses, Godox Flashes, Viltrox Lenses, and Nikon Z-Series modules seed automatically and provide fixture-verified catalog enumeration/firmware retrieval within supported compatibility boundaries. |
| CAP-012 | Responsive UI & Dark Mode | P2 | The interface is fully usable on mobile and desktop with first-class dark mode and collapsible navigation with version display. |
| CAP-013 | Module Authoring Guidance & AI-Assisted Dev Kit | P2 | Version-aligned docs, validator/harness, templates, examples, AI Module Kit, and copyable errors teach enumeration, stable variants, shared indexes/per-model details, freshness/failures, and explicit V1-to-catalog migration without silently changing existing modules. |
| CAP-014 | Official Module Health Monitoring | P2 | When a shipped official module consistently fails scraping, an in-app notification alerts the operator to check for a project update with a fixed module. |
| CAP-015 | Official Canon RF Modules | P2 | Independent Canon camera/lens modules enumerate exact Canon Asia EOS R and RF/RF-S catalogues, deduplicate OS packages, and persist verified observations with official release links/status. Mappings younger than 24 hours enable one live request per warm model verification; shared local UI reads need none, and expired/failed mappings rediscover visibly. |
| CAP-016 | Instance-Local Model Catalog | P1 | A persistent module-scoped catalog separates stable compatible model identities, names/aliases/source IDs/links, firmware observations, and verification outcomes from owned devices; all active catalog sources refresh even when unowned. |
| CAP-017 | Module Catalog Browsing & Onboarding | P1 | Bounded accessible local search/browse shows all module models, known firmware, freshness/status/links and inventory presence, with direct shared-form creation and clear loading/empty/stale/failed/legacy states plus explicit background refresh/retry. |

## Success Metrics / KPIs / Desired Outcomes

Success is defined by **reliability and correctness**, validated before release rather than measured via field telemetry (none is collected).

| Metric | Target | Why It Matters | Measurement Window |
|--------|--------|----------------|-------------------|
| Version-detection correctness | Detected latest == actual published latest for supported modules | The product's core promise is trustworthy detection. | Per release, against captured page fixtures |
| Missed-update rate (false negatives) | Zero for supported device types | A silently missed update is the most damaging failure. | Per release, fixture + regression validation |
| False-alert rate (false positives) | Zero for supported device types | False alerts erode set-and-forget trust. | Per release, fixture + regression validation |
| Scraper resilience to source changes | Source changes produce a visible "scrape failed" status, never a silent miss | Manufacturer pages change; honest failure is the safeguard. | Per release + when a source breaks |
| Responsible-scraping correctness | Effective source delay is enforced across concurrent requests and every retry; timed-out or cancelled checks issue no further requests | Source policy and bounded execution must hold under real multi-request behavior, not only isolated requests. | Per release, deterministic pacing/retry/cancellation tests |
| Catalog UI isolation and scale | Zero manufacturer requests while opening/typing/selecting/browsing; bounded results/rendering with 10,000 discovered models | Catalog usability must not depend on vendor availability or an unbounded model list. | Per release, local-query and accessible UI tests |
| Shared-discovery efficiency | One shared index fetch per refresh scope where source permits; one verification per unique model, independent of owned-copy count | Adding physical copies must not multiply manufacturer discovery. | Per release, scripted request-count and zero-inventory scheduler tests |
| Canon live-verification latency | One paced firmware request for a fresh endpoint mapping; 0-30 seconds for an uncontended warm lookup | Whole-catalog jobs may take longer; cold model discovery may take 90-120 seconds. Local browsing never waits for this work. | Per release, injected-time background/manual refresh tests |
| Independent inventory correctness | Unknown installed never current; all linked devices reevaluate on successful refresh/add/edit/confirm; zero duplicate application dispatches from repeated/concurrent actions | Shared results must not merge physical-device state or create alert storms. | Per release, concurrency/restart/channel retry tests |
| Notification delivery success | Detected update reliably produces a delivered Email (responsive HTML, light-themed) and Gotify notification | The alert is the entire point of an unattended tool. | Per release, end-to-end alert-path test |
| Unattended reliability | Runs across restarts/upgrades with no data loss | "Set and forget" is the operability promise. | Per release, restart/upgrade smoke test |

## Assumptions

- Users operate on a private, trusted LAN and accept a single-user, no-login model.
- Users can self-host a Docker container (or run the app on a host runtime) and provide a persistent volume.
- Users either have or can configure an SMTP server and/or a Gotify instance for notifications.
- Manufacturer firmware pages remain publicly reachable and scrapable (subject to change).
- Users accept responsibility for vetting any third-party/imported extension module they run.
- Devices to be tracked are offline / not auto-updating through a vendor ecosystem.

## Constraints

- Self-contained data storage only — no external database server.
- Single-user, single-instance operation on a trusted network; not designed for public internet exposure or multi-tenancy.
- Distributed primarily as a Docker container; must also be runnable on a host with standard language runtimes.
- Must start with zero required configuration and persist all state in one clearly defined data volume.
- Container must run as a non-root user with configurable UID/GID (PUID/PGID).
- No telemetry or central data collection is permitted by design.

## Dependencies

- Manufacturer firmware pages' structure and availability (Sony Alpha, Panasonic Lumix, Godox Flashes, Viltrox, Nikon Z-Series, Canon Asia EOS R/RF/RF-S catalogues, and any user-added sources).
- An SMTP server and/or a Gotify instance for notification delivery.
- A Docker/OCI-compatible runtime and a persistent volume for data and modules.
- Network egress from the trusted LAN to manufacturer sites.
- User-authored or imported extension modules for device types beyond the shipped examples.

## Risks

- **Scraper breakage** when manufacturer pages change — highest operational risk; mitigated by clear failure signaling rather than silent misses.
- **Arbitrary code execution** from user-supplied/imported modules running unsandboxed with the app's privileges — mitigated by least-privilege/non-root execution and an explicit user-vetting trust boundary, not by sandboxing.
- **Legal / ToS exposure** from scraping third-party sites despite favorable public-data case law — mitigated by polite-scraping defaults and clear user guidance; cannot be eliminated.
- **Invisible false negatives** (missed updates) being undetectable without telemetry — mitigated by fixture-based correctness validation at release.
- **Notification-channel failures** (SMTP/Gotify misconfiguration or outage) going unnoticed — mitigated by activity-log visibility and delivery validation.
- **Aggressive or inconsistent polling** harming sources or the project's reputation — mitigated by conservative default pacing, source-declared crawl-delay support, shared per-origin enforcement across concurrency and retries, and backoff.
- **Long source-declared delays** causing multi-request checks to exceed their useful execution window — mitigated by automatic bounded budgets, visible failure when work cannot complete, and cancellation that prevents further background requests without changing budgets for unaffected sources.
- **Regional catalogue gaps** causing apparent Canon RF coverage to exceed verified support — mitigated by documenting Canon Asia as the authority, matching only exact catalogue products, and explicitly excluding Cinema EOS/EOS R5 C until its product and firmware flow is verified. RF-S catalogue support must not imply that a positive RF-S firmware release has been observed.
- **Stale Canon endpoint mappings** causing an apparent successful check to hide source drift — mitigated by a 24-hour freshness limit, invalidation on cached-endpoint transport/status/parsing/model-identity failure, one full rediscovery fallback, and visible failure when recovery cannot verify a live version.
- **Compatibility identity collisions** across region/mount/hardware revisions — mitigate with stable variant-specific identity and explicit review of ambiguous legacy inventory mappings, never display-name-only guessing.
- **Full catalogs increasing source load** even with no owned devices — mitigate with shared indexes, bounded refresh work, source pacing, module-wide pause/frequency, and visible partial progress rather than inventory-based suppression.
- **Stale knowledge or ambiguous delivery** being mistaken for freshness or guaranteed delivery — retain last-known provenance and independent attempt status; show uncertain delivery for deliberate retry rather than silently resending.

## Open Questions

- None for this amendment. Official-source failures remain in-app guidance under CAP-014, extended to inventory-independent catalog refresh; catalog knowledge stays local and V1 compatibility remains explicit.

## Release or Validation Approach

Validation is correctness-first and pre-release, since the product collects no field telemetry:

- **Fixture-based correctness**: Captured real-page snapshots for every official module verify that detected latest versions match actual published versions, with regression coverage when sources change. Canon coverage includes catalogue-to-product-to-firmware-action discovery, exact near-name rejection, adapter/extender exclusion, OS-package deduplication, official release-page links, and explicit no-firmware fixtures where no positive RF-S release is verified.
- **Official-module integration**: Validate every shipped module's negotiated catalog capability, complete/partial enumeration, stable compatible identities, shared index reuse, and firmware/no-firmware/error outcomes with captured fixtures. Canon retains independent modules, exact matching, automatic seeding, 24-hour endpoint expiry/invalidation, restart persistence, coalesced live verification, and one full rediscovery fallback. Persisted firmware is a timestamped local observation, never a new live check; 0-30 second uncontended warm and 90-120 second cold model latency are not whole-catalog deadlines.
- **Catalog and onboarding validation**: Exercise local Add Device and Modules browsing against 10,000 models with bounded query/render sizes, accessible keyboard/status behavior, all loading/empty/no-match/stale/failed/legacy states, explicit refresh/retry, aliases and compatibility variants, direct preselection, and multiple physical copies. Assert no manufacturer requests from ordinary form/browse interaction and no installed-version autofill.
- **Migration and shared-loop validation**: Preserve device IDs/names/installed and notification history, module identity/frequency/pause, and unresolved legacy entries; test zero-inventory refresh, partial failure without freshness inflation, fan-out and local reevaluation, concurrent/repeated deduplication, channel failures, explicit uncertain-delivery handling, retry, and restart recovery. V1 remains operational and visibly non-catalog until explicitly upgraded.
- **Regional coverage documentation**: Release documentation identifies Canon Asia English as the verified region, lists EOS R and RF/RF-S catalogue boundaries, excludes unrelated mounts and non-lens accessories, explicitly marks Cinema EOS/EOS R5 C unsupported pending verification, and states that no positive RF-S firmware release was verified.
- **End-to-end alert-path smoke test**: Exercise the full detect → compare → notify loop for both notification channels (Email/SMTP and Gotify).
- **Operability smoke test**: Verify zero-config startup, single-volume persistence, non-root execution, and no data loss across restarts and upgrades.
- **Responsible-scraping verification**: Deterministically confirm delay selection, robots.txt respect, identifiable User-Agent, shared per-origin pacing across concurrent requests and every retry, exponential backoff, bounded multi-request execution, preserved default budgets, and no requests after timeout or cancellation.
- **Initial release**: Ship the full scope with the official modules as both immediate value and authoring templates; broader device coverage grows through user/community-authored modules.

## Domain Glossary / Terminology

- **Device**: A physical owned item with its own name, installed version (or explicit unknown), and notification state; normally linked to a module-scoped catalog model. Multiple devices may share that model. Transitional V1/unresolved inventory retains a labeled legacy association.
- **Catalog model**: A supported model/firmware-compatible variant with stable module-scoped identity, names/aliases/source identifiers and links; exists independently of ownership.
- **Firmware observation**: Latest verified source result with provenance and verification time; may become stale or have a failed subsequent attempt without becoming a new success.
- **Global/shared catalog**: Local data shared by inventory and interfaces inside this self-hosted instance only.
- **Device Type**: A firmware-source grouping (e.g., "Sony E-Mount Lenses") — derived from the extension module a device is linked to, rather than assigned directly by the user.
- **Extension Module**: A user-managed source integration declaring contract/capabilities. Catalog-capable modules enumerate compatible models and verify firmware; legacy V1 modules only check explicitly supplied model inputs. Device type remains module-derived.
- **Authoring Contract**: The strict, documented interface every module must implement to return data in a standardized format.
- **Refresh/check**: Explicit or scheduled background verification of a source/model; catalog results are shared across linked devices. A local lookup or comparison is not a manufacturer check.
- **Update Confirmation**: Explicit one-click acknowledgment after physically updating a device, recording the displayed target version and reevaluating its state without erasing delivered-version deduplication history.
- **Activity Log**: The size-bounded, in-UI record of all check activity and errors.
- **Responsible / Polite Scraping**: Fetching third-party pages while honoring robots.txt and valid source-declared crawl delays, sending an identifiable User-Agent, and applying shared per-origin pacing and backoff within bounded, cancellation-safe checks.

## Handoff Guidance

Context that downstream architecture design or governance work must preserve.

- **Product intent to preserve**: A reliable, unattended detect → compare → notify loop for offline devices; honest failure signaling over silent misses; data ownership with zero external backend.
- **Scope boundaries to respect**: No marketplace/registry, no multi-user, no telemetry, no automatic firmware flashing; local module upload/import/export only; modules run as an explicit user-vetted trust boundary (not sandboxed).
- **Critical constraints**: Self-contained storage (no external DB), single-container/single-volume/zero-config/non-root operability with PUID/PGID, primary Docker distribution with host-runtime fallback, polite-scraping defaults are mandatory.
- **Catalog handoff**: Separate inventory from model identity and verification; retain compatibility variants and source guidance, local-only bounded browsing, shared Add Device/Modules creation, unknown installed semantics, inventory-independent module refresh, explicit V1 migration/fallback, and per-device concurrent notification deduplication with delivery retry visibility.
- **Health behavior to preserve**: Official-module failure guidance covers catalog refresh even with zero inventory, distinguishing authoritative no-firmware from source breakage; retained last-known results never hide failed verification.
- **Prototype learnings to incorporate**: Device type derived from linked module (not standalone entity); start with shadcn/ui component library from the outset; notification deduplication is essential; HTML email notifications are required; PUID/PGID entrypoint needed for homelab volume permissions; schema should be consolidated from the start to avoid fix migrations. On the Inventory page, device cards must have a compact layout and exclude the derived device_type badge to prevent confusing display when a module supports multiple device types.

## Project Context Baseline Updates

*Managed section — rewritten by SDD planning agents. Do not edit manually.*

- Reserved for reusable project-level product context promoted from downstream runs.
- Firmware-source display guidance is separate from stable module identity. Human-readable coverage, model examples, and region notes describe verified matching behavior; canonical scraped-source links and consumer help links serve distinct purposes.
- Frequency and pause are module-wide controls affecting discovery and all linked devices, including sources with no inventory. Paused sources disable automatic monitoring without implying that explicit manual refresh is unavailable.
- Catalog-backed creation replaces live version search for catalog-capable modules. The old manual-entry/per-model version-search behavior is transitional for V1 custom modules or explicitly unresolved migrated inventory only; it must not be silently presented as catalog support.
