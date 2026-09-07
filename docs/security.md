# Security Model

## Extension trust boundary

Binocular extensions are user-vetted Python code. They execute unsandboxed and
in-process with full application privileges. The host-provided HTTP client
enforces robots policy, pacing, retries, redirects, credentials, and check-scope
deadlines for cooperative extensions. It is not a sandbox and does not claim to
contain malicious modules, alternate sockets or subprocesses, or already-running
non-cooperative kernel I/O.

Install only extensions whose source and provenance you trust. Official modules
are statically checked to use the host client and are fixture-tested before
release.

## Supported deployment boundary

Binocular is a single-user application intended for a trusted LAN. Exposing the
service to untrusted networks is outside the supported security posture. The
container runs application work as a non-root user to limit blast radius, not to
sandbox extension code.
