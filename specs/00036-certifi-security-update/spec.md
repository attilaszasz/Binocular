---
spec_type: technical
---
# certifi Security Update

## Problem Statement
Scheduled image scan 40146909923 fails on certifi 2026.6.17 with CRITICAL GHSA-6q48-6c7w-9gw2 (compromised CA certificates). Trivy identifies 2026.10.19 as fixed.

## Scope
Update the active backend security floor and frozen resolution for certifi, plus the user-authorized development-only filelock 4.2.1 remediation. Preserve scanner policy. Publishing, pushing, merging and deployment require separate authorization. Archived prototype dependencies are excluded.

## Technical Objectives
### OBJ1 (P1): Remove vulnerable certifi
Independently testable through the frozen runtime version and an enforced rebuilt-image vulnerability scan.

## Integration Points
`backend/pyproject.toml`, `backend/uv.lock`, Docker frozen production sync, backend checks and Trivy.

## Requirements
TR-001: Runtime dependencies MUST declare certifi>=2026.10.19 and lock a fixed version.
TR-002: Locked package versions other than certifi and the authorized filelock 4.2.1 update, and security scanner configuration, MUST remain unchanged. filelock MUST remain development-only with a fixed-version floor.
TR-003: Backend lint, strict typing, tests with >=80% coverage and an enforced rebuilt-image HIGH/CRITICAL scan MUST pass before release readiness is claimed.

## Assumptions & Risks
certifi is transitive through HTTP clients. Removing compromised roots intentionally changes TLS trust. Unrelated new advisories may block release independently.

## Implementation Signals
Use uv's targeted upgrade; preserve generated integrity hashes. Do not add vulnerability ignores.

## Success Criteria
SC-001 [OBJ1]: Frozen production dependencies contain certifi>=2026.10.19 and the rebuilt image passes the enforced scan.
SC-002 [OBJ1]: Backend lint, strict typing and tests pass with >=80% coverage and no unrelated locked package upgrades.

## Clarifications
No unresolved questions: the user authorized the repair, not external publication.
The user additionally authorized upgrading development-only filelock to 4.2.1 to clear the full dependency-audit blocker.
After QC passed, the user authorized publishing the changes and making a patch release. Use a green-CI pull request, then the next unused patch tag and the existing Release workflow; verify the published image with the scheduled scan.
