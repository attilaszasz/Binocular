# Release Runbook

## Cut a Release

1. Confirm `main` is green in CI and contains the intended release commits.
2. Create and push a SemVer tag:

   ```sh
   git tag vMAJOR.MINOR.PATCH
   git push origin vMAJOR.MINOR.PATCH
   ```

3. Open GitHub Actions and monitor the `Release` workflow for the tag.
4. Confirm the workflow published `ghcr.io/<owner>/binocular:<version>` and `ghcr.io/<owner>/binocular:latest`.
5. Confirm the workflow summary includes the immutable image digest.

## Verify a Published Image

Use the digest from the release workflow summary:

```sh
gh attestation verify oci://ghcr.io/<owner>/binocular@sha256:<digest> --repo <owner>/<repo>
docker buildx imagetools inspect ghcr.io/<owner>/binocular:<version>
```

The image inspection must list `linux/amd64` and `linux/arm64` platforms. The attestation command must verify the provenance and SBOM attestations for the digest.

## Trivy Gate Failure

A release workflow failure in `Trivy vulnerability gate` means the local release candidate contains a fixable HIGH or CRITICAL vulnerability.

1. Open the failed Trivy step and identify the package, installed version, fixed version, and severity.
2. Prefer the smallest safe remediation:
   - update the affected Python or Node dependency;
   - update the Docker base image tag if the vulnerability is OS-level;
   - remove unused dependency paths if they are not needed in the runtime image.
3. Run the local quality gates before retagging:

   ```sh
   cd backend && ruff check . && mypy . && pytest --cov=binocular --cov-report=term-missing
   cd ../frontend && npm run lint && npm run typecheck && npm test -- --run
   cd .. && docker build -t binocular:release-check .
   ```

4. Delete and recreate the release tag only if the failed tag has not been announced as a release. Otherwise, cut a new patch tag.
5. Re-run the release workflow by pushing the corrected SemVer tag.

## Publication Failure

If publishing or attestation fails after the Trivy gate passes:

1. Check repository package permissions for GHCR write access.
2. Verify the workflow job permissions include `packages: write`, `id-token: write`, and `attestations: write`.
3. Re-run the failed workflow once permissions or transient registry issues are resolved.
4. Treat the release as incomplete until the workflow finishes with published tags, SBOM attestation, and provenance attestation.
