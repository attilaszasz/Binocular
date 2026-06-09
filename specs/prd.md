# Product Requirements Document: Binocular

> Date: 2026-05-31 | Status: Draft

## Product Overview

Binocular is a self-hosted, single-user web application that automates the discovery of firmware updates for high-value **offline** devices — cameras, lenses, and homelab hardware that manufacturers never auto-update. Users maintain a digital inventory of their devices, each explicitly linked to an extension module, and Binocular periodically checks manufacturer firmware pages using those modules. When a newer version than the user's recorded version is found, Binocular notifies them through configurable channels (responsive HTML Email/SMTP matching the application light color scheme, and Gotify).

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
- When a manufacturer releases new firmware, I want to be told automatically so I don't have to remember to check.
- When I physically update a device, I want to confirm the new version in one click so alerts reset cleanly.
- When I'm unsure, I want to trigger an immediate check for one device or all devices and compare stored vs. latest side by side.
- When my gear isn't yet supported, I want to add support myself by writing/importing a module against a documented contract.
- When I want to create a module but don't know the codebase, I want to hand a ready-made prompt kit to my AI coding assistant and get back a valid module with zero prior knowledge.
- When a module I upload fails validation, I want to copy the errors in a format my AI tool can understand so I can iterate to a fix without manual translation.
- When something goes wrong (a page changed, a network error), I want to see honest status and a log rather than silent failure.
- When I deploy this, I want it to start with sane defaults, persist everything in one place, and survive restarts and upgrades with no data loss.

## Product Principles or UX Principles

- **Data ownership & portability**: All state lives in one backup-able volume; no external backend, no account, no cloud dependency.
- **Honest failure**: Never silently miss. Surface last-success timestamps and errors in the activity log; a broken check must be visible, not invisible.
- **Polite by default**: Identifiable User-Agent, robots.txt respect, and conservative per-source rate limits/backoff are built in, not optional add-ons.
- **Least-privilege & explicit trust boundary**: Non-root container; user-supplied/imported modules are explicitly the user's responsibility to vet — the product does not pretend they are sandboxed.
- **Set-and-forget reliability**: Zero-config start, survives restarts and upgrades; correctness is valued over feature breadth.
- **Local extensibility without a marketplace**: A clear authoring contract plus import/export enables sharing; an in-app registry/marketplace is intentionally out of scope. An AI-assisted authoring path (downloadable prompt kit) lowers the barrier to creating valid modules.
- **Responsive & accessible**: Fully usable on mobile and desktop; dark mode is a first-class requirement for this audience.

## Scope Summary

The v1 product scope equals the full product brief: a complete detect → compare → notify loop built on a user-extensible module engine, delivered as a self-hosted container with a responsive UI. Capabilities are prioritized P1–P3 to distinguish the minimum useful loop from supporting and convenience capabilities.

### In-Scope Capabilities

- Device inventory and lifecycle management, with each device linked to an extension module that determines its device type, stored current versions, and one-click update confirmation.
- A pluggable extension-module engine with a strict authoring contract, plus full module lifecycle management (upload, update, delete) through the UI.
- Automated scheduled checking with per-device-type frequency, plus manual on-demand checks (single and bulk) with side-by-side version comparison.
- Update detection, version comparison, and notification dispatch via responsive HTML Email/SMTP (matching the light color scheme) and Gotify. Only one notification is sent per detected version; a follow-up notification is dispatched only when an even newer version than the last-notified version is found.
- Responsible-scraping enforcement (robots.txt, identifiable User-Agent, rate limiting, backoff) provided centrally by the host.
- Activity logging with in-UI visibility and rolling/size-bounded retention.
- Officially shipped starter modules for Sony Alpha, Panasonic Lumix MFT Cameras, Panasonic Lumix Lenses, and Godox Flashes that are automatically seeded and registered in the database on startup as working examples and templates.
- Self-hosted operability: Docker distribution, single data volume, zero-config startup, non-root execution, responsive UI with dark mode.
- Local module sharing enablement: an authoring contract and import/export, plus authoring guidance for module creators — including a downloadable AI Module Kit and AI-friendly validation error output for assisted module creation.

### Out-of-Scope Items

