# Research: E017 — Release & Publish Pipeline

This research document summarizes operational best practices for implementing a secure, multi-architecture build and release pipeline within GitHub Actions.

## 1. GitHub Actions and GHCR Authentication
GitHub Packages (GHCR) is the recommended container registry for GitHub Actions. Authenticating to GHCR should use the automatic `GITHUB_TOKEN` provided by GitHub Actions for security, avoiding hardcoded secrets or personal access tokens. Jobs must explicitly request the `write` permission for the packages scope (`packages: write`) to push images.
Sources:
- GitHub Documentation: "Working with the Container registry"
- OpenSSF: "Token Permissions Best Practices"

## 2. Multi-Architecture Docker Builds via Buildx and QEMU
Building images for both `linux/amd64` and `linux/arm64` ensures homelab compatibility. In GitHub Actions, QEMU emulation is initialized via `docker/setup-qemu-action`, and Buildx via `docker/setup-buildx-action`. Using buildx allows simultaneous building and pushing of multi-arch manifests in a single step, preventing intermediate image layer pulling/pushing bottlenecks.
Sources:
- Docker Documentation: "Multi-platform images with Buildx"
- GitHub Actions: "docker/build-push-action"

## 3. Trivy Container Vulnerability Scanning
Trivy is an industry-standard, lightweight container scanner. In the release pipeline, scanning the newly built image before publishing catches vulnerabilities. The scanner should fail the build on high/critical severity items when fixes are available to prevent publishing vulnerable images. Running a weekly cron workflow in GitHub Actions to scan the latest published image ensures continuous visibility into newly discovered vulnerabilities.
Sources:
- Aqua Security: "Trivy GitHub Action integration"
- CNCF: "Continuous Container Security Auditing"

## 4. SBOM and Provenance Attestation Generation
Software Bill of Materials (SBOM) and build provenance increase supply chain security. Docker Buildx integrates natively with BuildKit to attach SBOM (using SPDX format) and SLSA provenance attestations during the build-and-push step using `docker/build-push-action` parameters. Attestations are stored alongside the image layers in GHCR.
Sources:
- Docker Documentation: "Attestations and SBOMs"
- SLSA: "Provenance Generation in CI/CD"

## 5. Build-Time Version Injection in React/Vite
Injecting the git tag version at build time ensures the UI displays the correct version without manual updates. In React/Vite, variables prefixed with `VITE_` are injected at build time. The release workflow can extract the tag name using github context refs and pass it as a `--build-arg` to the Docker build, which then maps it to the frontend environment.
Sources:
- Vite Guide: "Env Variables and Modes"
- GitHub Actions: "Using GitHub Contexts"
