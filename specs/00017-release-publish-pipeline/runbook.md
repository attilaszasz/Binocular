# Runbook: Release & Publish Pipeline

This runbook outlines operational procedures for managing software releases and addressing failures in the Binocular automated publication pipeline.

## 1. Triggering a Release

To release a new version of Binocular:
1. Ensure `main` branch builds successfully and all CI gates pass.
2. Draft a new release tag using semantic versioning prefixed with `v` (e.g., `v1.2.3`):
   ```bash
   git tag -a v1.2.3 -m "Release version 1.2.3"
   git push origin v1.2.3
   ```
3. Monitor the Release workflow under the GitHub Actions tab. The workflow will automatically compile the multi-architecture image, scan it for vulnerabilities, sign it, and publish it to GHCR.

## 2. Triggering an Emergency Hotfix

If a critical bug is found and must be fixed immediately:
1. Branch off the latest release tag or `main` (e.g. `hotfix/v1.2.4`).
2. Fix the bug, write regression tests, verify linting and local tests pass.
3. Merge the hotfix branch back to `main`.
4. Tag and push the next patch release:
   ```bash
   git tag -a v1.2.4 -m "Emergency hotfix 1.2.4"
   git push origin v1.2.4
   ```

## 3. Handling Vulnerability Gate Failures

If the Release pipeline fails at the "Trivy vulnerability gate" step:
1. Inspect the GHA logs to identify which dependency contains the HIGH/CRITICAL vulnerability.
2. Check if a patch is available. Since `ignore-unfixed: true` is configured, only vulnerabilities with available fixes will fail the build.
3. Upgrade the vulnerable library or base image:
   - For OS vulnerabilities, verify the base image `python:3.13-slim` or `node:22-slim` is up to date, or trigger a rebuild using the latest cached layers.
   - For python dependencies, update packages in `backend/pyproject.toml` and rebuild `uv.lock`.
   - For npm dependencies, update packages in `frontend/package.json` and rebuild `package-lock.json`.
4. Commit updates, merge to `main`, delete the failed tag locally and remotely if necessary, and push a corrected release tag.

## 4. Triggering a Manual Scan

To manually run a vulnerability scan on the published image:
1. Navigate to the "Actions" tab on GitHub.
2. Select the "Scheduled Vulnerability Scan" workflow.
3. Click "Run workflow" and select the target branch.
