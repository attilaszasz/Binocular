# Research: Continuous Integration Pipeline
> E002 | 2026-05-31 | Inform workflow design and validation

## GitHub Actions CI
- **Decision**: Use one PR/push workflow with backend, frontend, and Docker build jobs.
- **Rationale**: Separate jobs make failures visible while allowing independent evolution of backend and frontend checks.
- **Rejected**: A single shell-only job; it hides ownership and makes future frontend additions harder.
- **Pitfalls**: Do not publish images from PRs; keep push/publish for the later release epic.
- **Sources**: https://docs.github.com/actions, https://docs.docker.com/build/ci/github-actions/

## Backend Gates
- **Decision**: Run `ruff check`, `mypy`, `pytest --cov`, and `pip-audit` from `backend/`.
- **Rationale**: These match project instructions for linting, strict typing, tests, coverage, and security scanning.
- **Rejected**: Running tests without coverage; it would miss the configured 80% policy.
- **Pitfalls**: Use a virtualenv or GitHub setup-python environment, not system Python mutation.
- **Sources**: https://docs.astral.sh/ruff/, https://mypy.readthedocs.io/

## Frontend Gates
- **Decision**: Add a frontend job that runs only when `frontend/package.json` exists.
- **Rationale**: E003 is parallel and may not exist yet, but the CI contract should activate automatically when the SPA lands.
- **Rejected**: Failing CI because the future frontend directory is absent; that would block E002 before E003.
- **Pitfalls**: A skipped absent-frontend path must be visible in logs, not silently ignored.
- **Sources**: https://docs.github.com/actions/using-jobs/using-conditions-to-control-job-execution

## Docker Build Gate
- **Decision**: Build the repository `Dockerfile` with Buildx and GitHub Actions cache, without push.
- **Rationale**: E002 validates image buildability on every change while E018 owns multi-arch publishing.
- **Rejected**: Pushing images in CI for all branches; it violates the build-only constraint.
- **Pitfalls**: Keep permissions minimal and avoid registry login in this workflow.
- **Sources**: https://github.com/docker/setup-buildx-action, https://github.com/docker/build-push-action

## Summary
| Topic | Decision | Rationale |
|-------|----------|-----------|
| Workflow | PR/push CI | Early validation |
| Backend | Ruff/mypy/pytest/pip-audit | PI quality gates |
| Frontend | conditional job | Compatible with E003 parallelism |
| Docker | build-only Buildx | Validates image without publishing |