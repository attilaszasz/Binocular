# Research: Minimal Docker Runtime Base Package Update
> 00028-minimal-docker-runtime-base-package | 2026-08-23 | Inform plan amendment

## Dev-Only pip Resolution
- **Decision**: Declare `pip>=26.2` only in the existing uv `dev` dependency group and lock its resolved version.
- **Rationale**: uv dependency groups are local development dependencies, while the runtime builder synchronizes with `--no-dev`.
- **Rejected**: Add pip to `project.dependencies` or the runtime image; both alter the production dependency surface.
- **Pitfalls**: Do not modify application dependencies or omit the corresponding `uv.lock` resolution.
- **Sources**: https://docs.astral.sh/uv/concepts/projects/dependencies/#development-dependencies

## Local Candidate Build
- **Decision**: Use `docker buildx build --load -t binocular:qc-check -f Dockerfile .` with the active docker-container builder.
- **Rationale**: `--load` is shorthand for the Docker exporter and makes the single-platform candidate available to local inspection and Trivy.
- **Rejected**: Bare `docker build` or a Buildx build without output; neither expresses the required Buildx workflow or guarantees a local candidate export.
- **Pitfalls**: `--load` supports a single-platform result; do not change release multi-architecture publishing.
- **Sources**: https://docs.docker.com/reference/cli/docker/buildx/build/#load

## Local OS Vulnerability Scan
- **Decision**: Scan the loaded candidate with `trivy image --scanners vuln --pkg-types os` plus the existing severity and fixed-finding filters.
- **Rationale**: `--pkg-types` is the current supported selector and `os` limits local verification to the Debian runtime packages at issue.
- **Rejected**: Deprecated `--vuln-type` or scanner-policy changes; neither is in scope.
- **Pitfalls**: Do not suppress named CVEs; a missing vendor fix or delayed advisory data must remain visible.
- **Sources**: https://trivy.dev/latest/docs/references/configuration/cli/trivy_image/

## Summary
| Topic | Decision | Rationale |
|-------|----------|-----------|
| Dev-only pip | uv `dev` group only | Excluded from production sync |
| Candidate build | Buildx docker-container + `--load` | Exports local single-platform image |
| OS scan | `--pkg-types os` | Targets Debian packages without deprecated flag |

## Sources Index
| URL | Topic | Fetched |
|-----|-------|---------|
| https://docs.astral.sh/uv/concepts/projects/dependencies/#development-dependencies | Dev-only pip | 2026-08-23 |
| https://docs.docker.com/reference/cli/docker/buildx/build/#load | Candidate build | 2026-08-23 |
| https://trivy.dev/latest/docs/references/configuration/cli/trivy_image/ | OS scan | 2026-08-23 |
