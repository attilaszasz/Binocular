# Research: Self-Hosted Operability
> E013 | 2026-05-31 | Inform auth, secret, and deployment planning

## Docker Secrets And `_FILE` Inputs
- **Decision**: Support direct env vars and matching `_FILE` variables for credential-like settings; conflict fails fast.
- **Rationale**: Docker secrets mount as files and conflict failure avoids silent secret ambiguity.
- **Rejected**: `_FILE` precedence over direct env, because hidden precedence can mask operator mistakes.
- **Pitfalls**: Never log secret values or require secrets for default startup.
- **Sources**: https://docs.docker.com/engine/swarm/secrets/, https://docs.docker.com/compose/how-tos/use-secrets/

## Optional Basic Authentication
- **Decision**: Keep auth off by default; enable only with explicit flag plus username/password.
- **Rationale**: This preserves the trusted-LAN model while offering light protection for broader exposure.
- **Rejected**: Multi-user auth and RBAC, because v1 scope is single-user trusted LAN.
- **Pitfalls**: Do not present basic auth as internet-grade security; use constant-time comparison.
- **Sources**: https://fastapi.tiangolo.com/advanced/security/http-basic-auth/, https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication

## Single-Volume Persistence
- **Decision**: Keep mutable state in declared `/app/data` and `/app/modules` volumes and verify restart/upgrade survival.
- **Rationale**: Docker volumes survive container replacement; SQLite remains reliable when file state is on durable storage.
- **Rejected**: Hidden state outside declared volumes, because it breaks backup and upgrade expectations.
- **Pitfalls**: Avoid writing operator data to image layers or temp paths.
- **Sources**: https://docs.docker.com/engine/storage/volumes/, https://www.sqlite.org/howtocorrupt.html

## Summary
| Topic | Decision | Rationale |
|-------|----------|-----------|
| Secrets | direct env + `_FILE`, conflict fails | avoids secret leakage and ambiguity |
| Auth | opt-in basic auth | preserves no-auth trusted-LAN default |
| Persistence | declared volumes only | supports restart and upgrade survival |

## Sources Index
| URL | Topic | Fetched |
|-----|-------|---------|
| https://docs.docker.com/engine/swarm/secrets/ | Docker Secrets | 2026-05-31 |
| https://docs.docker.com/compose/how-tos/use-secrets/ | Docker Secrets | 2026-05-31 |
| https://fastapi.tiangolo.com/advanced/security/http-basic-auth/ | Basic Auth | 2026-05-31 |
| https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication | Basic Auth | 2026-05-31 |
| https://docs.docker.com/engine/storage/volumes/ | Persistence | 2026-05-31 |
| https://www.sqlite.org/howtocorrupt.html | Persistence | 2026-05-31 |
