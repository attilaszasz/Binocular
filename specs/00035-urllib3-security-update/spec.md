---
spec_type: technical
---
# urllib3 Security Update

## Problem Statement
Scheduled scan 37167150207 fails on urllib3 2.7.0 with HIGH CVE-2026-97687 and CVE-2026-97689. Trivy identifies 2.8.0 as the fixed version.

## Scope
Update the active backend dependency resolution and prevent resolving versions below the security floor. Remove unused base-image pip, which vendors a second vulnerable urllib3 copy. Upgrade oauthlib to 4.0.0 to resolve the QC audit blocker, as explicitly authorized. Preserve scanner enforcement and other application dependencies. Publishing and a subsequent GitHub Actions scan are explicitly authorized after QC passes.

## Technical Objectives
### OBJ1 (P1): Remove vulnerable urllib3
Independently testable by inspecting the frozen runtime resolution and scanning a rebuilt image.

## Integration Points
`backend/pyproject.toml`, `backend/uv.lock`, Docker's frozen production sync, existing backend tests and vulnerability scans.

## Requirements
TR-001: Backend resolution MUST use urllib3 >=2.8.0 and declare that security floor.
TR-002: Locked dependencies other than urllib3 and the authorized oauthlib 4.0.0 update, and vulnerability-scan enforcement, MUST remain unchanged.
TR-003: Backend lint, strict typing, tests with >=80% coverage, and a rebuilt-image HIGH/CRITICAL vulnerability scan MUST pass before release readiness is claimed.

## Assumptions & Risks
urllib3 and oauthlib are transitive runtime dependencies via requests/Apprise. oauthlib's major-version update requires compatibility validation. New unrelated advisories may independently block a full security audit. Archived prototype files are out of scope.

## Implementation Signals
Use uv's package-specific lock upgrade; do not hand-edit lockfile hashes or suppress advisories.

## Success Criteria
SC-001 [OBJ1]: The frozen production environment contains a fixed urllib3 version and neither reported CVE appears in the rebuilt image's enforced scan.
SC-002 [OBJ1]: Existing backend tests, lint and strict typing pass with coverage >=80%, with no unrelated dependency upgrades.
