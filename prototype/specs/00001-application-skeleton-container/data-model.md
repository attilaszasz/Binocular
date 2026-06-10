# Data Model: Application Skeleton & Container

No persistent data schema is introduced by E001. The entities below are runtime/configuration concepts only.

| Entity | Type | Key Fields | Lifecycle | Notes |
|--------|------|------------|-----------|-------|
| App Factory | Runtime component | settings, routers, logging | Constructed on import/startup | Owns FastAPI app assembly. |
| Settings | Runtime config | app_name, host, port, log_level, environment | Loaded at app construction | Defaults must require no environment variables. |
| Health Response | API DTO | status, service, version | Returned per request | Shallow liveness only. |
| Extension Boundary | Package boundary | core namespace, extension namespace | Established at source layout | Documents unsandboxed future module trust boundary. |

## Persistence

N/A — E001 adds no database tables, migrations, stored records, or external persistence.