- In-app community module **registry/marketplace** or discovery service (local upload/import/export only).
- Multi-user accounts, authentication beyond optional basic protection, role-based access, or tenancy.
- Any usage telemetry, analytics, or central data collection.
- Automatic application of firmware to devices (Binocular detects and notifies; it never flashes hardware).
- Support for always-online devices that already auto-update through vendor ecosystems.
- External/managed database servers (Postgres, MySQL) or cloud-hosted SaaS deployment.
- Sandboxed/isolated execution of extension modules (explicitly a user-vetted trust boundary in v1).

## Product Capability Map

Project-level execution anchors used by `specs/project-plan.md`. These are capability clusters, not feature-level user stories.

| Capability ID | Capability | Priority | Outcome |
|---------------|------------|----------|---------|
| CAP-001 | Device Inventory & Lifecycle | P1 | Users maintain an inventory of devices each linked to an extension module, with stored versions and one-click update confirmation. |
| CAP-002 | Extension Module Engine & Authoring Contract | P1 | A strict, documented contract lets modules supply device-specific firmware-checking intelligence in a standardized format. |
| CAP-003 | Module Lifecycle Management | P1 | Users upload, update, and delete modules through the UI to control which device types are supported. |
| CAP-004 | Automated Scheduled Checking | P1 | The system checks sources unattended on a per-device-type frequency. |
| CAP-005 | Manual On-Demand Checking | P1 | Users trigger immediate single or bulk checks and compare stored vs. latest versions side by side. |
| CAP-006 | Update Detection & Comparison | P1 | The system reliably determines whether a newer version exists than the user's recorded version. |
| CAP-007 | Notification & Alerting | P1 | Newer-version detections dispatch notifications once per version via configurable responsive HTML Email/SMTP (light-themed, mobile-friendly) and Gotify channels, with re-notification only when a version newer than the last-notified version appears. |
| CAP-008 | Responsible Scraping Enforcement | P1 | All outbound checks honor robots.txt, identifiable User-Agent, rate limits, and backoff by default. |
| CAP-009 | Self-Hosted Operability | P1 | Single-container, single-volume, zero-config, non-root deployment that survives restarts and upgrades with no data loss. |
| CAP-010 | Activity Logging & Visibility | P2 | All check activity and errors are recorded in a size-bounded, in-UI viewable log. |
| CAP-011 | Official Starter Modules | P2 | Sony Alpha, Panasonic Lumix MFT Cameras, Panasonic Lumix Lenses, and Godox Flashes modules are automatically registered and seeded in the database on startup, serving as immediate value and templates. |
| CAP-012 | Responsive UI & Dark Mode | P2 | The interface is fully usable on mobile and desktop with first-class dark mode. |
| CAP-013 | Module Authoring Guidance & AI-Assisted Dev Kit | P2 | Authoring docs, a downloadable AI Module Kit (prompt instructions, contract reference, templates, examples), an in-UI "Create a Module" guidance section, and AI-friendly validation error copy-paste empower users — especially those working with AI coding assistants — to create and iterate on valid modules with zero prior codebase knowledge. |

## Success Metrics / KPIs / Desired Outcomes

Success is defined by **reliability and correctness**, validated before release rather than measured via field telemetry (none is collected).

| Metric | Target | Why It Matters | Measurement Window |
|--------|--------|----------------|--------------------|
| Version-detection correctness | Detected latest == actual published latest for supported modules | The product's core promise is trustworthy detection. | Per release, against captured page fixtures |
| Missed-update rate (false negatives) | Zero for supported device types | A silently missed update is the most damaging failure. | Per release, fixture + regression validation |
| False-alert rate (false positives) | Zero for supported device types | False alerts erode set-and-forget trust. | Per release, fixture + regression validation |
| Scraper resilience to source changes | Source changes produce a visible "scrape failed" status, never a silent miss | Manufacturer pages change; honest failure is the safeguard. | Per release + when a source breaks |
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
- Container must run as a non-root user.
- No telemetry or central data collection is permitted by design.

## Dependencies

- Manufacturer firmware pages' structure and availability (Sony Alpha, Panasonic Lumix, Godox Flashes, and any user-added sources).
- An SMTP server and/or a Gotify instance for notification delivery.
- A Docker/OCI-compatible runtime and a persistent volume for data and modules.
- Network egress from the trusted LAN to manufacturer sites.
- User-authored or imported extension modules for device types beyond the shipped examples.

