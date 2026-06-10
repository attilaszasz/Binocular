---
adr_id: ADR-0008
status: accepted
date: 2026-05-31
tags: [security, trust-boundary, operations]
supersedes: []
superseded_by: ""
related_artifacts: [specs/prd.md#Constraints, specs/prd.md#Risks]
---

# ADR-0008: Trusted-LAN single-user security model with optional basic auth

## Status

Accepted.

## Context

Binocular is designed for a private, trusted LAN and a single user who is also the operator (PRD constraints: single-user, single-instance, no telemetry, not designed for public internet exposure). It also executes user-installed extension modules in-process with no sandbox (ADR-0005). A coherent security/trust model must be defined: authentication posture, the module trust boundary, container privilege level, and secrets handling.

## Decision Drivers

- Match the trusted-LAN, single-user product constraint without friction
- Avoid mandatory accounts/login on a private tool (homelab UX expectation)
- Provide a defense option for users who expose the UI more broadly
- Least-privilege operation despite unsandboxed modules
- Safe handling of notification credentials/secrets

## Considered Options

### Option A: Trusted-LAN no-auth default with optional basic auth

No authentication by default (trusted-LAN assumption), with OPTIONAL basic-auth middleware the operator can enable; treat installed extension modules as an explicit user-vetted trust boundary (no sandbox); run the container as a non-root user (PUID/PGID support); load sensitive config via env vars / `_FILE` (Docker secrets) and never hardcode credentials.

- **Pros**: Zero-friction default for the target audience; optional hardening; least-privilege mitigations layered around the accepted ACE risk.
- **Cons**: Insecure if naively exposed to the public internet; module ACE risk remains by design.

### Option B: Mandatory authentication / user accounts

- **Pros**: Stronger default posture.
- **Cons**: Conflicts with single-user trusted-LAN UX; adds account/session management complexity disproportionate to the threat model.

### Option C: Network-only security

Rely entirely on the user's firewall.

- **Pros**: Simplest.
- **Cons**: No in-app option at all for users who reverse-proxy the UI; weaker secrets discipline.

## Decision Outcome

Chosen option: **A: trusted-LAN no-auth default with optional basic auth, explicit module trust boundary, non-root container, and disciplined secrets handling** — this matches the product's stated environment and audience. A default with no login keeps the homelab UX frictionless, while optional basic-auth middleware gives users who expose the UI a built-in safeguard. The unsandboxed-module arbitrary-code-execution risk (ADR-0005) is accepted under the single-operator trust model and mitigated — not eliminated — by running as a non-root user and documenting that the operator is responsible for vetting modules. Secrets (SMTP/Gotify credentials) load via env/`_FILE` patterns and are never hardcoded.

## Consequences

### Positive

- Frictionless default for trusted LANs.
- Optional hardening path via basic-auth middleware.
- Least-privilege via non-root container.
- Clean secrets handling.

### Negative

- Not safe to expose to the public internet without the optional auth and a reverse proxy.
- Module ACE risk persists by design.

### Neutral

- Security posture is documented prominently for operators.
- This ADR governs the project's trust boundaries referenced by the extension-engine and scraping ADRs.

## Links

- specs/prd.md — Constraints (trusted-LAN, single-user)
- specs/prd.md — Risks (arbitrary code execution)
- ADR-0005 (unsandboxed extension engine)
- ADR-0006 (centralized scraping client)
