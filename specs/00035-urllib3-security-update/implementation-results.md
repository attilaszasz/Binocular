## Dependency Repair

- Added `urllib3>=2.8.0,<3` and resolved urllib3 2.8.0 using `uv lock --upgrade-package urllib3`.
- All 79 unrelated locked package records are unchanged. Only urllib3, root dependency metadata, and uv-generated lockfile revision changed.
- Removed unused base-image pip with `python -m pip uninstall --yes pip` in the final Docker stage before the venv copy. Builder tooling is unchanged.
- Archived prototype, scan workflows, `.trivyignore`, and unrelated application dependencies are unchanged.
- Reverted implementation-added `.gitignore` changes and removed implementation-added `.dockerignore`; neither is necessary to this repair.

## Actual Validation

- `uv lock --check` and `uv sync --frozen`: PASS.
- `uv run --frozen ruff check .`: PASS.
- `uv run --frozen mypy .`: PASS; strict configuration, 116 source files.
- `uv run --frozen pytest --cov=binocular --cov-report=term-missing`: PASS; 442 tests, 86.85% coverage.
- `uv run --frozen pip-audit`: FAIL on the final rerun as well as earlier attempts; unchanged oauthlib 3.3.1 has `PYSEC-2026-4114`, fixed in 4.0.0. No urllib3 finding. Local project is skipped because it is not on PyPI. T002 explicitly requires recording unrelated audit blockers, not fixing them.
- `docker build -t binocular:urllib3-security-fix .`: PASS, but the configured docker-container builder does not load images by default. Retried with `--load`: PASS.
- Final `docker build --load -t binocular:urllib3-security-fix .`: PASS after pip removal.
- Final image ID: `sha256:454ec2d61203836a798b075c62883aa98ca44d64484cc4e6ed4930d960036c7c`.
- Runtime checks confirm application urllib3 2.8.0, pip absent from base Python and application Python, and no remaining base site-packages `pip*` files. Application factory, requests and Apprise imports pass.
- Actual default-entrypoint startup: PASS; `/healthz` returns HTTP 200 and `{"status":"ok"}`. Application process UID/GID are 1000/1000. Temporary validation container was removed.
- Final `trivy image --severity HIGH,CRITICAL --ignore-unfixed --ignorefile .trivyignore --exit-code 1 binocular:urllib3-security-fix`: PASS, exit 0; zero enforced OS/library findings. JSON repeat also passes with neither `CVE-2026-97687` nor `CVE-2026-97689` present.
- Earlier scan failure was traced to base-image pip 26.2.1 vendoring urllib3 2.7.0; T004 removes this independent copy. Scanner policy was not weakened.
- Docker frontend build also reported 24 npm audit findings (15 HIGH); frontend dependencies were not modified.
- `git diff --check`: PASS.

## Completion and Remaining Risk

- T001, T004, T002, T003 and T005 are complete under the updated authorized task scope. Structural review and real image validation pass.
- The oauthlib audit advisory is resolved by T005. Frontend dependencies were not changed; full QC remains the next gate. No release-readiness claim is made.
- `.completed` records implementation completion only. No commit, push, publication, or QC pass was performed; `.qc-passed` was not created.
- Raw logs and Trivy JSON are in ignored `backend/.venv/implementation-evidence/`.
- Nested workflow delegation was unavailable because the subagent depth limit was reached; the workflow was executed directly.

## T005 Authorized oauthlib Remediation

- Added `oauthlib>=4.0.0,<5`; `uv lock --upgrade-package 'oauthlib==4.0.0'` resolved exactly 4.0.0. Compared parsed package records against the pre-T005 lock: only oauthlib and root dependency metadata changed; 79 other records are identical. Scanner workflows and `.trivyignore` remain unchanged.
- Reviewed upstream 4.0.0 changelog at `https://raw.githubusercontent.com/oauthlib/oauthlib/master/CHANGELOG.rst`: breaking changes concern provider authentication and JSONP revocation, not the tested OAuth client signing/authorization paths.
- Compatibility PASS: requests-oauthlib 2.0.0 imports, OAuth1 request signing, OAuth2 authorization URL and bearer-token preparation; Apprise 1.11.0 imports and notification plugin loading. No external request was made. Existing notification tests pass within the full suite. Initial scratch check incorrectly expected OAuth2Session.prepare_request to add a bearer header; corrected to its OAuth client add_token path and reran successfully, without application changes.
- `uv lock --check`, `uv sync --frozen`, Ruff and strict mypy (116 source files): PASS.
- `uv run --frozen pytest --cov=binocular --cov-report=term-missing`: PASS; 442 tests, 86.85% coverage.
- `uv run --frozen pip-audit`: PASS; no known vulnerabilities. Local binocular package is skipped because it is unavailable on PyPI.
- `docker build --load -t binocular:urllib3-security-fix .`: PASS. Updated image ID: `sha256:8b286d2c72d923bf9c4580bc855d75e3223e8be60e51455e0c92c73f30acb5b7`.
- `trivy image --severity HIGH,CRITICAL --ignore-unfixed --ignorefile .trivyignore --exit-code 1 binocular:urllib3-security-fix`: PASS, exit 0; zero enforced OS/library findings. JSON repeat also passes.
- Updated-image runtime imports PASS: application factory, oauthlib 4.0.0, urllib3 2.8.0, requests-oauthlib and Apprise; pip remains absent. File existence, strict typing, no new code stubs and `git diff --check` structural review PASS.
- T005 marked complete and implementation checkpoint/`.completed` updated only after successful validation. No commit, push, publication, QC report mutation or `.qc-passed` creation performed.
- T005 raw logs and Trivy JSON: ignored `backend/.venv/implementation-evidence/t005-*`.