## Risks

- **Scraper breakage** when manufacturer pages change — highest operational risk; mitigated by clear failure signaling rather than silent misses.
- **Arbitrary code execution** from user-supplied/imported modules running unsandboxed with the app's privileges — mitigated by least-privilege/non-root execution and an explicit user-vetting trust boundary, not by sandboxing in v1.
- **Legal / ToS exposure** from scraping third-party sites despite favorable public-data case law — mitigated by polite-scraping defaults and clear user guidance; cannot be eliminated.
- **Invisible false negatives** (missed updates) being undetectable without telemetry — mitigated by fixture-based correctness validation at release.
- **Notification-channel failures** (SMTP/Gotify misconfiguration or outage) going unnoticed — mitigated by activity-log visibility and delivery validation.
- **Aggressive default polling** harming sources or the project's reputation — mitigated by conservative default rate limits and backoff.

## Open Questions

- Should optional basic authentication be encouraged or off by default for users who expose the UI beyond a fully trusted LAN?
- What is the appropriate default check frequency that balances timeliness against polite-scraping load?
- How should the product communicate when a shipped official module breaks due to a manufacturer page change (in-app guidance vs. project-side update)?

## Release or Validation Approach

Validation is correctness-first and pre-release, since the product collects no field telemetry:

- **Fixture-based correctness**: Captured real-page snapshots for the official Sony, Panasonic, and Godox modules verify that detected latest versions match the actual published versions, with regression coverage when sources change.
- **End-to-end alert-path smoke test**: Exercise the full detect → compare → notify loop for both notification channels (Email/SMTP and Gotify).
- **Operability smoke test**: Verify zero-config startup, single-volume persistence, non-root execution, and no data loss across restarts and upgrades.
- **Responsible-scraping verification**: Confirm robots.txt respect, identifiable User-Agent, rate limiting, and backoff behavior before release.
- **Initial release**: Ship the full v1 scope with the official modules as both immediate value and authoring templates; broader device coverage grows through user/community-authored modules.

## Domain Glossary / Terminology

- **Device**: A single owned hardware item (e.g., a specific camera body) with a recorded current firmware version. Each device is explicitly linked to an extension module at creation, and its device type is derived from that module.
- **Device Type**: A firmware-source grouping (e.g., "Sony E-Mount Lenses") — derived from the extension module a device is linked to, rather than assigned directly by the user.
- **Extension Module**: A user-managed script implementing the authoring contract that knows how to determine the latest firmware version for a device type. Each module defines its device type, and devices are explicitly linked to a module — the module determines the device's type.
- **Authoring Contract**: The strict, documented interface every module must implement to return data in a standardized format.
- **Check**: An execution (manual or scheduled) that uses a module to determine the latest available version for a device.
- **Update Confirmation**: The one-click action a user takes after physically updating a device, syncing the stored version and resetting alert status.
- **Activity Log**: The size-bounded, in-UI record of all check activity and errors.
- **Responsible / Polite Scraping**: Fetching third-party pages while honoring robots.txt, sending an identifiable User-Agent, and applying rate limits and backoff.

## Handoff Guidance

Context that downstream architecture design or governance work must preserve.

- **Product intent to preserve**: A reliable, unattended detect → compare → notify loop for offline devices; honest failure signaling over silent misses; data ownership with zero external backend.
- **Scope boundaries to respect**: No marketplace/registry, no multi-user, no telemetry, no automatic firmware flashing; local module upload/import/export only; modules run as an explicit user-vetted trust boundary (not sandboxed in v1).
- **Critical constraints**: Self-contained storage (no external DB), single-container/single-volume/zero-config/non-root operability, primary Docker distribution with host-runtime fallback, polite-scraping defaults are mandatory.
- **Open decisions needing technical input**: Optional auth default posture; default check-frequency balance vs. scraping load; mechanism for signaling and recovering from broken official modules.

## Project Context Baseline Updates

*Managed section — rewritten by SDD planning agents. Do not edit manually.*

- Reserved for reusable project-level product context promoted from downstream runs.
