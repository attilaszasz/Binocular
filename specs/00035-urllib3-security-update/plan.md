# Plan: urllib3 Security Update

## Technical Context
Python 3.13; uv; FastAPI; requests/Apprise transitive urllib3; Alpine multi-stage Docker build; Trivy.

## Clarification
No unresolved questions. User explicitly authorized oauthlib 4.0.0 remediation, QC, image publication and the subsequent GitHub Actions scan.

## Instructions Check
PASS: No application, data, HTTP-client, privilege, or UI behavior changes. Preserve strict analysis, coverage and enforced image scanning. Existing Alpine-vs-documented-slim discrepancy predates this repair and is not changed here.

## Implementation
Add `urllib3>=2.8.0,<3` to backend runtime dependencies to enforce a secure compatible floor. Run `uv lock --upgrade-package urllib3`; inspect the diff to ensure only urllib3 and root requirement metadata change. Remove pip from the final Docker stage using its own uninstall command: its unused vendored urllib3 also triggers the same two CVEs. Builder tooling remains available and the application venv is unaffected. Sync frozen dependencies and run backend checks. Build a local image and run Trivy with the scheduled workflow's HIGH/CRITICAL, ignore-unfixed and repository ignore-file settings. Do not publish, push or weaken scanner policy.

## Testing Strategy
Authorized QC remediation: enforce `oauthlib>=4.0.0,<5` and resolve exactly 4.0.0 using a package-specific uv upgrade. Preserve other packages. Validate requests-oauthlib/Apprise imports and notification tests. After QC passes, use a short-lived branch and green-CI pull request, then the next unused patch SemVer tag to invoke the existing multi-architecture Release workflow. Wait for publication before dispatching scheduled-scan.yml on main; verify its final conclusion.
Backend: `uv run ruff check .`, `uv run mypy .`, `uv run pytest --cov=binocular --cov-report=term-missing`, `uv run pip-audit`.
Frontend CI-equivalent checks during QC: lint, typecheck and tests.
Image: `docker build -t binocular:urllib3-security-fix .`; `trivy image --severity HIGH,CRITICAL --ignore-unfixed --ignorefile .trivyignore --exit-code 1 binocular:urllib3-security-fix`.
Record actual failures or environment limitations; never infer a passing scan.

## Requirement Coverage Map
| Requirement | Tasks | Evidence |
|---|---|---|
| TR-001 | T001,T004 | Manifest floor, locked urllib3 version and removal of vulnerable vendored copy |
| TR-002 | T001 | Lockfile diff and unchanged scanner config |
| TR-003 | T002,T003 | Backend checks and image scan |
