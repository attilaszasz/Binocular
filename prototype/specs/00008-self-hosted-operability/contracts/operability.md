# Contract: Self-Hosted Operability

## Runtime Settings

| Setting | Type | Default | Secret File | Behavior |
|---------|------|---------|-------------|----------|
| `BINOCULAR_DATA_DIR` | path | `/app/data` in image, `data` locally | no | Base durable data path. |
| `BINOCULAR_MODULES_DIR` | path | `/app/modules` in Compose, `modules` locally | no | Trusted module source path. |
| `BINOCULAR_AUTH_ENABLED` | bool | `false` | no | Enables HTTP basic auth only when credentials are complete. |
| `BINOCULAR_AUTH_USERNAME` | string | empty | no | Required when auth enabled. |
| `BINOCULAR_AUTH_PASSWORD` | secret string | empty | yes: `BINOCULAR_AUTH_PASSWORD_FILE` | Required when auth enabled. |

## Secret Resolution Rules

1. If neither direct nor `_FILE` value is supplied, use the normal settings default.
2. If only direct value is supplied, use it.
3. If only `_FILE` is supplied, read and trim one trailing newline from the file contents.
4. If both direct and `_FILE` are supplied for the same setting, fail startup with a configuration error naming the setting.
5. If `_FILE` points to a missing, unreadable, or empty file, fail startup with a configuration error naming the setting.
6. Secret values must never appear in logs, exception messages, API responses, or test assertions.

## Basic Auth Behavior

| Condition | Expected Result |
|-----------|-----------------|
| `auth_enabled=false` | UI, static assets, health, and API routes remain accessible without credentials. |
| `auth_enabled=true` and missing username/password | startup fails with a configuration error. |
| `auth_enabled=true` and invalid/missing request credentials | request returns `401` with `WWW-Authenticate: Basic`. |
| `auth_enabled=true` and valid credentials | request proceeds to the underlying route/static handler. |

## Route Coverage

| Route Class | Protected When Auth Enabled | Notes |
|-------------|-----------------------------|-------|
| `/api/*` | yes | Includes inventory and future API routes. |
| `/assets/*` | yes | Static bundle should not bypass auth. |
| SPA fallback `/...` | yes | Deep links require auth. |
| `/healthz` | no | Container healthcheck must work without credentials. |

## Example Files

| File | Required Content |
|------|------------------|
| `compose.yaml` | app service, one exposed port, `/app/data` volume, `/app/modules` volume, env file reference, optional secret mount example. |
| `.env.example` | port/bind defaults, data/modules path notes, auth disabled defaults, password and password-file examples commented or empty. |
