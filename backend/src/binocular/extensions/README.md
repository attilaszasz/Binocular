# Extension Boundary

Extension modules are trusted Python files loaded from the configured modules directory.

## Authoring Contract

Each module must define:

- `MODULE_METADATA`: a mapping with `module_id` and `display_name`; `version`, `author`, and `supported_device_hints` are optional.
- `async check_firmware(input, scrape_client)`: an async callable that receives a `ModuleCheckInput` and the host `ScrapeClient`, then returns a `ModuleCheckResult`-compatible mapping or model.

Modules must use the provided `scrape_client` for outbound firmware-page requests. The host owns robots.txt handling, User-Agent, rate limiting, retry, and scrape diagnostics.

## Trust Boundary

Extension modules are not sandboxed. They run in-process with the same application privileges as the core backend, so operators must vet any module before installing it. The container runs as a non-root user to reduce host-level blast radius, but that is not a sandbox and must not be described as one.