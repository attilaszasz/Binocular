# Contract: Module Engine Internal Interfaces

## Module Authoring Contract

| Item | Required | Shape |
|------|----------|-------|
| `MODULE_METADATA` | yes | Mapping with module_id, display_name, version, author optional. |
| `async check_firmware(input, scrape_client)` | yes | Async callable returning normalized module check result data. |

## Host Models

| Model | Fields | Consumer |
|-------|--------|----------|
| ModuleMetadata | module_id, display_name, version, author, supported_device_hints | Loader, repository, E008 UI. |
| ModuleCheckInput | device_type, model, current_version, source_url, extra | E009 check workflows. |
| ModuleCheckResult | status, latest_version, detail, source_url, diagnostics | E009 detection/comparison. |
| ValidationPhaseResult | phase, status, findings, duration_ms, error_type, message | E008 validation feedback. |
| ModuleValidationResult | module_id, static_phase, runtime_phase, overall_status | E008 lifecycle and metadata persistence. |

## Service Interfaces

| Service | Operation | Contract |
|---------|-----------|----------|
| ModuleLoader | load(path) | Returns loaded module or structured load failure. |
| ModuleRunner | run(loaded_module, input, scrape_client, timeout_seconds) | Returns ModuleCheckResult or failed result. |
| ModuleValidator | validate(path, proof_input=None) | Returns ModuleValidationResult. |
| ModuleRepository | create/update/list/status | Persists ModuleRecord and validation summary. |

## Error Contract

| Error | Result Mapping |
|-------|----------------|
| syntax/import/contract failure | static phase failed |
| invalid runtime output | runtime phase failed |
| ScrapeClient error | runtime failed with scrape diagnostics |
| timeout | runtime failed with `timeout` error_type |
| `Exception` or `SystemExit` | runtime failed with normalized error type/message |
| host cancellation | re-raised, not converted to module success/failure |
