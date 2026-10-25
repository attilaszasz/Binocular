# Plan: certifi Security Update

## Technical Context
Python 3.13; uv; FastAPI/httpx/requests; frozen production dependencies; multi-stage Alpine Docker image; Trivy.

## Clarification
No unresolved requirements. Local repair and validation only; no publication authorization.
The user authorized the filelock 4.2.1 major-version upgrade after the initial audit failure.
After QC PASS, the user authorized pushing, merging through a green-CI pull request and publishing a patch release. The next unused patch tag is v0.1.30 (remote tags checked). Follow the existing release workflow, then dispatch and verify the published-image scheduled scan. Earlier no-publication statements describe the pre-authorization state.

## Instructions Check
PASS: No application logic, persistence, centralized HTTP-client, module trust, privilege or UI changes. Preserve strict analysis, >=80% coverage and enforced image scanning. The existing Alpine-versus-documented-slim discrepancy predates this repair and is unchanged.

## Implementation
Add certifi>=2026.10.19 to runtime dependencies and regenerate backend/uv.lock using uv lock --upgrade-package certifi. Compare package versions to ensure only certifi changed. Sync frozen dependencies, verify the installed version, and run backend checks. Build a local image and scan with the scheduled workflow's severity, ignore-unfixed and repository ignore-file policy. Do not publish or weaken scanning.
Authorized remediation: add filelock>=4.2.1,<5 to the dev dependency group and use a package-specific uv lock upgrade constrained to filelock==4.2.1. Verify only certifi and filelock versions differ from HEAD, filelock is absent from the production dependency export, and the full pip-audit passes. Re-run backend and frontend quality gates, image build and enforced scan before QC.

## Testing Strategy
Backend: uv sync --frozen; uv run --frozen ruff check .; uv run --frozen mypy .; uv run --frozen pytest --cov=binocular --cov-report=term-missing; uv run --frozen pip-audit.
Image: docker build -t binocular:certifi-security-fix .; trivy image --severity HIGH,CRITICAL --ignore-unfixed --ignorefile .trivyignore --exit-code 1 binocular:certifi-security-fix.
Record real results and any blockers. Frontend code and dependencies remain unchanged.

## Requirement Coverage Map
| Requirement | Tasks | Evidence |
|---|---|---|
| TR-001 | T001 | Manifest, generated lockfile and installed version |
| TR-002 | T001,T004 | Package-version comparison, dev-only filelock and unchanged scanner policy |
| TR-003 | T002,T003 | Backend checks and rebuilt-image scan |
