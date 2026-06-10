## Research Report

**Context**: CI/CD pipeline best practices for a Python FastAPI + React/Vite/TypeScript monorepo with GitHub Actions, targeting operational reliability and fast feedback.

## GitHub Actions CI Architecture

- **Key findings**: Modular job separation (lint → test → build) enables parallel execution and fast failure feedback. Concurrency groups with cancel-in-progress prevent duplicate runs on rapid pushes.
- **Recommended**: Separate backend/frontend/docker-build jobs; use `ubuntu-latest`; cache dependencies (uv for Python, npm for Node); keep jobs independent.
- **Avoid**: Monolithic single-job pipelines; running tests without coverage thresholds; skipping Docker build validation.

### Sources
- https://docs.github.com/en/actions/writing-workflows/quickstart — GitHub Actions workflow fundamentals

## Python Quality Gates

- **Key findings**: Ruff replaces flake8+black+isort. `mypy --strict` catches type errors. `pytest-cov` enforces coverage thresholds. `pip-audit` catches dependency vulnerabilities.
- **Recommended**: Ruff lint → mypy strict → pytest with coverage → pip-audit as sequential steps. Set `fail_under` in coverage config.
- **Avoid**: Running mypy without strict flag; omitting security audit; setting coverage threshold below project mandate (80%).

### Sources
- https://docs.astral.sh/ruff/ — Ruff linter documentation

## Frontend Quality Gates

- **Key findings**: Conditional frontend jobs allow CI to pass before frontend scaffolding exists (E004). `npm run lint` covers ESLint/Biome; `tsc --noEmit` catches type errors; `vitest --run` ensures non-interactive test execution.
- **Recommended**: Guard frontend steps with package.json existence check. Use Node 22 LTS with npm cache. Run lint → typecheck → test in sequence.
- **Avoid**: Running Vitest in watch mode in CI; omitting TypeScript strict check; failing CI when optional frontend hasn't been scaffolded yet.

### Sources
- https://vitest.dev/guide/ci — Vitest CI integration guide

## Docker Build-Only Validation

- **Key findings**: PR builds should build the image without pushing, verifying Dockerfile correctness. `docker/build-push-action` with `push: false` and GHA cache (`cache-from: type=gha`) speeds subsequent builds. Buildx enables multi-arch preparation.
- **Recommended**: Use Buildx with GHA cache. Build-only on PRs; push deferred to release pipeline (E017).
- **Avoid**: Pushing images from PR builds; building without cache; skipping Buildx setup.

### Sources
- https://docs.docker.com/build/ci/github-actions/ — Docker GitHub Actions integration

### Summary

The CI pipeline should separate backend, frontend, and Docker build into parallel jobs for fast feedback. Backend gates use Ruff + mypy strict + pytest-cov + pip-audit. Frontend gates are conditional on package.json existence to gracefully handle pre-E004 state. Docker builds use Buildx with GHA cache in build-only mode.

### Sources Index

| URL | Topic | Fetched |
|-----|-------|---------| 
| https://docs.github.com/en/actions/writing-workflows/quickstart | CI Architecture | 2026-06-10 |
| https://docs.astral.sh/ruff/ | Python Quality | 2026-06-10 |
| https://vitest.dev/guide/ci | Frontend Quality | 2026-06-10 |
| https://docs.docker.com/build/ci/github-actions/ | Docker Build | 2026-06-10 |
