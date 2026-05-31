---
feature_branch: "00008-self-hosted-operability"
created: "2026-05-31"
input: "E013 Self-Hosted Operability"
spec_type: "product"
spec_maturity: "clarified"
epic_id: "E013"
epic_sources: "{PRD:CAP-009}, {SAD:ADR-0008}, {DOD:DDR-002}"
---

# Feature Specification: Self-Hosted Operability

**Feature Branch**: `00008-self-hosted-operability`  
**Created**: 2026-05-31  
**Status**: Draft  
**Spec Type**: product  
**Spec Maturity**: clarified  
**Epic ID**: E013  
**Epic Sources**: {PRD:CAP-009}, {SAD:ADR-0008}, {DOD:DDR-002}  
**Product Document**: specs/prd.md

## Problem Statement

Operators choose Binocular because it should run unattended on a trusted LAN. The foundation has zero-config defaults and persistence primitives, but still needs Docker-secret-compatible credential loading, optional basic protection, and Compose documentation. Without this, self-hosters may leak secrets, lose data across upgrades, or overestimate the security posture.

## Scope

### Included

- Zero-config startup verification with single-volume SQLite persistence.
- Environment variable and `_FILE` secret loading for credentials.
- Optional basic auth for UI and API when explicitly configured.
- `compose.yaml` and `.env.example` with volumes, ports, secrets, and defaults.
- Restart and image-upgrade smoke validation.

### Excluded

- Multi-user accounts, sessions, RBAC, OAuth, or public-internet hardening — out of v1 scope.
- Backup/restore scheduling and restore runbooks — owned by E019.
- Notification credential validation beyond loading secrets — E012.
- Sandboxing extension modules — explicitly out of scope for v1.

### Edge Cases & Boundaries

- Direct env var plus matching `_FILE` var must fail fast to avoid ambiguity.
- Missing, unreadable, or empty secret files must fail visibly without logging secret content.
- Authentication remains disabled unless explicitly enabled and fully configured.
- Basic auth must be documented as light trusted-LAN or TLS reverse-proxy protection.

## User Scenarios & Testing

### User Story 1 - Zero-Config Durable Startup (Priority: P1)

As an operator, I want no-config startup and declared persistent volumes so restarts or upgrades do not erase inventory.

**Why this priority**: P1 because it is the core self-hosted operability promise and blocks safe deployment.

**Independent Test**: Start without env configuration, create state, restart/recreate, and verify state remains.

**Acceptance Scenarios**:

1. **Given** no operator configuration, **When** the app starts, **Then** it serves health and UI/API routes.
2. **Given** inventory data exists on the data volume, **When** the container restarts, **Then** the data remains available.
3. **Given** the same data volume is mounted into a rebuilt image, **When** the app starts, **Then** migrations run safely and existing data remains available.

### User Story 2 - Docker-Compatible Secret Loading (Priority: P1)

As an operator, I want credentials to load from environment variables or Docker secret files so passwords stay out of Compose files and images.

**Why this priority**: P1 because secret handling is required before auth and notification credentials.

**Independent Test**: Configure credentials through env vars and `_FILE` paths and verify values load without secret leakage.

**Acceptance Scenarios**:

1. **Given** a credential value is supplied through `BINOCULAR_AUTH_PASSWORD_FILE`, **When** settings load, **Then** the password is read from that file.
2. **Given** a secret file path is missing or unreadable, **When** settings load, **Then** startup fails visibly with the setting name and no secret content.
3. **Given** both direct and `_FILE` values are present for the same secret, **When** settings load, **Then** startup fails with a clear conflict error.

### User Story 3 - Optional Basic Protection (Priority: P1)

As an operator exposing Binocular beyond a fully trusted LAN, I want opt-in basic auth that is off by default.

**Why this priority**: P1 because ADR-0008 requires truthful trusted-LAN defaults with opt-in protection.

**Independent Test**: Exercise auth-off access, auth-on rejection, and auth-on success for UI and API requests.

**Acceptance Scenarios**:

1. **Given** auth is not enabled, **When** a browser requests the UI or API, **Then** no login prompt is required.
2. **Given** auth is enabled with credentials, **When** a request omits or sends invalid credentials, **Then** the request receives an authentication challenge.
3. **Given** auth is enabled with valid credentials, **When** a request reaches the UI or API, **Then** the request succeeds.

### User Story 4 - Copy-Ready Deployment Examples (Priority: P2)

As an operator, I want Compose and env examples that reflect defaults and the trust boundary.

**Why this priority**: P2 because examples reduce deployment mistakes and secret leakage.

**Independent Test**: Use the examples to start the app and inspect volumes, ports, auth settings, and secret placeholders.

**Acceptance Scenarios**:

1. **Given** the example Compose file, **When** an operator runs it with default values, **Then** Binocular starts on one port with data and modules volumes mounted.
2. **Given** `.env.example`, **When** an operator reviews auth and secret settings, **Then** optional values are present but disabled by default.

## Requirements

### Functional Requirements

- **FR-001**: System MUST start successfully with no required operator-provided configuration.
- **FR-002**: System MUST keep durable state under declared persistent volumes so data survives restart and image replacement.
- **FR-003**: System MUST load credential-like settings from direct environment variables or matching `_FILE` path variables.
- **FR-004**: System MUST fail visibly when a configured secret file is missing, unreadable, or empty, without logging the value.
- **FR-005**: System MUST fail visibly when both direct and `_FILE` values are supplied for the same setting.
- **FR-006**: System MUST provide optional basic-auth protection for UI and API routes when explicitly enabled.
- **FR-007**: System MUST keep authentication disabled by default for the trusted-LAN model.
- **FR-008**: System MUST compare basic-auth credentials using constant-time comparison semantics.
- **FR-009**: System MUST provide a `compose.yaml` example with one exposed port and declared data/modules volumes.
- **FR-010**: System MUST provide an `.env.example` listing operability, auth, and secret-file settings with safe defaults.
- **FR-011**: System MUST document that basic auth is not a sandbox, multi-user security, or a substitute for trusted-network/TLS controls.

### Key Entities

- **Runtime Settings**: Operator configuration for paths, auth, secrets, and binding.
- **Secret File Reference**: `_FILE` path whose contents become the effective secret value.
- **Basic Auth Configuration**: Enable flag plus username/password for optional authentication.
- **Persistent Volume**: Operator-mounted storage for SQLite data, backups, and modules.

## Assumptions & Risks

### Assumptions

- Operators deploy primarily through Docker or Compose on a private LAN.
- Existing SQLite migration behavior remains the source of schema upgrade safety.
- The frontend and API are served from the same FastAPI app and can share middleware protection.
- Secret-file support is for credential-like string settings.
- Operators who expose the app beyond a trusted LAN can provide TLS through a reverse proxy.

### Risks

- **Auth overclaiming** *(likelihood: medium, impact: high)*: Operators may treat basic auth as internet-grade security; mitigate with explicit trusted-LAN language.
- **Secret ambiguity** *(likelihood: medium, impact: medium)*: Direct and `_FILE` values may conflict; mitigate with deterministic precedence tests.
- **Persistence smoke fragility** *(likelihood: low, impact: medium)*: Docker availability may vary; mitigate with a targeted container smoke path.

## Implementation Signals

- `NEW-CONFIG` — auth flag, username/password, and `_FILE` secret resolution.
- `NEW-API` — middleware-level basic-auth enforcement for UI and API requests.
- `NEW-UI` — no new screens required; existing UI must remain accessible behind optional auth.
- `EXTERNAL-SERVICE` — Docker/Compose examples use local container runtime and secret file mounts.
- `NEW-WORKER` — no new background worker required.
- `MIGRATION` — no schema migration expected unless implementation discovers a durable settings record is necessary.

## Success Criteria

### Measurable Outcomes

- **SC-001** [US1]: A no-env startup smoke test reaches `/healthz` successfully.
- **SC-002** [US1]: A persistence smoke test verifies SQLite state remains after container recreation or image rebuild.
- **SC-003** [US2]: Settings tests cover direct env, `_FILE`, missing file, empty file, and precedence without exposing secrets.
- **SC-004** [US3]: Request tests prove auth-off access, auth-on rejection, and auth-on success for API and UI routes.
- **SC-005** [US4]: The example Compose configuration starts the app with one exposed port and declared data/modules volumes.
- **SC-006** [US4]: `.env.example` documents safe defaults and all E013 auth/secret settings.

## Clarifications

### Session 2026-05-31

- Q: How should direct env plus `_FILE` conflicts resolve? -> A: fail fast; no precedence.
- Q: When should basic auth activate? -> A: only when explicitly enabled and both username/password are set.

## Glossary

| Term | Definition |
|------|------------|
| `_FILE` Secret Convention | Environment pattern where a variable points to a file containing the effective secret value. |
| Basic Auth | HTTP username/password authentication used here as optional light protection. |
| Trusted LAN | Private network context assumed by Binocular's default single-user security model. |
| Zero-Config Startup | App startup requiring no operator-provided settings. |

## Compliance Check

**Result**: PASS

- Project instructions satisfied: zero-config preserved, single-volume persistence emphasized, optional auth framed honestly, no external services required, and no sandbox claim introduced.
